"""
SSL Smart Tunnel Monitoring System - PyVista 3D View Manager.

This module owns all 3D visualization logic for the tunnel monitoring app:

- Revit-like light viewport.
- Trackball camera navigation.
- Scroll zoom, middle-button pan, Shift + middle-button orbit.
- Intensity mapped to the Viridis colormap.
- Level-of-detail preprocessing for multi-million-point Faro Focus scans.
- Strict 1:1:1 axis scaling to prevent tunnel distortion.

The GUI layer should call ViewManager.update_view(...) and should not create
PyVista actors directly.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import List, Optional, Sequence, Tuple

os.environ["VTK_TK_WIDGET_PATH"] = ""
os.environ["VTK_DISABLE_TK_WIDGET"] = "1"
os.environ.setdefault("QT_API", "pyside6")

import numpy as np
import pyvista as pv
import vtk

from tunnel_utils import normalize_colors, validate_xyz, voxel_downsample


@dataclass
class ViewConfig:
    """Runtime parameters for the PyVista viewport."""

    title: str = "SSL Smart Tunnel Monitoring System - 4D LiDAR"
    background: str = "#FFFFFF"
    foreground: str = "#111827"
    colormap: str = "viridis"
    point_size: float = 2.0
    render_budget_points: int = 650_000
    hard_cap_points: int = 900_000
    default_voxel_size: float = 0.05
    min_voxel_size: float = 0.01
    max_voxel_size: float = 0.25
    fast_threshold_percentile: Tuple[float, float] = (0.5, 99.5)
    show_axes: bool = True
    show_bounds: bool = True


class RevitTrackballStyle(vtk.vtkInteractorStyleTrackballCamera):
    """
    VTK interactor style tuned for Revit-like navigation.

    Controls:
        - Mouse wheel: zoom, inherited from vtkInteractorStyleTrackballCamera.
        - Middle mouse: pan.
        - Shift + middle mouse: orbit/rotate.

    PyVista's default trackball style already gives strong camera behavior.
    This subclass only overrides middle-button behavior so operators can pan
    without fighting the camera while still orbiting with Shift + middle drag.
    """

    def __init__(self) -> None:
        super().__init__()
        self._middle_mode: Optional[str] = None

    def OnMiddleButtonDown(self) -> None:  # noqa: N802 - VTK override name
        interactor = self.GetInteractor()
        if interactor is not None and interactor.GetShiftKey():
            self._middle_mode = "rotate"
            self.StartRotate()
        else:
            self._middle_mode = "pan"
            self.StartPan()

    def OnMiddleButtonUp(self) -> None:  # noqa: N802 - VTK override name
        if self._middle_mode == "rotate":
            self.EndRotate()
        elif self._middle_mode == "pan":
            self.EndPan()
        self._middle_mode = None


class ViewManager:
    """
    Production PyVista manager for SSL tunnel point-cloud visualization.

    Typical use:

        manager = ViewManager()
        manager.update_view(points, intensity=intensity)

    For GUI embedding, create the plotter externally and pass it through the
    constructor. For a standalone viewer, leave plotter=None.
    """

    def __init__(
        self,
        plotter: Optional[pv.Plotter] = None,
        config: Optional[ViewConfig] = None,
    ) -> None:
        self.config = config or ViewConfig()
        self.plotter = plotter or pv.Plotter(title=self.config.title)
        self.cloud_actor = None
        self.scalar_bar_actor = None
        self.current_mesh: Optional[pv.PolyData] = None
        self.target_label_actors: List[object] = []
        self.original_point_count = 0
        self.rendered_point_count = 0

        self._configure_plotter()

    def _configure_plotter(self) -> None:
        """Apply light style, axes, camera behavior, and Revit-like controls."""

        pv.global_theme.background = self.config.background
        pv.global_theme.font.color = self.config.foreground

        self.plotter.set_background(self.config.background)
        self.plotter.enable_trackball_style()
        self.plotter.set_scale(1.0, 1.0, 1.0)

        if self.config.show_axes:
            self.plotter.add_axes(
                line_width=2,
                labels_off=False,
                color=self.config.foreground,
            )

        self._install_revit_controls()

    def _install_revit_controls(self) -> None:
        """Install the custom VTK interactor style."""

        style = RevitTrackballStyle()
        renderer = self.plotter.renderer
        if renderer is not None:
            style.SetDefaultRenderer(renderer)

        iren = getattr(self.plotter, "iren", None)
        interactor = getattr(iren, "interactor", None)
        if interactor is None and iren is not None and hasattr(iren, "SetInteractorStyle"):
            interactor = iren
        if interactor is not None:
            interactor.SetInteractorStyle(style)
        self._revit_style = style

    def update_view(
        self,
        points: np.ndarray,
        intensity: Optional[np.ndarray] = None,
        colors: Optional[np.ndarray] = None,
        title: str = "Tunnel Point Cloud",
        reset_camera: bool = True,
    ) -> pv.PolyData:
        """
        Load or refresh the visible point cloud.

        The LOD pipeline is intentionally fast:
            1. Validate finite XYZ.
            2. Build a PyVista PolyData and run fast_threshold on a lightweight
               spatial scalar to remove extreme scan tails/outliers.
            3. Voxel-downsample if the cloud is still above the render budget.
            4. Apply a hard cap to protect interactive camera rotation.

        Args:
            points: Nx3 XYZ points in meters.
            intensity: Optional N intensity values. Rendered with Viridis.
            colors: Optional Nx3 RGB colors, used only if intensity is absent.
            title: View title shown in the corner.
            reset_camera: Center and frame the model after loading.

        Returns:
            The rendered PyVista mesh.
        """

        xyz = validate_xyz(points)
        self.original_point_count = int(len(xyz))
        safe_intensity = self._prepare_scalar(intensity, len(xyz), "intensity")
        safe_colors = normalize_colors(colors)
        if safe_colors is not None and len(safe_colors) != len(xyz):
            safe_colors = None

        xyz, safe_intensity, safe_colors = self._fast_threshold_lod(
            xyz,
            safe_intensity,
            safe_colors,
        )
        xyz, safe_intensity, safe_colors = self._voxel_lod(
            xyz,
            safe_intensity,
            safe_colors,
        )
        xyz, safe_intensity, safe_colors = self._hard_cap_lod(
            xyz,
            safe_intensity,
            safe_colors,
        )

        mesh = self._build_mesh(xyz, safe_intensity, safe_colors)
        self._render_mesh(mesh, title, reset_camera=reset_camera)
        self.current_mesh = mesh
        self.rendered_point_count = int(mesh.n_points)
        return mesh

    def point_cloud_mesh(
        self,
        points: np.ndarray,
        scalars: Optional[np.ndarray] = None,
        colors: Optional[np.ndarray] = None,
        downsample: bool = True,
    ) -> pv.PolyData:
        """
        Build a PyVista point-cloud mesh for overlay layers.

        The main cloud should be loaded through update_view(). This helper is
        for sidebar-controlled layers such as heatmaps and AI detections.
        """

        xyz = validate_xyz(points)
        safe_scalars = self._prepare_scalar(scalars, len(xyz), "scalars") if scalars is not None else None
        safe_colors = normalize_colors(colors)
        if safe_colors is not None and len(safe_colors) != len(xyz):
            safe_colors = None
        if downsample:
            xyz, safe_scalars, safe_colors = self._voxel_lod(xyz, safe_scalars, safe_colors)
            xyz, safe_scalars, safe_colors = self._hard_cap_lod(xyz, safe_scalars, safe_colors)

        mesh = self._clean_point_polydata(xyz)
        if safe_scalars is not None and len(safe_scalars) == len(xyz):
            mesh["scalars"] = safe_scalars
        elif safe_colors is not None and len(safe_colors) == len(xyz):
            mesh["RGB"] = (np.clip(safe_colors, 0.0, 1.0) * 255).astype(np.uint8)
        return mesh

    def clear(self) -> None:
        """Clear the viewport without replacing the configured interactor."""

        self.plotter.clear()
        self.target_label_actors = []
        self.plotter.set_background(self.config.background)
        self.plotter.set_scale(1.0, 1.0, 1.0)
        if self.config.show_axes:
            self.plotter.add_axes(color=self.config.foreground)

    def label_targets(self, target_centroids: Sequence[Sequence[float]]) -> List[object]:
        """
        Label target centroids by station and tunnel position.

        Targets are sorted by stationing (Y). Each consecutive group of three
        is treated as one station: highest Z becomes Crown, and the two wall
        targets are assigned Left/Right by their X positions.
        """

        for actor in self.target_label_actors:
            try:
                self.plotter.remove_actor(actor, reset_camera=False, render=False)
            except Exception:
                pass
        self.target_label_actors = []

        if target_centroids is None or len(target_centroids) == 0:
            self.plotter.render()
            return []

        xyz = validate_xyz(np.asarray(target_centroids, dtype=np.float64), "target_centroids")
        order = np.lexsort((xyz[:, 0], xyz[:, 2], xyz[:, 1]))
        sorted_xyz = xyz[order]
        station_groups = [sorted_xyz[index : index + 3] for index in range(0, len(sorted_xyz), 3)]

        crown_points = []
        crown_labels = []
        wall_points = []
        wall_labels = []

        for station_index, group in enumerate(station_groups, start=1):
            if len(group) < 3:
                continue

            crown_idx = int(np.argmax(group[:, 2]))
            wall_indices = [index for index in range(len(group)) if index != crown_idx]
            wall_indices.sort(key=lambda index: group[index, 0])

            crown_points.append(group[crown_idx])
            crown_labels.append(f"S{station_index}-Crown")
            wall_points.extend([group[wall_indices[0]], group[wall_indices[-1]]])
            wall_labels.extend([f"S{station_index}-Left", f"S{station_index}-Right"])

        if crown_points:
            actor = self.plotter.add_point_labels(
                np.asarray(crown_points, dtype=np.float64),
                crown_labels,
                text_color="#FF4F4F",
                point_color="#FF4F4F",
                font_size=14,
                point_size=10,
                shape="rounded_rect",
                shape_color="#1B0A0A",
                shape_opacity=0.85,
                always_visible=True,
                reset_camera=False,
                render=False,
                name="target_crown_labels",
            )
            self.target_label_actors.append(actor)

        if wall_points:
            actor = self.plotter.add_point_labels(
                np.asarray(wall_points, dtype=np.float64),
                wall_labels,
                text_color="#35E27A",
                point_color="#35E27A",
                font_size=13,
                point_size=8,
                shape="rounded_rect",
                shape_color="#071B10",
                shape_opacity=0.85,
                always_visible=True,
                reset_camera=False,
                render=False,
                name="target_wall_labels",
            )
            self.target_label_actors.append(actor)

        self.plotter.render()
        return self.target_label_actors

    def show(self, interactive: bool = True) -> None:
        """Open the PyVista render window."""

        self.plotter.show(interactive=interactive)

    def show_registered_clouds(
        self,
        source_points: np.ndarray,
        target_points: np.ndarray,
        title: str = "SVD/ICP Registration QA",
    ) -> None:
        """Visual QA helper for source and target station alignment."""

        source = validate_xyz(source_points)
        target = validate_xyz(target_points)
        source, _, _ = self._hard_cap_lod(source, None, None)
        target, _, _ = self._hard_cap_lod(target, None, None)

        self.clear()
        self.plotter.add_mesh(
            self._clean_point_polydata(target),
            color="#00FF9C",
            style="points",
            point_size=self.config.point_size,
            render_points_as_spheres=False,
            reset_camera=True,
        )
        self.plotter.add_mesh(
            self._clean_point_polydata(source),
            color="#00C4FF",
            style="points",
            point_size=self.config.point_size,
            render_points_as_spheres=False,
            reset_camera=True,
        )
        self._finalize_camera(title, reset_camera=True)

    def show_deformation_heatmap(
        self,
        points: np.ndarray,
        delta_mm: np.ndarray,
        title: str = "4D Deformation Heatmap",
        warning_mm: float = 3.0,
    ) -> pv.PolyData:
        """Render deformation deltas with the project traffic-light thresholds."""

        values = np.asarray(delta_mm, dtype=np.float64).reshape(-1)
        if len(values) != len(points):
            raise ValueError("delta_mm length must match points length.")
        caution_mm = max(1.0, float(warning_mm) / 3.0)
        colors = np.zeros((len(values), 3), dtype=np.float64)
        colors[values < caution_mm] = np.array([0.0, 0.75, 0.20])
        colors[(values >= caution_mm) & (values < warning_mm)] = np.array([1.0, 0.85, 0.0])
        colors[values >= warning_mm] = np.array([1.0, 0.05, 0.02])

        return self.update_view(
            points=points,
            intensity=None,
            colors=colors,
            title=title,
            reset_camera=True,
        )

    def _fast_threshold_lod(
        self,
        xyz: np.ndarray,
        intensity: Optional[np.ndarray],
        colors: Optional[np.ndarray],
    ) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Use PyVista fast_threshold to remove extreme spatial tails.

        For long tunnel scans, rare far-away points can inflate the bounding box
        and hurt camera precision. A normalized radial-distance scalar keeps the
        main tunnel body and removes only percentile-defined extremes.
        """

        if len(xyz) <= self.config.render_budget_points:
            return xyz, intensity, colors

        center = np.median(xyz, axis=0)
        radius = np.linalg.norm(xyz - center, axis=1)
        low_pct, high_pct = self.config.fast_threshold_percentile
        low = float(np.percentile(radius, low_pct))
        high = float(np.percentile(radius, high_pct))

        mesh = self._clean_point_polydata(xyz)
        mesh["lod_radius"] = radius
        mesh["source_index"] = np.arange(len(xyz), dtype=np.int64)
        thresholded = mesh.fast_threshold((low, high), scalars="lod_radius", preference="point")

        if thresholded.n_points == 0:
            return xyz, intensity, colors

        kept = np.asarray(thresholded["source_index"], dtype=np.int64)
        out_xyz = np.asarray(thresholded.points, dtype=np.float64)
        out_intensity = intensity[kept] if intensity is not None and len(intensity) == len(xyz) else None
        out_colors = colors[kept] if colors is not None and len(colors) == len(xyz) else None
        return out_xyz, out_intensity, out_colors

    def _voxel_lod(
        self,
        xyz: np.ndarray,
        intensity: Optional[np.ndarray],
        colors: Optional[np.ndarray],
    ) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray]]:
        """Voxel-downsample clouds above the target render budget."""

        if len(xyz) <= self.config.render_budget_points:
            return xyz, intensity, colors

        voxel_size = self._estimate_voxel_size(xyz, len(xyz), self.config.render_budget_points)

        # Preserve intensity through downsampling by passing it as grayscale RGB
        # only when RGB is unavailable; scalar values are then re-estimated by
        # nearest source index after the geometric downsample.
        down_xyz, down_colors = voxel_downsample(
            xyz,
            colors,
            voxel_size=voxel_size,
            max_points=self.config.hard_cap_points,
        )

        down_intensity = None
        if intensity is not None and len(down_xyz) > 0:
            down_intensity = self._nearest_scalar_transfer(xyz, intensity, down_xyz)

        return down_xyz, down_intensity, down_colors

    def _hard_cap_lod(
        self,
        xyz: np.ndarray,
        intensity: Optional[np.ndarray],
        colors: Optional[np.ndarray],
    ) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray]]:
        """Final deterministic point cap for smooth camera interaction."""

        if len(xyz) <= self.config.hard_cap_points:
            return xyz, intensity, colors

        step = int(np.ceil(len(xyz) / self.config.hard_cap_points))
        idx = np.arange(0, len(xyz), step, dtype=np.int64)[: self.config.hard_cap_points]
        out_xyz = xyz[idx]
        out_intensity = intensity[idx] if intensity is not None and len(intensity) == len(xyz) else None
        out_colors = colors[idx] if colors is not None and len(colors) == len(xyz) else None
        return out_xyz, out_intensity, out_colors

    def _estimate_voxel_size(self, xyz: np.ndarray, point_count: int, target_count: int) -> float:
        """Estimate voxel size from bounding volume and desired point budget."""

        bounds_min = np.min(xyz, axis=0)
        bounds_max = np.max(xyz, axis=0)
        extent = np.maximum(bounds_max - bounds_min, self.config.min_voxel_size)
        volume = float(np.prod(extent))
        if volume <= 0.0 or point_count <= target_count:
            return self.config.default_voxel_size

        target_density = target_count / volume
        voxel_size = (1.0 / max(target_density, 1e-12)) ** (1.0 / 3.0)
        voxel_size = max(voxel_size, self.config.default_voxel_size)
        return float(np.clip(voxel_size, self.config.min_voxel_size, self.config.max_voxel_size))

    def _nearest_scalar_transfer(
        self,
        source_xyz: np.ndarray,
        source_values: np.ndarray,
        query_xyz: np.ndarray,
    ) -> np.ndarray:
        """
        Transfer scalar values after voxel downsampling.

        Uses VTK's point locator through PyVista, avoiding a mandatory SciPy
        dependency in the viewer layer.
        """

        source = self._clean_point_polydata(source_xyz)
        source["scalar_source"] = source_values
        target = self._clean_point_polydata(query_xyz)
        sampled = target.sample(source, pass_point_data=True)
        values = sampled.get_array("scalar_source")
        if values is None or len(values) != len(query_xyz):
            stride = max(1, len(source_values) // max(1, len(query_xyz)))
            return source_values[::stride][: len(query_xyz)].astype(np.float64)
        return np.asarray(values, dtype=np.float64)

    def _build_mesh(
        self,
        xyz: np.ndarray,
        intensity: Optional[np.ndarray],
        colors: Optional[np.ndarray],
    ) -> pv.PolyData:
        """Create the final render mesh."""

        mesh = self._clean_point_polydata(xyz)
        if intensity is not None and len(intensity) == len(xyz):
            mesh["Intensity"] = np.asarray(intensity, dtype=np.float64)
        elif colors is not None and len(colors) == len(xyz):
            mesh["RGB"] = (np.clip(colors, 0.0, 1.0) * 255).astype(np.uint8)
        else:
            mesh["Intensity"] = np.linspace(0.0, 1.0, len(xyz), dtype=np.float64)
        return mesh

    def _clean_point_polydata(self, points: np.ndarray) -> pv.PolyData:
        """
        Create a vertex-only PolyData cloud from XYZ coordinates.

        Some LAS/PLY sources can carry mesh-like connectivity metadata.  The
        viewer only wants point clouds, so this creates a fresh PolyData, drops
        any faces/lines/strips, and explicitly stores one VTK vertex per point.
        """

        xyz = validate_xyz(points)
        points_array = np.ascontiguousarray(xyz, dtype=np.float64)
        point_cloud = pv.PolyData(points_array)
        if hasattr(point_cloud, "clear_data"):
            point_cloud.clear_data()
        if hasattr(point_cloud, "clear_cells"):
            point_cloud.clear_cells()
        point_cloud.points = points_array

        empty = np.empty(0, dtype=np.int64)
        for attr in ("faces", "lines", "strips"):
            try:
                setattr(point_cloud, attr, empty)
            except Exception:
                pass

        num_points = len(points_array)
        vertex_cells = np.hstack(
            [
                np.ones((num_points, 1), dtype=np.int64),
                np.arange(num_points, dtype=np.int64).reshape(-1, 1),
            ]
        )
        flat_vertex_cells = vertex_cells.ravel()
        try:
            point_cloud.verts = vertex_cells
        except Exception:
            try:
                point_cloud.verts = pv.CellArray(flat_vertex_cells)
            except Exception:
                point_cloud.verts = flat_vertex_cells

        if point_cloud.n_cells != num_points:
            try:
                point_cloud.verts = pv.CellArray(flat_vertex_cells)
            except Exception:
                point_cloud.verts = flat_vertex_cells

        return point_cloud

    def _render_mesh(self, mesh: pv.PolyData, title: str, reset_camera: bool) -> None:
        """Draw the cloud actor and restore exact scaling."""

        self.clear()
        scalar_bar_args = {
            "title": "Intensity",
            "title_font_size": 13,
            "label_font_size": 11,
            "color": self.config.foreground,
        }

        if "Intensity" in mesh.array_names:
            self.cloud_actor = self.plotter.add_mesh(
                mesh,
                scalars="Intensity",
                cmap=self.config.colormap,
                style="points",
                point_size=self.config.point_size,
                render_points_as_spheres=False,
                reset_camera=reset_camera,
                scalar_bar_args=scalar_bar_args,
            )
        elif "RGB" in mesh.array_names:
            self.cloud_actor = self.plotter.add_mesh(
                mesh,
                scalars="RGB",
                rgb=True,
                style="points",
                point_size=self.config.point_size,
                render_points_as_spheres=False,
                reset_camera=reset_camera,
            )
        else:
            self.cloud_actor = self.plotter.add_mesh(
                mesh,
                color="#D8E8F2",
                style="points",
                point_size=self.config.point_size,
                render_points_as_spheres=False,
                reset_camera=reset_camera,
            )

        self._finalize_camera(title, reset_camera=reset_camera)

    def _finalize_camera(self, title: str, reset_camera: bool) -> None:
        """Apply title, 1:1:1 scale, bounds, and centered camera."""

        self.plotter.set_scale(1.0, 1.0, 1.0)
        self.plotter.add_text(
            title,
            position="upper_left",
            font_size=11,
            color=self.config.foreground,
            name="viewport_title",
        )

        if self.config.show_bounds:
            self.plotter.show_bounds(
                grid="front",
                location="outer",
                all_edges=False,
                color="#5E7F93",
                font_size=8,
            )

        self.plotter.camera.parallel_projection = True
        self.plotter.view_isometric()
        if reset_camera:
            self.plotter.reset_camera()
        self.plotter.render()

    def _prepare_scalar(
        self,
        values: Optional[np.ndarray],
        expected_length: int,
        name: str,
    ) -> Optional[np.ndarray]:
        """Validate and clean scalar arrays such as intensity or delta_mm."""

        if values is None:
            return None
        arr = np.asarray(values, dtype=np.float64).reshape(-1)
        if len(arr) != expected_length:
            raise ValueError(f"{name} length must match points length.")
        finite = np.isfinite(arr)
        if finite.all():
            return arr
        cleaned = arr.copy()
        fallback = float(np.nanmedian(cleaned[finite])) if finite.any() else 0.0
        cleaned[~finite] = fallback
        return cleaned


__all__ = ["RevitTrackballStyle", "ViewConfig", "ViewManager"]
