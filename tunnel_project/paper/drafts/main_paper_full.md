# The SSL Smart Tunnel Monitoring System: An Automated LiDAR-Based Point Cloud Processing Pipeline for Structural Health Monitoring of Underground Tunnels

**Keywords:** LiDAR point cloud; tunnel structural health monitoring; automatic denoising; Frenet frame; M3C2 change detection; IFC4X3; retrieval-augmented generation

## Abstract

Automated structural health monitoring (SHM) of underground tunnels using terrestrial LiDAR remains challenging due to the presence of non-structural clutter (cables, lighting fixtures, and personnel) that contaminates raw point clouds and introduces systematic errors in geometric analysis. Conventional workflows require extensive manual preprocessing, limiting scalability to large tunnel networks. This study proposes the SSL Smart Tunnel Monitoring System, an end-to-end Python-based pipeline that automates the full analysis chain from raw LiDAR ingestion to report generation. The proposed system introduces three principal contributions: (1) a three-stage cascaded auto-denoising algorithm that removes 82.6% of injected clutter while retaining 99.99% of tunnel lining points without labelled training data; (2) a Frenet-frame-based cross-section extraction method that reduces the systematic ovality bias present in axis-aligned slicing approaches; and (3) an end-to-end inspection pipeline with a local Retrieval-Augmented Generation (RAG) module that drafts preliminary engineering summaries on-device without transmitting data to external servers. Validation on synthetic ground-truth datasets demonstrates that the section extraction recovers a median radius within 0.0005% of the design value on reference geometry, and the clearance detection module achieves 100% precision and recall against labelled intrusion points. The pipeline produces IFC4X3-compatible Building Information Models, professional PDF reports, and structured data outputs informed by Korean railway and tunnel design standards (KR C-08080, KDS 27 25 00).

## 1. Introduction

Underground tunnels are critical components of transportation networks, yet they pose unique challenges for inspection and maintenance. Major tunnel fire incidents in Europe, including the Mont Blanc (1999, 39 fatalities) and Tauern (1999, 12 fatalities) disasters, exposed fundamental weaknesses in tunnel safety management and accelerated regulatory reform across the continent [1,2]. While these events primarily concerned fire safety, they drew attention to the broader problem of monitoring the structural condition of aging tunnel assets.

The European Union subsequently adopted Directive 2004/54/EC, establishing minimum safety requirements for road tunnels exceeding 500 m in the Trans-European network [1]. Korean railway and tunnel standards (KR C-08080, KDS 27 25 00) specify survey intervals of not less than six months for tunnels in deformation-sensitive ground [3,4]. A single unplanned closure of a metropolitan rail tunnel in Seoul results in estimated direct losses of USD 1–3 million per day [5]. These regulatory and economic pressures motivate the development of automated geometric monitoring methods that can scale to large tunnel networks.

Terrestrial LiDAR scanning has become widely adopted for tunnel structural health monitoring (SHM), capturing dense full-section 3D point clouds in a single survey pass with minimal disruption to traffic [6,7]. Building on this capability, researchers have developed automated methods for specific inspection subtasks. Jung et al. [8] extracted ovality metrics from mobile laser scanning data using iterative circle fitting, demonstrating the feasibility of automated geometric assessment for precast tunnel segments. Gikas [9] extended this approach to long-term convergence monitoring by applying least-squares cylinder fitting to successive scans during highway tunnel excavation. Ye et al. [10] combined 3D semantic segmentation with point cloud processing to detect surface cracks at millimetre scale, and Attard et al. [11] benchmarked five commercial inspection packages, reporting significant variability depending on preprocessing. The pattern is consistent: each tool addresses one piece of the inspection problem. Yet these methods assume clean input data. In practice, raw tunnel scans contain 5–30% non-structural points from cables, lighting fixtures, and personnel. Standard statistical outlier removal [17] targets random Gaussian noise and fails against the structured, elongated geometry of wall-mounted cable runs.

A related limitation concerns cross-section extraction in curved tunnels. Conventional approaches slice the point cloud perpendicular to a global coordinate axis, which can introduce oblique cuts that overestimate ovality in curved alignments [18]. Slicing perpendicular to the local tunnel axis via Frenet frames addresses this bias, a technique established in pipeline inspection [19] but not yet applied in open-source tunnel analysis tools.

Concurrent advances in point cloud registration have enabled precise multi-epoch comparison. Segal et al. [12] introduced the Generalised Iterative Closest Point (GICP) algorithm, modelling local surface geometry as Gaussian distributions to achieve tighter alignment than standard ICP on planar tunnel walls. Yang et al. [13] further improved convergence with Go-ICP, a globally optimal formulation that reduces sensitivity to initialisation. These registration methods underpin the Multiscale Model to Model Cloud Comparison (M3C2) algorithm of Lague et al. [14], which derives a Level-of-Detection (LoD) threshold at 95% confidence from local point cloud roughness, formalising multi-epoch change detection. However, translating M3C2 displacement maps into prioritised maintenance actions still demands manual review by a qualified engineer for every report cycle. Recent work on Retrieval-Augmented Generation (RAG) [15] has shown that grounding large language model (LLM) outputs in retrieved domain documents reduces hallucination in technical contexts [16], but no system has applied this approach to draft preliminary tunnel inspection summaries.

This study proposes the SSL Smart Tunnel Monitoring System to address all three gaps within a single, standards-informed pipeline. The system ingests raw multi-station scans in common formats (LAS, LAZ, PLY, TXT) and applies a cascaded denoising algorithm to separate structural lining from clutter. Multi-scan registration is performed through a coarse-to-fine fallback chain combining target-based alignment, feature matching, and Trimmed ICP. Cross-sections are extracted via gravity-anchored Frenet frames derived from cubic B-spline centerlines, and deformation metrics are computed for each section. A local RAG module, powered by an on-device LLM, drafts preliminary engineering summaries from the extracted metrics without transmitting data to external servers.

The principal contributions of this study are as follows:

1. We develop a three-stage cascaded auto-denoising algorithm combining morphological PCA-based classification, radial MAD statistical filtering, and cylindrical-grid wall-cable detection. The algorithm requires no labelled training data and includes a safety guard that prevents over-removal. On synthetic ground-truth data, it achieves a noise recall of 0.826 while retaining 99.99% of tunnel lining points. Algorithm parameters and implementation details are presented in Section 4.

2. We introduce a Frenet-frame cross-section extraction method that uses cubic B-spline centerline fitting, gravity-anchored local frames, and adaptive slice thickness to ensure geometric orthogonality to the tunnel axis. On reference geometry, the method recovers a median radius within 0.0005% of the design value, substantially reducing the ovality bias of world-frame slicing. The full formulation is given in Section 6.

3. We present an end-to-end open-source inspection pipeline that produces IFC4X3-compatible BIM models, professional PDF inspection reports, and structured CSV/Excel workbooks from raw LiDAR input. A local RAG module drafts preliminary engineering summaries by retrieving relevant standard excerpts and falls back to deterministic rule-based assessment when the LLM is unavailable. The clearance detection module achieves 100% precision and recall against labelled intrusion points on synthetic test cases.

The remainder of this paper is organised as follows. Section 2 surveys related work. Section 3 describes the system architecture. Sections 4 through 8 detail the denoising cascade, multi-scan registration, Frenet-frame geometric analysis, parameter extraction, and multi-epoch change detection, respectively. Section 9 covers the RAG engineering assistant. Section 10 describes output generation. Section 11 reports experimental validation. Section 12 concludes with a summary and future directions.

<!-- SECTIONS 2-12 ARE MAINTAINED IN drafts/sections/section_XX_*.md AND CONCATENATED HERE BY tools/assemble_paper.py -->
<!-- The canonical, individually-reviewable source for each section below is its own file in drafts/sections/. -->

@@SECTION_02@@
@@SECTION_03@@
@@SECTION_04@@
@@SECTION_05@@
@@SECTION_06@@
@@SECTION_07@@
@@SECTION_08@@
@@SECTION_09@@
@@SECTION_10@@
@@SECTION_11@@
@@SECTION_12@@

## References

[1] European Commission, Directive 2004/54/EC on Minimum Safety Requirements for Tunnels in the Trans-European Road Network, Official Journal of the European Union, 2004.

[2] OECD/PIARC, Safety in Tunnels: Transport of Dangerous Goods through Road Tunnels, Paris, 2001.

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

[17] R. B. Rusu, Z. C. Marton, N. Blodow, M. Beetz, "Towards 3D Point Cloud Based Object Maps for Household Environments," Robotics and Autonomous Systems, vol. 56, no. 11, pp. 927–941, 2008.

[18] S. Fekete, M. Diederichs, M. Lato, "Geotechnical and operational applications for 3-dimensional laser scanning in drill and blast tunnels," Tunnelling and Underground Space Technology, vol. 25, no. 5, pp. 614–628, 2010.

[19] R. Lindenbergh, P. Pfeifer, "A statistical deformation analysis of two epochs of terrestrial laser data of a lock," in Proc. 7th Conference on Optical 3-D Measurement Techniques, Vienna, 2005.

[20] A. W. Fitzgibbon, M. Pilu, R. B. Fisher, "Direct least square fitting of ellipses," IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 21, no. 5, pp. 476–480, 1999.

[21] I. Kåsa, "A circle fitting procedure and its error analysis," IEEE Transactions on Instrumentation and Measurement, vol. IM-25, no. 1, pp. 8–14, 1976.

[22] R. B. Rusu, N. Blodow, M. Beetz, "Fast Point Feature Histograms (FPFH) for 3D registration," in Proc. IEEE International Conference on Robotics and Automation (ICRA), Kobe, Japan, 2009, pp. 3212–3217.

[23] L. Yan, P. Wei, H. Xie, J. Dai, H. Wu, M. Huang, "A New Outlier Removal Strategy Based on Reliability of Correspondence Graph for Fast Point Cloud Registration," IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 45, no. 6, pp. 7986–8002, 2023.

[24] K. Koide, M. Yokozuka, S. Oishi, A. Banno, "Voxelized GICP for Fast and Accurate 3D Point Cloud Registration," in Proc. IEEE International Conference on Robotics and Automation (ICRA), Xi'an, China, 2021, pp. 11054–11059.

[25] Q.-Y. Zhou, J. Park, V. Koltun, "Open3D: A Modern Library for 3D Data Processing," arXiv preprint arXiv:1801.09847, 2018.

[26] M. Ester, H.-P. Kriegel, J. Sander, X. Xu, "A density-based algorithm for discovering clusters in large spatial databases with noise," in Proc. 2nd International Conference on Knowledge Discovery and Data Mining (KDD), Portland, OR, 1996, pp. 226–231.

[27] N. Reimers, I. Gurevych, "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks," in Proc. Conference on Empirical Methods in Natural Language Processing (EMNLP), Hong Kong, 2019, pp. 3982–3992.

[28] K. Anders, D. Kempf, W. Albert, et al., "py4dgeo: Open-source scientific software for topographic change analysis in 3D/4D geographic point clouds," SoftwareX, vol. 34, p. 102670, 2026.

[29] buildingSMART International, Industry Foundation Classes (IFC) 4.3.2.0 (IFC4X3), ISO 16739-1:2024, 2024.
