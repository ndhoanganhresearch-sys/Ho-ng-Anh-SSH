## 4. Data Preprocessing and Three-Stage Denoising

Raw tunnel scans contain 5–30% non-structural points. The preprocessing layer (`preprocessing.py`) reduces the cloud to clean lining points through a fixed sequence: range crop, voxel downsampling, and a three-stage cascaded denoising algorithm. The cascade requires no labelled training data and is the first principal contribution of this study.

### 4.1 Range crop and downsampling

Ingestion is followed by a range crop that discards returns beyond a working radius, with a default limit of 20 m. The function `range_crop` supports three distance references: Euclidean distance from the sensor origin, distance from the cloud centroid, and radial distance from the principal axis of the cloud. The axis mode suits the tube geometry of a tunnel, where distant returns from adjacent chambers or portal openings are far in radius but not in axial position. Voxel downsampling (`voxel_downsample`, default leaf size 0.05 m) then enforces uniform spacing, which both bounds memory for large surveys and stabilises the neighbourhood statistics used by the cascade.

### 4.2 Stage 1 — morphological classification

The first stage, `semantic_noise_removal`, classifies each point from the geometry of its local neighbourhood. For every point the *k* = 20 nearest neighbours are gathered and their covariance is decomposed into eigenvalues *λ*₁ ≥ *λ*₂ ≥ *λ*₃ ≥ 0. Two normalised shape descriptors follow:

$$ L = \frac{\lambda_1 - \lambda_2}{\lambda_1 + \lambda_2 + \lambda_3}, \qquad S = \frac{\lambda_3}{\lambda_1 + \lambda_2 + \lambda_3} \tag{1} $$

where *L* is linearity and *S* is sphericity. Cables and conduit produce highly linear neighbourhoods, so points with *L* ≥ 0.30 are flagged as cable clutter; an additional ratio test *λ*₂ ⁄ *λ*₁ < 0.15 rejects elongated lining patches that would otherwise be misclassified. Lighting fixtures and other compact objects produce near-spherical neighbourhoods, so points with *S* ≥ 0.12 and a local extent below 0.20 m are flagged as fixture clutter. Personnel are removed by clustering planar points (planarity above 0.4) with DBSCAN [26] (*ε* = 0.15 m, minimum 5 samples) and rejecting clusters whose height falls in 1.2–2.2 m and whose width is below 0.8 m, the envelope of a standing person.

### 4.3 Stage 2 — radial robust statistics

The lining of a tunnel section forms a tight band of radii about a central value. The second stage exploits this by working in the cylindrical frame of the dominant principal axis, dividing the cloud into 0.5 m axial slices and, within each slice, comparing every point's radius *r* to the slice median *R*~med~. A robust scatter estimate uses the median absolute deviation:

$$ \tau = k_\sigma \cdot 1.4826 \cdot \mathrm{MAD}(r), \qquad k_\sigma = 2.5 \tag{2} $$

The constant 1.4826 converts the MAD to a standard-deviation-equivalent under a Gaussian model, and *k*~σ~ sets the acceptance width. A point is retained when

$$ |r - R_\text{med}| \le \tau \quad \text{and} \quad r \ge 0.40\,R_\text{med} \tag{3} $$

The first condition rejects radial outliers; the second removes interior returns, such as equipment near the tunnel axis, that lie far inside the lining band. Operating per slice keeps the test local, so it adapts to a tunnel whose radius changes along its length.

### 4.4 Stage 3 — wall-mounted protrusion detection

Cable trays run continuously along the wall and present a linear, planar signature that can survive the first two stages. The third stage, `_detect_wall_protrusion`, builds a cylindrical occupancy grid of 60 axial by 180 angular cells and estimates the local wall radius as the 90th percentile of point radii within each angular column. Points protruding inward by more than 0.05 m relative to this envelope are candidates for removal. A protrusion is confirmed as a fixture only when it persists across at least three axial cells, the axial-continuity test that distinguishes a continuous cable run from incidental lining roughness.

### 4.5 Safety guard

Each classifier could, on atypical geometry, flag a large fraction of structural points. A safety guard caps any single class at 30% of the cloud: if a gate would remove more than this fraction, it is disabled and a warning is recorded rather than risking destruction of the lining. This guard makes the cascade safe to run unattended, which is a precondition for batch processing of large tunnel networks.

The three stages run in the order above inside `auto_denoise`. On the labelled synthetic case (Section 11), the cascade removed 82.6% of injected clutter (noise recall 0.826) while retaining 99.99% of tunnel lining points, with precision 1.00 and F1 0.90.
