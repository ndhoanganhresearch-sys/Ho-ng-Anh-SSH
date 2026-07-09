# Intro v8 — STRUCTURE-ONLY revision of v7

> Restructured to the professor's checklist: 7–8 paragraphs in the canonical order,
> ONE topic sentence per paragraph (first sentence = topic, NO citation),
> first sentences read as a coherent story. **No content/claims/refs changed** — only
> reorganised and citations moved out of topic sentences.
> CITATIONS STILL PENDING (next step): add lab papers + recent KSCE JCE & JSIM (≤2 yr).

## 1. Introduction

Underground tunnels are critical components of transportation networks that must remain safe and serviceable over service lives spanning many decades. As these assets age, their linings accumulate deformation and damage that, if left undetected, can escalate into operational closures or safety hazards. The Mont Blanc (1999, 39 fatalities) and Tauern (1999, 12 fatalities) tunnel fires exposed fundamental weaknesses in tunnel safety management and accelerated regulatory reform across Europe [1,2]. Although those events primarily concerned fire safety, they drew sustained attention to the broader need to monitor the structural condition of aging tunnel assets.

Periodic geometric monitoring of tunnels is therefore mandated by regulation, yet it remains operationally demanding at network scale. The European Union adopted Directive 2004/54/EC, establishing minimum safety requirements for road tunnels longer than 500 m in the Trans-European road network [1]. Korean railway and tunnel standards specify survey intervals of not less than six months for tunnels in deformation-sensitive ground [3,4]. Because a single unplanned closure of a metropolitan rail tunnel in Seoul is estimated to cause direct losses of USD 1–3 million per day [5], inspection must be both frequent and dependable. Conventional workflows, however, rely on extensive manual preprocessing and expert interpretation, which limits their scalability to large tunnel networks and motivates automated geometric monitoring.

Terrestrial LiDAR scanning has become the standard acquisition technology for tunnel structural health monitoring (SHM). A single survey pass captures dense, full-section three-dimensional point clouds with minimal disruption to traffic [6,7]. This capability provides the geometric raw material on which automated condition-assessment methods are built.

Building on this acquisition capability, researchers have automated individual geometric inspection subtasks. Jung et al. [8] extracted ovality metrics from mobile laser scanning data using iterative circle fitting, demonstrating automated geometric assessment for precast tunnel segments. Gikas [9] extended this idea to long-term convergence monitoring by applying least-squares cylinder fitting to successive scans during highway tunnel excavation. Ye et al. [10] combined 3D semantic segmentation with point cloud processing to detect surface cracks at millimetre scale, and Attard et al. [11] benchmarked five commercial inspection packages and reported significant variability depending on preprocessing. Across these studies, each tool addresses one well-defined piece of the inspection problem.

In parallel, advances in point cloud registration and change detection have enabled precise multi-epoch deformation analysis. Segal et al. [12] introduced Generalised ICP, modelling local surface geometry as Gaussian distributions to achieve tighter alignment than standard ICP on planar tunnel walls, and Yang et al. [13] improved convergence robustness with the globally optimal Go-ICP formulation. These registration methods underpin the Multiscale Model-to-Model Cloud Comparison (M3C2) algorithm of Lague et al. [14], which derives a 95%-confidence Level-of-Detection threshold from local point cloud roughness to formalise change detection. More recently, Retrieval-Augmented Generation (RAG) [15] has been shown to reduce large language model hallucination by grounding outputs in retrieved domain documents [16], suggesting a route toward automated interpretation of inspection results.

Despite this progress, three limitations still prevent existing methods from forming a complete, automated tunnel-monitoring workflow. First, most geometric methods assume clean input, whereas raw tunnel scans contain an estimated 5–30% non-structural points from cables, lighting fixtures, and personnel; standard statistical outlier removal [17] targets random Gaussian noise and fails against the structured, elongated geometry of wall-mounted cable runs. Second, cross-section extraction that slices perpendicular to a global coordinate axis introduces oblique cuts that overestimate ovality in curved alignments [18]; slicing perpendicular to the local axis via Frenet frames addresses this bias, a technique established in pipeline inspection [19] but not yet available in open-source tunnel analysis tools. Third, even where displacement maps are produced, translating M3C2 results into prioritised maintenance actions still requires manual review by a qualified engineer for every report cycle, and no existing system applies RAG to draft preliminary tunnel inspection summaries.

This study proposes the SSL Smart Tunnel Monitoring System to address these three limitations within a single, standards-informed pipeline. The system ingests raw multi-station scans in common formats (LAS, LAZ, PLY, TXT) and applies a cascaded denoising algorithm to separate structural lining from clutter. Multi-scan registration is performed through a coarse-to-fine fallback chain combining target-based alignment, feature matching, and Trimmed ICP. Cross-sections are extracted via gravity-anchored Frenet frames derived from cubic B-spline centerlines, and deformation metrics are computed for each section. A local RAG module, powered by an on-device LLM, drafts preliminary engineering summaries from the extracted metrics without transmitting data to external servers. The principal contributions of this study are as follows:

1. We develop a three-stage cascaded auto-denoising algorithm combining morphological PCA-based classification, radial MAD statistical filtering, and cylindrical-grid wall-cable detection. The algorithm requires no labelled training data and includes a safety guard that prevents over-removal. On synthetic ground-truth data, it achieves a noise recall of 0.826 while retaining 99.99% of tunnel lining points. Algorithm parameters and implementation details are presented in Section 4.

2. We introduce a Frenet-frame cross-section extraction method that uses cubic B-spline centerline fitting, gravity-anchored local frames, and adaptive slice thickness to ensure geometric orthogonality to the tunnel axis. On reference geometry, the method recovers a median radius within 0.0005% of the design value, substantially reducing the ovality bias of world-frame slicing. The full formulation is given in Section 6.

3. We present an end-to-end open-source inspection pipeline that produces IFC4X3-compatible BIM models, professional PDF inspection reports, and structured CSV/Excel workbooks from raw LiDAR input. A local RAG module drafts preliminary engineering summaries by retrieving relevant standard excerpts and falls back to deterministic rule-based assessment when the LLM is unavailable. The clearance detection module achieves 100% precision and recall against labelled intrusion points on synthetic test cases.

The remainder of this paper is organised as follows. Section 2 surveys related work. Section 3 describes the system architecture. Sections 4 through 8 detail the denoising cascade, multi-scan registration, Frenet-frame geometric analysis, parameter extraction, and multi-epoch change detection, respectively. Section 9 covers the RAG engineering assistant. Section 10 describes output generation. Section 11 reports experimental validation. Section 12 concludes with a summary and future directions.

---

## Story-line check (rule #2 — read only the first sentence of each paragraph)

1. Underground tunnels are critical components of transportation networks that must remain safe and serviceable over decades.  *(background)*
2. Periodic geometric monitoring is mandated by regulation, yet remains operationally demanding at network scale.  *(problem)*
3. Terrestrial LiDAR scanning has become the standard acquisition technology for tunnel SHM.  *(existing technology)*
4. Building on this capability, researchers have automated individual geometric inspection subtasks.  *(recent trends I)*
5. In parallel, advances in registration and change detection have enabled precise multi-epoch deformation analysis.  *(recent trends II)*
6. Despite this progress, three limitations still prevent a complete automated monitoring workflow.  *(limitations)*
7. This study proposes the SSL Smart Tunnel Monitoring System to address these three limitations.  *(purpose & novelty)*
8. The remainder of this paper is organised as follows.  *(structure)*

→ Each opening sentence continues directly from the previous one; no topic sentence carries a citation.

## Pending (citations) — next step, target journal = KSCE JCE
- Add lab's related papers (user to supply list).
- Add recent (≤2 yr) **KSCE Journal of Civil Engineering** and **Journal of Structural Integrity and Maintenance** papers.
- Place all new refs only in supporting sentences, never in topic sentences.
