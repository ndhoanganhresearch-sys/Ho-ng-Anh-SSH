## 6. Frenet-Frame Geometric Analysis

Cross-section measurements are only meaningful when the cutting plane is orthogonal to the tunnel axis. Slicing perpendicular to a global coordinate axis introduces oblique cuts in curved tunnels, and an oblique cut inflates the apparent radius and ovality [18]. The geometry layer (`geometry.py`) avoids this bias by extracting sections in the local Frenet frame of a fitted centerline. This curvature-correct extraction is the second principal contribution.

### 6.1 Centerline fitting

The centerline is a cubic B-spline through per-chunk geometric centres. The cloud is binned into equal-axial-position chunks, `n_chunks = max(2·section_count, 40)`, and the centre of each chunk is estimated by a circle fit rather than a mass centroid, so that uneven point density on one wall does not pull the axis off-centre. A cubic spline (degree 3, C² continuity) is fitted to these centres with a smoothing weight

$$ s = c \cdot m, \qquad c = 0.5 \tag{4} $$

where *m* is the number of centres and *c* the smoothing factor. The smoothing is necessary: an interpolating spline (*s* = 0) chases every centre and wanders laterally by up to 0.31 m, whereas the smoothed fit reduces the wander to the order of 0.002 m. End chunks whose circle-fit deviation exceeds a robust tolerance are trimmed before fitting, which prevents portal returns from distorting the spline ends.

### 6.2 Circle fitting

Chunk centres and per-section radii use the algebraic least-squares circle fit of Kåsa [21]. For a set of section points (*x*, *y*) in the cutting plane, the fit solves the linear system

$$ \begin{bmatrix} x & y & 1 \end{bmatrix} \begin{bmatrix} 2c_x \\ 2c_y \\ r^2 - c_x^2 - c_y^2 \end{bmatrix} = x^2 + y^2 \tag{5} $$

for the centre (*c*~x~, *c*~y~) and radius *r*. The algebraic form is fast and stable, but it degrades when the section is a short arc rather than a full ring. The implementation therefore guards coverage: a section is accepted only when the occupied angular span exceeds 220° or at least 24 of 36 angular bins are populated. Sections failing this test fall back to a normal-based or centroid-based centre, which keeps sparse or occluded sections from producing spurious geometry.

### 6.3 Gravity-anchored Frenet frames

At each section the orthonormal frame is built from the local tangent. The tangent *T* is the central difference of the centerline, normalised. Rather than the classical Frenet normal, which rotates with curvature and accumulates twist along the axis, the frame is anchored to gravity. A reference direction (global *Z*, or global *X* where the tangent is near-vertical, |*T~z~*| > 0.9999) is projected orthogonal to *T* to give the vertical axis *B*, and the lateral axis *N* completes the right-handed triad:

$$ B = \frac{\hat{z} - (\hat{z}\cdot T)\,T}{\lVert \hat{z} - (\hat{z}\cdot T)\,T \rVert}, \qquad N = B \times T \tag{6} $$

Anchoring to gravity gives every section a consistent vertical and lateral reference, so crown settlement is always measured along *B* and lateral convergence along *N*, independent of how the tunnel curves. In the section plane, a point's lateral coordinate is *d* · *N* and its vertical coordinate is *d* · *B*, where *d* is the offset from the section centre.

### 6.4 Section extraction

Points are assigned to a section when their projection onto the tangent falls within a half-thickness *ε* of the section plane. The thickness adapts to local point density:

$$ \varepsilon = \mathrm{clip}\!\left(0.55 \cdot \mathrm{median}(\Delta),\; 0.05,\; 0.5\right) \ \text{m} \tag{7} $$

where Δ is the set of nearest-neighbour spacings. Tying *ε* to the median spacing keeps each slice thick enough to contain a stable ring of points on sparse scans, while the 0.5 m cap prevents over-thick slices from blurring axial gradients on dense scans. On reference circular geometry, the extracted sections recover a median radius of 4.00002 m against a 4.00000 m design value, an error of 0.0005% (Section 11).
