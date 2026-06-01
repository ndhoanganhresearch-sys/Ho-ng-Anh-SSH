from .common import *
# ------------------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------------------

@dataclass
class PointCloudBundle:
    points:     np.ndarray
    intensity:  Optional[np.ndarray] = None
    colors_raw: Optional[np.ndarray] = None
    path:       Optional[str]        = None
    metadata:   Dict[str, object]    = field(default_factory=dict)
    cloud:      Optional[object]     = None

@dataclass
class SectionGeometry:
    chainage:       float = 0.0
    center_3d:      Optional[np.ndarray] = None
    pts_2d:         Optional[np.ndarray] = None   
    labels:         Optional[np.ndarray] = None   
    H1:             float = float("nan")          
    H2:             float = float("nan")          
    H3:             float = float("nan")          
    W1:             float = float("nan")          
    W2:             float = float("nan")          
    C1:             float = float("nan")          
    C2:             float = float("nan")          
    C3:             float = float("nan")          
    wall_angle_L:   float = float("nan")          
    wall_angle_R:   float = float("nan")          
    radius_fit:     float = float("nan")          
    eccentricity:   float = float("nan")          
    ovality:        float = float("nan")          
    clearance_violation: bool = False
    min_clearance_dist:  float = float("nan")

@dataclass
class PipelineContext:
    scans:              List[PointCloudBundle]   = field(default_factory=list)
    active_index:       int                      = -1
    normalized_points:  Optional[np.ndarray]     = None
    registered_points:  Optional[np.ndarray]     = None
    centerline:         Optional[np.ndarray]     = None
    centerline_smooth:  Optional[np.ndarray]     = None
    frenet_frames:      List[Dict[str, np.ndarray]] = field(default_factory=list)
    parameters:         Dict[str, float]         = field(default_factory=dict)
    heatmap_scalars:    Optional[np.ndarray]     = None
    time_series_plot:   Optional[np.ndarray]     = None
    m3c2_result:        Optional[Dict[str, np.ndarray]] = None
    rmse_mm:            Optional[float]          = None
    polar_map:          Optional[np.ndarray]     = None
    polar_angles:       Optional[np.ndarray]     = None
    polar_centers:      Optional[np.ndarray]     = None
    sections:           List[SectionGeometry]    = field(default_factory=list)
    design_center:      Optional[np.ndarray]     = None   # design axis center (C_design for eccentricity)
    design_radius:      Optional[float]          = None   # design radius (for polar deformation)
    tunnel_profile:     str                      = "Circle"
    # Component classification counts from auto_denoise (cable/light/person/
    # wall-cable). Stored so downstream (IFC export, reports) can record what
    # non-structural elements were detected; auto_denoise only logged them.
    denoise_stats:      Dict[str, int]           = field(default_factory=dict)
    # Per-class detected non-structural point sets from auto_denoise
    # ("cable"/"light"/"person" -> Nx3 array), used by optional IFC component
    # export. Empty until a denoise pass stores them.
    component_points:   Dict[str, object]        = field(default_factory=dict)

    @property
    def active_scan(self) -> Optional[PointCloudBundle]:
        if 0 <= self.active_index < len(self.scans):
            return self.scans[self.active_index]
        return None

    @property
    def working_points(self) -> Optional[np.ndarray]:
        if self.registered_points is not None:
            return self.registered_points
        if self.normalized_points is not None:
            return self.normalized_points
        s = self.active_scan
        return None if s is None else s.points

    def _aligned_channel(self, channel: str) -> Optional[np.ndarray]:
        """Return a per-point channel (intensity / label) aligned to
        working_points, even after voxel/SOR/lining changed the point count.

        The raw channel lives on the active scan and matches scan.points. When
        working_points are a subset (SOR / lining) or resampled (voxel) cloud,
        the channel is re-attached by nearest-neighbour lookup against the raw
        scan, so intensity/label stay row-aligned with the current points
        instead of being silently dropped on a length mismatch (T2). Returns
        None when the scan has no such channel.
        """
        scan = self.active_scan
        wp = self.working_points
        if scan is None or wp is None:
            return None
        if channel == 'intensity':
            raw = scan.intensity
        else:
            raw = scan.metadata.get('labels') if scan.metadata else None
        if raw is None:
            return None
        raw = np.asarray(raw).ravel()
        base = np.asarray(scan.points, dtype=np.float64)
        if len(raw) != len(base):
            return None
        wp = np.asarray(wp, dtype=np.float64)
        if len(wp) == len(base):
            return raw
        if cKDTree is None:
            return None
        _d, idx = cKDTree(base).query(wp, k=1, workers=-1)
        return raw[idx]

    def working_intensity(self) -> Optional[np.ndarray]:
        """Intensity aligned to working_points (see _aligned_channel)."""
        return self._aligned_channel('intensity')

    def working_labels(self) -> Optional[np.ndarray]:
        """Semantic labels aligned to working_points (see _aligned_channel)."""
        return self._aligned_channel('label')

