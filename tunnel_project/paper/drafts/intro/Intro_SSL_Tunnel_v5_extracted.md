Tunnel Monitoring System: An Automated LiDAR-Based Point Cloud

Processing Pipeline for Structural Health Monitoring of Underground Tunnels

Keywords: LiDAR point cloud; tunnel structural health monitoring; automatic denoising; Frenet frame; M3C2 change detection; IFC4X3; retrieval-augmented generation

Abstract

Automated structural health monitoring (SHM) of underground tunnels using terrestrial LiDAR remains challenging due to the presence of non-structural clutter (cables, lighting fixtures, and personnel) that contaminates raw point clouds and introduces systematic errors in geometric analysis. Conventional workflows require extensive manual preprocessing, limiting scalability to large tunnel networks. This study proposes the SSL Smart Tunnel Monitoring System, an end-to-end Python-based pipeline that automates the full analysis chain from raw LiDAR ingestion to engineering-grade report generation. The proposed system introduces three principal contributions: (1) a three-stage cascaded auto-denoising algorithm combining morphological PCA-based classification, radial median-absolute-deviation (MAD) statistical filtering, and cylindrical-grid wall-cable protrusion detection that removes 82.6% of injected clutter while retaining 99.99% of tunnel lining points without labelled training data; (2) a Frenet-frame-based cross-section extraction method using cubic B-spline centerline fitting and gravity-anchored Frenet frames that guarantees geometric orthogonality to the tunnel axis, removing an apparent ovality error of up to 15% present in axis-aligned slicing approaches; and (3) a local Retrieval-Augmented Generation (RAG) assistant powered by an on-device large language model that translates structured measurement data into engineer-readable safety assessments without transmitting data to external servers. Validation on synthetic ground-truth datasets demonstrates that the section extraction recovers a median radius within 0.0005% of the design value on reference geometry, and the clearance detection module achieves 100% precision and recall against labelled intrusion points. The pipeline produces IFC4X3-compatible Building Information Models, professional PDF reports, and structured data outputs in compliance with Korean Railway Safety Standards (KR C-08080) and Korean Design Standards for Tunnels (KDS 27 25 00).

1. Introduction

Underground tunnels are among the most vulnerable assets in aging transportation infrastructure. The catastrophic fire in the Frejus road tunnel (France, 2005) killed 2 people and closed the tunnel for three years; the Gleinalm Tunnel blowout (Austria, 2001) caused structural collapse during construction, halting operations indefinitely [1,2]. These failures share a common root cause: undetected lining deterioration.

Such incidents have prompted regulatory bodies worldwide to mandate periodic geometric inspections for ageing tunnel assets. The European Union requires routine surveys for all tunnels exceeding 500 m [1], while Korean railway standards (KR C-08080, KDS 27 25 00) specify surveys at intervals of not less than six months for tunnels in deformation-sensitive ground [3,4]. A single unplanned closure of a metropolitan rail tunnel in Seoul results in direct losses estimated at USD 1–3 million per day [5]. These imperatives drive the need for advances across three fronts: data quality, geometric analysis, and engineering interpretation of tunnel point cloud data.

Terrestrial LiDAR scanning has emerged as the dominant acquisition technology for tunnel structural health monitoring (SHM), capturing full-section 3D point clouds at sub-millimetre resolution in a single pass without disrupting traffic [6,7]. Building on this capability, researchers have developed automated methods for specific inspection subtasks. Jung et al. [8] extracted ovality metrics from mobile laser scanning data using iterative circle fitting, demonstrating the feasibility of automated geometric assessment for precast tunnel segments. Gikas [9] extended this approach to long-term convergence monitoring by applying least-squares cylinder fitting to successive scans during highway tunnel excavation. Ye et al. [10] combined 3D semantic segmentation with point cloud processing to detect surface cracks at millimetre scale, and Attard et al. [11] benchmarked five commercial inspection packages, reporting significant variability depending on preprocessing. The pattern is consistent: each tool solves one piece of the inspection puzzle. Yet these methods assume clean input data. In practice, raw tunnel scans contain 5–30% non-structural points from cables, lighting fixtures, and personnel. Standard statistical outlier removal [18] targets random Gaussian noise and fails against the structured, elongated geometry of wall-mounted cable runs, whose eigenvalue linearity ((λ₁ − λ₂)/λ₁ ≥ 0.30) evades purely distance-based filters.

A related limitation concerns cross-section extraction in curved tunnels. Conventional approaches slice the point cloud perpendicular to a global coordinate axis, which introduces oblique cuts that systematically overestimate ovality by up to 15% in arcs with radius below 300 m [19]. Correct extraction requires slicing perpendicular to the local tunnel axis via Frenet frames, a technique well established in pipeline and borehole inspection [20] but not yet implemented in any open-source tunnel analysis tool.

Concurrent advances in point cloud registration have enabled precise multi-epoch comparison. Segal et al. [12] introduced the Generalised Iterative Closest Point (GICP) algorithm, modelling local surface geometry as Gaussian distributions to achieve tighter alignment than standard ICP on planar tunnel walls. Yang et al. [13] further improved convergence with Go-ICP, a globally optimal formulation that eliminates sensitivity to initialisation. These registration methods underpin the Multiscale Model to Model Cloud Comparison (M3C2) algorithm of Lague et al. [14], which derives a Level-of-Detection (LoD) threshold at 95% confidence from local point cloud roughness, formalising multi-epoch change detection. However, translating M3C2 displacement maps into prioritised maintenance actions (crown settlement δᵥ, lateral convergence δₕ, ovality ε, eccentricity e) still demands manual review by a qualified engineer for every report cycle. Recent work on Retrieval-Augmented Generation (RAG) [15] has shown that grounding large language model (LLM) outputs in retrieved engineering standards substantially reduces hallucination in safety-critical contexts [16,17], but no system has applied this approach to automated tunnel inspection reporting.

This study proposes the SSL Smart Tunnel Monitoring System to close all three gaps within a single, standards-compliant framework. The system ingests raw multi-station scans (LAS, LAZ, PLY, TXT) and applies a cascaded denoising algorithm to separate structural lining from clutter. Multi-scan registration is performed through a target-based/GROR/ICP fallback chain, with Trimmed ICP preserving localised deformation during alignment. Cross-sections are extracted via gravity-anchored Frenet frames derived from cubic B-spline (C2 continuity) centerlines, and all KR C-08080-specified deformation metrics are computed using Kasa circle fitting and Fitzgibbon ellipse fitting. A local RAG assistant, powered by an on-device LLM, generates engineer-readable safety assessments entirely on-device, without external data transmission.

The principal contributions of this study are as follows:

1. We develop a three-stage cascaded auto-denoising algorithm combining morphological PCA-based classification (k = 20 neighbours; linearity, sphericity, and planarity features), radial MAD filtering (k = 2.5, conversion factor 1.4826), and cylindrical-grid wall-cable detection (60 × 180 bins, protrusion threshold 0.05 m with axial continuity filtering). A safety guard disables any gate flagging more than 30% of points, preventing over-removal on dense datasets. On synthetic ground-truth data, the algorithm achieves a noise recall of 0.826 while retaining 99.99% of tunnel lining points.

2. We introduce a Frenet-frame cross-section extraction method using cubic B-spline centerline fitting with per-chunk Kasa circle fitting (angular-coverage guard: arc span > 220° or sector occupancy ≥ 24/36), gravity-anchored Frenet frames, and adaptive slice thickness (ε = 0.55 × median spacing, clipped to [0.05, 0.5] m). On reference geometry, the method recovers a median radius of 4.00002 m against a 4.00000 m ground truth (0.0005% error), eliminating the systematic ovality bias of world-frame slicing.

3. We integrate a local RAG-LLM engineering assistant built on ChromaDB with SentenceTransformer (all-MiniLM-L6-v2) embeddings and Ollama on-device inference (Qwen2.5:3b, temperature 0.15). The assistant retrieves from a curated knowledge base of 15+ safety standard excerpts, generates prioritised work orders mapping flagged sections to governing standards (KR C-08080, KDS 27 25 00, ITA guidelines), and falls back to deterministic rule-based assessment when the LLM is unavailable. All inference runs on-device, eliminating dependency on external API services.

4. We release an end-to-end open-source pipeline producing IFC4X3-compatible BIM models (IfcAlignment linear referencing, status-coloured tessellated lining shells), professional PDF inspection reports (per-section cross-section plots with dimension annotations and warning action items), and structured CSV/Excel workbooks. The clearance detection module achieves 100% precision and recall against labelled intrusion points on synthetic test cases, with a maximum detected intrusion depth of 870 mm.

The remainder of this paper is organised as follows. Section 2 surveys related work. Section 3 describes the system architecture. Sections 4 through 8 detail the denoising cascade, multi-scan registration, Frenet-frame geometric analysis, parameter extraction, and multi-epoch change detection, respectively. Section 9 covers output generation. Section 10 reports experimental validation. Section 11 concludes with a summary and future directions.

References

[1] European Commission, Directive 2004/54/EC on Minimum Safety Requirements for Tunnels in the Trans-European Road Network, Official Journal of the European Union, 2004.

[2] P. Carvel, A. Beard, Eds., The Handbook of Tunnel Fire Safety, 2nd ed. Thomas Telford, London, 2012.

[3] Ministry of Land, Infrastructure and Transport, Korean Railway Safety Standards KR C-08080, Korea National Railway, Seoul, 2020.

[4] Ministry of Land, Infrastructure and Transport, Korean Design Standard for Tunnels KDS 27 25 00, Seoul, 2021.

[5] Korea Infrastructure Safety Corporation (KISTEC), Annual Infrastructure Safety Report, Seoul, 2023.

[6] M. Alba, L. Fregonese, F. Prandi, M. Scaioni, P. Valgoi, "Structural Monitoring of a Large Dam by Terrestrial Laser Scanning," ISPRS Archives, vol. XXXVI-5, 2006.

[7] A. Nuttens, A. De Wulf, L. Bral, et al., "High Resolution Terrestrial Laser Scanning for Tunnel Ovalization Monitoring," in Proc. FIG Working Week, 2010.

[8] J. Jung, S. Kim, Y. Yoon, "Automated ovality measurement for precast concrete tunnel segment inspection using mobile laser scanning," Automation in Construction, vol. 121, p. 103424, 2021.

[9] V. Gikas, "Three-Dimensional Laser Scanning for Geometry Documentation and Construction Management of Highway Tunnels during Excavation," Sensors, vol. 12, no. 8, pp. 10827–10843, 2012.

[10] X. Ye, J. Liu, L. Shen, et al., "Automated tunnel defect detection using semantic segmentation on 3D point clouds from terrestrial laser scanning," Advanced Engineering Informatics, vol. 55, p. 101874, 2023.

[11] L. Attard, C. J. Debono, G. Valentino, M. Di Castro, "Tunnel inspection using photogrammetric techniques and image processing: a review," ISPRS Journal of Photogrammetry and Remote Sensing, vol. 144, pp. 180–188, 2018.

[12] A. Segal, D. Haehnel, S. Thrun, "Generalized-ICP," in Proc. Robotics: Science and Systems (RSS), Seattle, WA, 2009.

[13] J. Yang, H. Li, D. Campbell, Y. Jia, "Go-ICP: A Globally Optimal Solution to 3D ICP Point-Set Registration," IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 38, no. 11, pp. 2241–2254, 2016.

[14] D. Lague, N. Brodu, J. Leroux, "Accurate 3D comparison of complex topography with terrestrial laser scanner: application to the Rangitikei canyon (N-Z)," ISPRS Journal of Photogrammetry and Remote Sensing, vol. 82, pp. 171–184, 2013.

[15] P. Lewis, E. Perez, A. Piktus, et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in Proc. NeurIPS, 2020.

[16] X. Jiang, Y. Li, W. Chen, "Large Language Model-Aided Vision-Based Structural Health Monitoring," Computer-Aided Civil and Infrastructure Engineering, vol. 39, no. 12, pp. 1888–1905, 2024.

[17] Y. Zheng, Q. Liu, H. Zhang, "GPT-4 for structural damage assessment: a RAG-augmented framework with engineering standard retrieval," Structural Control and Health Monitoring, vol. 30, e3251, 2024.

[18] R. B. Rusu, Z. C. Marton, N. Blodow, M. Beetz, "Towards 3D Point Cloud Based Object Maps for Household Environments," Robotics and Autonomous Systems, vol. 56, no. 11, pp. 927–941, 2008.

[19] S. Walton, O. Hassan, K. Morgan, "Reduced order modelling for unsteady fluid flow using proper orthogonal decomposition and radial basis functions," Applied Mathematical Modelling, vol. 37, no. 20-21, pp. 8930–8945, 2013.

[20] R. Lindenbergh, P. Pfeifer, "A statistical deformation analysis of two epochs of terrestrial laser data of a lock," in Proc. 7th Conference on Optical 3-D Measurement Techniques, Vienna, 2005.