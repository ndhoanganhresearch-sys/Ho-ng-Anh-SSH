import numpy as np

from registration_engine import StationData, StationManager, Target, compute_svd_transform


def make_transform(angle_deg=8.0, translation=(1.2, -0.7, 0.25)):
    angle = np.deg2rad(angle_deg)
    c, s = np.cos(angle), np.sin(angle)
    transform = np.eye(4)
    transform[:3, :3] = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    transform[:3, 3] = np.array(translation, dtype=float)
    return transform


def apply_transform(points, transform):
    homogeneous = np.ones((len(points), 4))
    homogeneous[:, :3] = points
    return (transform @ homogeneous.T).T[:, :3]


def build_tunnel_points():
    y = np.linspace(0.0, 20.0, 80)
    theta = np.linspace(0.0, 2.0 * np.pi, 40, endpoint=False)
    yy, tt = np.meshgrid(y, theta)
    radius = 3.0
    x = radius * np.cos(tt)
    z = radius * np.sin(tt) + 3.0
    return np.column_stack([x.ravel(), yy.ravel(), z.ravel()])


def test_svd_transform():
    source = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.0, 0.0, 1.5],
            [1.0, 2.0, 1.0],
        ]
    )
    true_transform = make_transform()
    target = apply_transform(source, true_transform)
    estimated, rmse = compute_svd_transform(source, target)
    assert rmse < 1e-9, f"SVD RMSE too high: {rmse}"
    assert np.allclose(estimated, true_transform, atol=1e-9), "SVD transform mismatch"
    return rmse


def test_station_manager_registration():
    base_points = build_tunnel_points()
    targets_global = np.array(
        [
            [-2.0, 2.0, 4.5],
            [2.0, 5.0, 4.7],
            [-1.8, 9.0, 1.5],
            [1.9, 13.0, 1.6],
            [0.2, 17.0, 5.8],
        ]
    )
    local_to_previous = make_transform(angle_deg=5.0, translation=(0.4, 1.1, -0.2))
    previous_to_local = np.linalg.inv(local_to_previous)
    current_local_points = apply_transform(base_points, previous_to_local)
    current_local_targets = apply_transform(targets_global, previous_to_local)

    previous = StationData(station_id="S001", filepath="synthetic_previous.las", timestamp="T0", points=base_points)
    current = StationData(station_id="S002", filepath="synthetic_current.las", timestamp="T0", points=current_local_points)
    previous.targets = [
        Target(target_id=f"T{i:03d}", centroid=point, point_count=50, mean_intensity=1000.0)
        for i, point in enumerate(targets_global, start=1)
    ]
    current.targets = [
        Target(target_id=f"T{i:03d}", centroid=point, point_count=50, mean_intensity=1000.0)
        for i, point in enumerate(current_local_targets, start=1)
    ]

    manager = StationManager()
    manager.stations = [previous, current]
    links = manager.register_sequential(use_icp=False, prefer_target_ids=True)
    assert len(links) == 1, "Expected one registration link"
    link = links[0]
    assert link.rmse_final_m < 1e-9, f"Registration RMSE too high: {link.rmse_final_m}"
    assert np.allclose(current.transform_global, local_to_previous, atol=1e-9), "Accumulated transform mismatch"
    return link.rmse_final_m


def test_temporal_overlap():
    base_points = build_tunnel_points()
    shifted_points = base_points.copy()
    shifted_points[:, 2] += 0.002

    manager = StationManager()
    manager.stations = [
        StationData(station_id="S001", filepath="synthetic_t0.las", timestamp="T0", points=base_points),
        StationData(station_id="S002", filepath="synthetic_t1.las", timestamp="T1", points=shifted_points),
    ]
    results = manager.compute_temporal_overlap(reference_timestamp="T0", current_timestamp="T1", method="c2c", voxel_size=0.0)
    assert len(results) == 1, "Expected one deformation result"
    mean_delta = results[0].statistics["mean_delta_mm"]
    assert 1.9 <= mean_delta <= 2.1, f"Mean delta should be about 2 mm, got {mean_delta}"
    return mean_delta




def test_target_ids_no_mutation():
    """Targets must be created with final IDs, never with empty string."""
    import numpy as np
    from registration_engine import Target

    targets = [
        Target(target_id=f"T{i:03d}", centroid=np.array([float(i), 0.0, 0.0]), point_count=25, mean_intensity=500.0)
        for i in range(1, 6)
    ]
    for t in targets:
        assert t.target_id != "", f"Target ID must not be empty, got: {t.target_id!r}"
        assert t.target_id.startswith("T"), f"Target ID must start with T, got: {t.target_id!r}"
    return True


def test_thread_safety_registration():
    """register_sequential must accumulate transforms without race conditions."""
    import threading
    import numpy as np
    from registration_engine import StationData, StationManager, Target

    def build_tunnel_pts():
        y = np.linspace(0.0, 20.0, 80)
        theta = np.linspace(0.0, 2.0 * np.pi, 40, endpoint=False)
        yy, tt = np.meshgrid(y, theta)
        return np.column_stack([3.0 * np.cos(tt).ravel(), yy.ravel(), 3.0 * np.sin(tt).ravel() + 3.0])

    base = build_tunnel_pts()
    targets_global = np.array([[-2.0, 2.0, 4.5], [2.0, 5.0, 4.7], [-1.8, 9.0, 1.5], [1.9, 13.0, 1.6], [0.2, 17.0, 5.8]])

    manager = StationManager()
    manager.stations = [
        StationData(station_id="S001", filepath="s1.las", timestamp="T0", points=base),
        StationData(station_id="S002", filepath="s2.las", timestamp="T0", points=base.copy()),
    ]
    for s in manager.stations:
        s.targets = [Target(target_id=f"T{i:03d}", centroid=pt, point_count=50, mean_intensity=1000.0)
                     for i, pt in enumerate(targets_global, start=1)]

    errors = []
    def run():
        try:
            manager.register_sequential(use_icp=False, prefer_target_ids=True)
        except Exception as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=run) for _ in range(3)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert not errors, f"Thread errors: {errors}"
    return True


def test_import_targets_csv():
    """import_targets_csv must load targets without NameError on targets variable."""
    import tempfile, csv, os
    import numpy as np
    from registration_engine import StationData, StationManager

    rows = [
        {"target_id": "T001", "x": "1.0", "y": "2.0", "z": "3.0", "point_count": "30", "mean_intensity": "800.0", "radius_m": "0.05"},
        {"target_id": "T002", "x": "4.0", "y": "5.0", "z": "6.0", "point_count": "28", "mean_intensity": "820.0", "radius_m": "0.05"},
        {"target_id": "T003", "x": "7.0", "y": "8.0", "z": "9.0", "point_count": "32", "mean_intensity": "790.0", "radius_m": "0.05"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        tmp_path = f.name
    try:
        station = StationData(station_id="S001", filepath="s1.las", timestamp="T0",
                              points=np.zeros((10, 3), dtype=np.float64))
        manager = StationManager()
        loaded = manager.import_targets_csv(station, tmp_path)
        assert len(loaded) == 3, f"Expected 3 targets, got {len(loaded)}"
        assert loaded[0].target_id == "T001"
    finally:
        os.unlink(tmp_path)
    return True

if __name__ == "__main__":
    svd_rmse = test_svd_transform()
    reg_rmse = test_station_manager_registration()
    mean_delta = test_temporal_overlap()
    target_id_ok = test_target_ids_no_mutation()
    thread_ok = test_thread_safety_registration()
    csv_ok = test_import_targets_csv()
    print("SMOKE TEST PASSED")
    print(f"SVD RMSE: {svd_rmse * 1000:.6f} mm")
    print(f"Sequential registration RMSE: {reg_rmse * 1000:.6f} mm")
    print(f"Temporal overlap mean delta: {mean_delta:.6f} mm")
    print(f"Target ID no-mutation: {target_id_ok}")
    print(f"Thread safety registration: {thread_ok}")
    print(f"Import targets CSV: {csv_ok}")

