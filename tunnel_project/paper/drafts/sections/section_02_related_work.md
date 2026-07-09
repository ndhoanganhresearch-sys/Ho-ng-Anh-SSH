## 2. Related Work

Automated tunnel monitoring draws on four research threads: LiDAR-based geometric inspection, point cloud denoising, multi-epoch registration, and AI-assisted structural assessment. Each thread has matured independently. The gap this study addresses lies in their integration.

### 2.1 LiDAR-based tunnel inspection

Terrestrial laser scanning records dense full-section point clouds in a single survey pass, and this capability reshaped how tunnel geometry is documented [6,7]. Early work focused on isolated metrics. Jung et al. [8] fitted circles iteratively to mobile laser scans of precast segments and recovered ovality at the segment scale, showing that geometric defects could be quantified without manual cross-section drawing. Gikas [9] applied least-squares cylinder fitting to successive scans during highway tunnel excavation, tracking convergence over construction stages. Ye et al. [10] coupled 3D semantic segmentation with point cloud processing to localise surface cracks at millimetre scale, and Attard et al. [11] benchmarked five commercial inspection packages, reporting that results varied substantially with the preprocessing each package applied. Fekete et al. [18] documented how oblique slicing in drill-and-blast tunnels distorts the apparent cross-section when the tunnel curves.

The pattern is consistent. Each tool solves one piece of the inspection problem, and each assumes the input cloud already represents only the tunnel lining. That assumption rarely holds in operational tunnels.

### 2.2 Point cloud denoising

The dominant cleaning method in the point cloud literature is statistical outlier removal, which flags points whose mean neighbour distance exceeds a global threshold [17]. The method targets random, Gaussian-distributed noise and isolated stray returns. Cable runs, conduit, and lighting fixtures in a tunnel are neither random nor isolated: they are elongated, locally dense structures mounted against the lining. Geometric classifiers based on local principal component analysis can separate linear from planar neighbourhoods, but published pipelines apply them to terrain or building facades rather than to the closed cylindrical geometry of a tunnel, where the lining itself is a curved surface that confounds a single global threshold. The result is that clutter survives cleaning or, when thresholds are tightened, structural points are removed with it.

### 2.3 Registration for multi-epoch comparison

Comparing scans across epochs requires alignment to a common frame. The Iterative Closest Point family is standard, and Segal et al. [12] generalised it by modelling local surface patches as Gaussian distributions, which improves alignment on the planar walls typical of tunnels. Yang et al. [13] removed the dependence on a good initial guess with a globally optimal branch-and-bound formulation. Feature-based coarse alignment using Fast Point Feature Histograms [22] and graph-based outlier rejection [23] now provides reliable initialisation, and voxelised GICP variants [24] reach sub-millimetre accuracy at interactive speed. These advances feed directly into change detection: the Multiscale Model to Model Cloud Comparison (M3C2) algorithm of Lague et al. [14] derives a Level of Detection from local roughness and registration uncertainty, separating real deformation from noise at a stated confidence level. What remains open is the engineering chain after the displacement map is produced. Registration and M3C2 are well-characterised in isolation, yet packaging them into a repeatable tunnel workflow that an inspector can run end to end is largely left to bespoke scripts.

### 2.4 AI-assisted structural assessment

Translating a displacement map into a maintenance decision still requires a qualified engineer to read every report. Retrieval-Augmented Generation [15] grounds large language model output in retrieved domain documents, and Jiang et al. [16] showed that this grounding reduces hallucination when language models support vision-based structural health monitoring. These systems are typically cloud-hosted, which conflicts with the data-handling constraints of critical infrastructure, and none has been specialised for tunnel inspection metrics. A local, standards-grounded assistant that drafts a preliminary summary while keeping survey data on-device has not been demonstrated.

### 2.5 Summary

Table 1 positions the proposed system against representative prior work. Existing methods each cover part of the chain from raw scan to engineering report; none covers the full chain with automated denoising of structured clutter, Frenet-frame cross-section extraction, and an on-device assessment assistant in a single open pipeline.

**Table 1.** Capability comparison with representative prior work (●: provided, ◐: partial, ○: not addressed).

| Capability | Jung [8] | Gikas [9] | Ye [10] | Commercial [11] | This study |
|---|---|---|---|---|---|
| Automated clutter denoising | ○ | ○ | ◐ | ◐ | ● |
| Curvature-correct sectioning | ○ | ◐ | ○ | ○ | ● |
| Multi-epoch M3C2 detection | ○ | ◐ | ○ | ◐ | ● |
| BIM (IFC) output | ○ | ○ | ○ | ◐ | ● |
| On-device AI assistant | ○ | ○ | ○ | ○ | ● |
| Open source | ○ | ○ | ○ | ○ | ● |
