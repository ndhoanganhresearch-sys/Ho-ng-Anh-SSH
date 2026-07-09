## 5. Multi-Scan Registration

Multi-station and multi-epoch surveys produce clouds in different coordinate frames. Registration (`registration.py`) aligns them to a common reference through a coarse-to-fine fallback chain that selects the strongest available method for the data at hand. The chain is implemented in `register_epochs`.

### 5.1 Method selection

The pipeline prefers the most constrained method the scene supports and falls back when its preconditions are not met. When survey targets are detected, a target-based rigid transform is used directly. Without targets, the pipeline computes a feature-based coarse alignment, refines it with generalised ICP, and validates the result against a divergence guard. The final transform is the one with the lowest root-mean-square error among the as-is, coarse, and refined candidates, which prevents a failed refinement from degrading an already adequate alignment.

### 5.2 Target-based alignment

When at least three targets are matched between clouds, their centres define a rigid transform recovered in closed form by the Horn singular-value-decomposition solution, with correspondences accepted within a 2.0 m gate. This path is exact up to target-centroiding error and is preferred wherever targets exist, as is standard in surveying practice.

### 5.3 Feature-based coarse alignment

Without targets, the clouds are downsampled to a working resolution derived from their extent (cloud span divided by 600, clipped to 0.02–0.12 m) and described by Fast Point Feature Histograms [22]. Mutual nearest neighbours in the 33-dimensional feature space form candidate correspondences. These candidates contain many false matches, so a graph-based reliable outlier removal step [23] retains only a mutually consistent set: correspondences whose pairwise distances are preserved within tolerance form a consistency graph, and the largest star-consistent subset seeded from the highest-degree node is kept. The surviving correspondences yield a coarse transform by the Umeyama estimator. This stage provides an initial guess robust enough for fine registration to converge.

### 5.4 Fine registration

Refinement uses Generalised ICP, which models each local neighbourhood as a Gaussian and minimises a plane-to-plane cost well suited to the planar walls of a tunnel [12]. The primary backend is the parallel small_gicp implementation of voxelised GICP [24]; when it is unavailable the pipeline falls back to a two-stage point-to-plane ICP in Open3D [25], a coarse pass at six times the voxel size followed by a fine pass at 1.5 times, with relative fitness and RMSE tolerances tightened from 10⁻⁵ to 10⁻⁷ between stages. Both backends report the final RMSE in millimetres.

### 5.5 Trimmed ICP and divergence guard

Partial overlap and residual clutter can bias a least-squares fit toward non-corresponding points. A trimmed ICP variant addresses this by keeping only the best-matched fraction of correspondences at each iteration. The keep fraction defaults to 0.80, clipped to the range 0.4–0.98, and the iteration stops when the RMSE change falls below 10⁻⁶ or after 25 iterations. Because the chain selects the minimum-RMSE transform across all candidates, a refinement that diverges on difficult geometry cannot worsen the output: the guard falls back to the coarse or as-is alignment. On a straight reference tunnel, GICP recovered a 1.2° yaw and 7 cm translation perturbation to an RMSE of 0.198 mm, 20 to 61 times faster than the Open3D point-to-plane baseline (Section 11).
