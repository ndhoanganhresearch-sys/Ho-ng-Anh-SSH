from .common import *
from .models import PointCloudBundle
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

PLY_DTYPES = {
    "char":"i1","int8":"i1","uchar":"u1","uint8":"u1",
    "short":"i2","int16":"i2","ushort":"u2","uint16":"u2",
    "int":"i4","int32":"i4","uint":"u4","uint32":"u4",
    "float":"f4","float32":"f4","double":"f8",
}

MAX_POINTS_DEFAULT = 5_000_000  # 5M points max to avoid OOM

def _read_las(fp: str, max_points: int = MAX_POINTS_DEFAULT) -> PointCloudBundle:
    if laspy is None: raise RuntimeError("laspy not installed.")
    las = laspy.read(fp)
    total = len(las.x)
    
    # Subsample if too large
    if total > max_points:
        step = max(1, total // max_points)
        idx = np.arange(0, total, step)
        x = np.asarray(las.x)[idx]
        y = np.asarray(las.y)[idx]
        z = np.asarray(las.z)[idx]
        intensity = np.asarray(las.intensity, dtype=np.float64)[idx] if hasattr(las, "intensity") else None
        colors = None
        if all(hasattr(las, c) for c in ("red", "green", "blue")):
            colors = np.vstack([np.asarray(las.red)[idx], np.asarray(las.green)[idx], np.asarray(las.blue)[idx]]).T.astype(np.float64)
        subsampled = True
    else:
        x = np.asarray(las.x)
        y = np.asarray(las.y)
        z = np.asarray(las.z)
        intensity = np.asarray(las.intensity, dtype=np.float64) if hasattr(las, "intensity") else None
    # If intensity is all zeros but RGB exists, compute luminance as pseudo-intensity
    if intensity is not None and float(intensity.max()) < 1e-6:
        if all(hasattr(las, c) for c in ("red", "green", "blue")):
            if total > max_points:
                r_arr = np.asarray(las.red, dtype=np.float64)[idx]
                g_arr = np.asarray(las.green, dtype=np.float64)[idx]
                b_arr = np.asarray(las.blue, dtype=np.float64)[idx]
            else:
                r_arr = np.asarray(las.red, dtype=np.float64)
                g_arr = np.asarray(las.green, dtype=np.float64)
                b_arr = np.asarray(las.blue, dtype=np.float64)
            luminance = 0.299*r_arr + 0.587*g_arr + 0.114*b_arr
            if float(luminance.max()) > 1e-6:
                intensity = luminance
        colors = None
        if all(hasattr(las, c) for c in ("red", "green", "blue")):
            colors = np.vstack([las.red, las.green, las.blue]).T.astype(np.float64)
        subsampled = False

    pts = np.vstack([x, y, z]).T.astype(np.float64)
    pts = validate_xyz(pts, Path(fp).name)
    cloud = make_vertex_cloud(pts, intensity=intensity, colors_raw=colors)
    return PointCloudBundle(
        points=pts, intensity=intensity, colors_raw=colors, path=fp, cloud=cloud,
        metadata={
            "format": Path(fp).suffix.lower(),
            "point_count": int(len(pts)),
            "original_count": total,
            "subsampled": subsampled,
            "subsample_step": total // max_points if subsampled else 1,
            "bounds_min": pts.min(0).tolist(),
            "bounds_max": pts.max(0).tolist(),
            "has_intensity": intensity is not None,
            "has_colors": colors is not None,
        },
    )

def _read_ply(fp: str) -> PointCloudBundle:
    path = Path(fp)
    with path.open("rb") as fh:
        if fh.readline().strip() != b"ply": raise ValueError(f"Not PLY: {fp}")
        fmt = None; n_v = 0; props: List[Tuple[str, str]] = []; elem = None
        while True:
            raw = fh.readline()
            if not raw: raise ValueError("PLY header truncated.")
            line = raw.decode("ascii", errors="replace").strip()
            if line == "end_header": break
            if not line or line.startswith("comment"): continue
            p = line.split()
            if p[0] == "format": fmt = p[1]
            elif p[0] == "element": elem = p[1]; n_v = int(p[2]) if elem == "vertex" else n_v
            elif p[0] == "property" and elem == "vertex":
                props.append((p[2], p[1]))
        pnames = [nm.lower() for nm, _ in props]
        xyz_i = [pnames.index(a) for a in ("x", "y", "z")]
        ci = None
        for cn in (("red", "green", "blue"), ("r", "g", "b")):
            if all(c in pnames for c in cn): ci = [pnames.index(c) for c in cn]; break
        if fmt == "ascii":
            pts = np.empty((n_v, 3), dtype=np.float64)
            col = np.empty((n_v, 3), dtype=np.float64) if ci else None
            for r in range(n_v):
                vs = fh.readline().decode("ascii", "replace").split()
                pts[r] = [float(vs[i]) for i in xyz_i]
                if col is not None and ci: col[r] = [float(vs[i]) for i in ci]
        else:
            endian = "<" if "little" in (fmt or "") else ">"
            dtype = np.dtype([(f"f{i}_{nm}", endian + PLY_DTYPES[k]) for i, (nm, k) in enumerate(props)])
            table = np.fromfile(fh, dtype=dtype, count=n_v)
            fn = table.dtype.names or ()
            pts = np.column_stack([table[fn[i]] for i in xyz_i]).astype(np.float64)
            col = np.column_stack([table[fn[i]] for i in ci]).astype(np.float64) if ci else None
    pts = validate_xyz(pts, path.name)
    cloud = make_vertex_cloud(pts, colors_raw=col)
    return PointCloudBundle(
        points=pts, colors_raw=col, path=fp, cloud=cloud,
        metadata={"format": ".ply", "point_count": int(len(pts)),
                  "bounds_min": pts.min(0).tolist(), "bounds_max": pts.max(0).tolist(),
                  "has_intensity": False, "has_colors": col is not None},
    )

def _sniff_delimiter(line: str) -> Optional[str]:
    """Guess the column delimiter of a text point-cloud line.

    Returns None for any-whitespace (numpy default), or an explicit char for
    comma / semicolon / tab separated files. Picks whichever non-space
    delimiter yields the most columns, else falls back to whitespace.
    """
    best = None
    best_n = 1
    for d in (",", ";", "\t"):
        n = len(line.split(d))
        if n > best_n:
            best_n = n
            best = d
    return best


def _read_txt(fp: str, max_points: int = MAX_POINTS_DEFAULT) -> PointCloudBundle:
    """Read an ASCII point cloud (.txt/.xyz/.pts/.csv/.asc).

    Auto-detects delimiter (whitespace/comma/semicolon/tab), an optional
    non-numeric header line, and column layout by width: 3 -> XYZ; 6 -> XYZ +
    (normals or RGB); 7+ -> XYZ + normals(3) + intensity (+ label, kept in
    metadata). Subsamples by striding when the file exceeds max_points (same
    policy as the LAS reader) so large FY387/STSD scans stay within memory.
    """
    path = Path(fp)
    header_rows = 0
    delim = None
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            t = line.strip()
            if not t:
                header_rows += 1
                continue
            if t.startswith(("#", "//")):
                header_rows += 1
                continue
            delim = _sniff_delimiter(t)
            first = t.split(delim) if delim else t.split()
            try:
                float(first[0]); float(first[1]); float(first[2])
            except (ValueError, IndexError):
                header_rows += 1
            break

    arr = np.loadtxt(str(path), delimiter=delim, skiprows=header_rows, ndmin=2)
    if arr.ndim != 2 or arr.shape[1] < 3:
        raise ValueError(f"{path.name}: need >= 3 numeric columns, got shape {arr.shape}.")
    total = int(len(arr))
    subsampled = False
    step = 1
    if total > max_points:
        step = max(1, total // max_points)
        arr = arr[::step]
        subsampled = True

    ncol = arr.shape[1]
    pts = arr[:, :3].astype(np.float64)
    intensity = None
    colors = None
    labels = None
    if ncol == 6:
        tail = arr[:, 3:6]
        if float(np.nanmin(tail)) >= 0.0 and float(np.nanmax(tail)) > 1.5:
            colors = tail.astype(np.float64)
    elif ncol == 7:
        intensity = arr[:, 6].astype(np.float64)
    elif ncol >= 8:
        intensity = arr[:, 6].astype(np.float64)
        labels = arr[:, 7].astype(np.float64)

    if (intensity is None or float(np.nanmax(intensity)) < 1e-6) and colors is not None:
        lum = 0.299 * colors[:, 0] + 0.587 * colors[:, 1] + 0.114 * colors[:, 2]
        if float(np.nanmax(lum)) > 1e-6:
            intensity = lum

    # Filter non-finite rows once on XYZ and apply the same mask to every
    # channel so intensity / colors / labels stay row-aligned with points.
    finite = np.isfinite(pts).all(axis=1)
    if not finite.all():
        pts = pts[finite]
        if intensity is not None: intensity = intensity[finite]
        if colors is not None: colors = colors[finite]
        if labels is not None: labels = labels[finite]
    pts = validate_xyz(pts, path.name)
    cloud = make_vertex_cloud(pts, intensity=intensity, colors_raw=colors)
    meta = {
        "format": path.suffix.lower(),
        "columns": int(ncol),
        "delimiter": "whitespace" if delim is None else repr(delim),
        "header_rows": int(header_rows),
        "point_count": int(len(pts)),
        "original_count": total,
        "subsampled": subsampled,
        "subsample_step": step,
        "bounds_min": pts.min(0).tolist(),
        "bounds_max": pts.max(0).tolist(),
        "has_intensity": intensity is not None,
        "has_colors": colors is not None,
        "has_labels": labels is not None,
    }
    bundle = PointCloudBundle(
        points=pts, intensity=intensity, colors_raw=colors, path=fp, cloud=cloud,
        metadata=meta,
    )
    if labels is not None:
        bundle.metadata["labels"] = labels
    return bundle

class BaseLayer:
    def load_scan(self, fp: str, max_points: int = MAX_POINTS_DEFAULT) -> PointCloudBundle:
        sfx = Path(fp).suffix.lower()
        if sfx in {".las", ".laz"}: return _read_las(fp, max_points=max_points)
        if sfx == ".ply": return _read_ply(fp)
        if sfx in {".txt", ".xyz", ".pts", ".csv", ".asc"}:
            return _read_txt(fp, max_points=max_points)
        raise ValueError(f"Unsupported format: {sfx}")

    def get_point_count(self, fp: str) -> int:
        """Get total point count without loading full file."""
        sfx = Path(fp).suffix.lower()
        if sfx in {".las", ".laz"} and laspy is not None:
            try:
                las = laspy.read(fp)
                return len(las.x)
            except Exception:
                return -1
        return -1


