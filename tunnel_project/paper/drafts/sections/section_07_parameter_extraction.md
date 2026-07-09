## 7. Parameter Extraction

From each extracted section the parameter layer (`parameters.py`) computes the deformation metrics that drive the assessment: crown settlement, lateral convergence, ovality, eccentricity, and clearance. Every metric uses a percentile rather than an extremum, because a single stray point corrupts a maximum but barely moves a high percentile.

### 7.1 Crown settlement

Crown settlement is the downward movement of the section apex. Within a section, the apex height is the 99th percentile of the vertical projection, and settlement is its drop relative to the reference epoch:

$$ \delta_v = \mathrm{p99}\big( (S_0 - C)\cdot B \big) - \mathrm{p99}\big( (S_n - C)\cdot B \big) \tag{8} $$

where *S*₀ and *S~n~* are the section points at the reference and current epochs, *C* the section centre, and *B* the vertical Frenet axis. A positive *δ~v~* denotes settlement. The 99th percentile stands in for the apex because, on field data, a stray reflection above the lining corrupts a literal maximum to spurious values on the order of a metre.

### 7.2 Lateral convergence

Convergence is the narrowing of the section across its lateral axis. The section width is the spread of the lateral projection between its 1st and 99th percentiles, and convergence is the reduction of that width relative to the reference:

$$ \delta_h = w_0 - w_n, \qquad w = \mathrm{p99}(d\cdot N) - \mathrm{p1}(d\cdot N) \tag{9} $$

with *d* = *S* − *C* and *N* the lateral axis. Using the p99–p1 span rather than the max–min span makes the width resistant to isolated outliers on either wall.

### 7.3 Ovality

Ovality quantifies departure from circularity. A direct least-squares ellipse is fitted to the section points by the method of Fitzgibbon et al. [20], which returns a stable fit under heterogeneous point density because it minimises an algebraic distance subject to an ellipse-specific constraint rather than iterating. From the fitted semi-axes *a* ≥ *b*,

$$ O = \frac{a - b}{a} \times 100\% \tag{10} $$

When the constrained fit fails on a degenerate section, the implementation falls back to the axis-aligned extents.

### 7.4 Eccentricity

Eccentricity measures lateral drift of the section centre away from the design axis. With a reference epoch, it is the distance between the measured and design centres. Without a reference, the implementation derives it from geometry alone: a circle is fitted to each section to obtain its centre (*c~x~*, *c~y~*), a baseline trajectory is formed by a moving median of the centres along the tunnel (window fraction 0.10), and eccentricity is the deviation from that baseline,

$$ e = 1000\,\sqrt{(c_x - \bar{c}_x)^2 + (c_y - \bar{c}_y)^2} \ \ \text{[mm]} \tag{11} $$

where (*c̄~x~*, *c̄~y~*) is the moving-median baseline. Detrending against the baseline separates real lateral drift from the gentle wander of the fitted centerline. A 5-point median filter then suppresses single-section spikes, since a genuine defect spans at least three consecutive sections, and a coverage guard skips sections with fewer than 17 of 24 occupied angular bins so that incomplete rings do not generate false eccentricity.

### 7.5 Clearance

Clearance checks whether the lining intrudes into the design envelope reserved for traffic. For a circular profile the signed clearance of a point is its radial distance minus the design envelope radius; for a box profile it is the signed distance to the nearest envelope face. A section is flagged as a violation when the 1st percentile of its signed clearance falls below zero, so that a real intrusion affecting at least 1% of the section triggers a warning while a lone stray point does not. On the labelled intrusion case, the check achieved 100% precision and 100% recall against ground-truth intrusion points (Section 11).

### 7.6 Output assembly

The per-section metrics are aggregated into the global `parameters` dictionary (mean ovality, mean eccentricity, peak crown settlement, peak convergence) and retained per section for export. These values feed the change-detection warnings of Section 8, the outputs of Section 10, and the assessment assistant of Section 9.
