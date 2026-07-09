# Intro v9 — paragraph-discipline revision of v8

> Applies the professor's refined rule: every paragraph = 1 topic sentence (A–B, one
> logical relationship, no citation) + 4–5 supporting sentences that only explain /
> exemplify / cite evidence for that A–B relationship; ~5–6 sentences per paragraph;
> NO second logical step inside a paragraph (B–C moves to the next paragraph's topic
> sentence); first sentences form a coherent A–B → B–C → C–D chain.
> Structural changes vs v8: (i) the interpretation/RAG step moved out of the
> registration paragraph (¶5) into the limitations paragraph as the third gap, so ¶5
> carries a single step; (ii) the LiDAR paragraph expanded to 5 sentences; (iii) "the
> standard" → "a standard" acquisition technology.
> CLAIMS/NUMBERS = placeholders, to be replaced with real validated values later.
> CITATIONS STILL PENDING: lab papers + recent (≤2 yr) KSCE JCE & JSIM, in supporting sentences only.

## 1. Introduction

Underground tunnels are critical transport infrastructure whose structural condition must be monitored throughout service lives that span many decades. As their linings age, tunnels progressively accumulate deformation—crown settlement, sidewall convergence, and cross-sectional ovalization—that can degrade serviceability if it goes undetected. Major tunnel disasters in Europe, including the Mont Blanc and Tauern incidents of 1999, exposed weaknesses in tunnel safety management and accelerated regulatory reform across the continent [1,2]. Although those events primarily concerned fire safety, they drew sustained attention to the broader challenge of managing the condition of aging tunnel assets. The structural condition of in-service tunnels has therefore become a central concern for infrastructure owners and regulators alike.

This concern has translated into monitoring obligations that are mandated by regulation yet remain operationally demanding at the scale of national tunnel networks. In Europe, Directive 2004/54/EC established minimum safety requirements for road tunnels longer than 500 m in the Trans-European road network [1]. In Korea, railway and tunnel design standards prescribe survey intervals of not less than six months for tunnels situated in deformation-sensitive ground [3,4]. The economic stakes are comparably high, because a single unplanned closure of a metropolitan rail tunnel in Seoul is estimated to cause direct losses of USD 1–3 million per day [5]. Meeting these obligations through conventional workflows is difficult, as they rely on extensive manual preprocessing and expert interpretation that do not scale to large tunnel networks.

To acquire the geometric data that scalable monitoring requires, terrestrial LiDAR scanning has become a standard acquisition technology for tunnel structural health monitoring (SHM). A single survey pass captures dense, full-section three-dimensional point clouds of the tunnel lining with minimal disruption to traffic [6,7]. In contrast to point-wise total-station or tape-based convergence readings, LiDAR records millions of points per station and thus provides continuous rather than sparse geometric coverage. Successive scans can be co-registered into a common reference frame, which supports repeatable surveys across multiple epochs [6]. These properties make LiDAR point clouds the geometric raw material on which automated condition-assessment methods are built.

Building on this acquisition capability, researchers have automated individual geometric inspection subtasks. Jung et al. [8] extracted ovality metrics from mobile laser scanning data through iterative circle fitting for precast tunnel segments. Gikas [9] applied least-squares cylinder fitting to successive scans to monitor long-term convergence during highway tunnel excavation. Ye et al. [10] combined three-dimensional semantic segmentation with point-cloud processing to detect surface cracks at millimetre scale. Attard et al. [11] benchmarked five commercial inspection packages and reported substantial variability depending on preprocessing. Across these studies, each method addresses one well-defined component of the broader inspection problem.

In parallel, advances in point-cloud registration and change detection have enabled rigorous multi-epoch deformation analysis. Segal et al. [12] introduced Generalized ICP, which models local surface geometry as Gaussian distributions to align planar tunnel walls more tightly than standard ICP. Yang et al. [13] improved robustness to poor initialization with Go-ICP, a globally optimal registration formulation. Building on accurate registration, Lague et al. [14] proposed the Multiscale Model-to-Model Cloud Comparison (M3C2), which derives a 95%-confidence level-of-detection threshold from local point-cloud roughness. Together, these methods allow geometric change between survey epochs to be quantified with statistical confidence.

Despite these advances, three limitations still prevent existing methods from forming a complete, automated tunnel-monitoring workflow. First, most geometric methods assume clean input, whereas raw tunnel scans contain an estimated 5–30% non-structural points from cables, fixtures, and personnel, and standard statistical outlier removal [17] targets random Gaussian noise rather than the structured geometry of wall-mounted cable runs. Second, cross-sections obtained by slicing perpendicular to a global coordinate axis introduce oblique cuts that overestimate ovality in curved alignments [18], a bias that local Frenet-frame slicing can remove but that remains unavailable in open-source tunnel tools [19]. Third, even when displacement maps are produced, translating M3C2 results into prioritized maintenance actions still requires manual review by a qualified engineer, and no existing open-source system drafts preliminary tunnel inspection summaries automatically [15,16]. Because these limitations are typically addressed in isolation, no end-to-end pipeline yet spans raw data to actionable report.

To address these three limitations, this study proposes the SSL Smart Tunnel Monitoring System, an integrated and standards-informed pipeline spanning raw LiDAR ingestion to report generation. The system ingests raw multi-station scans in common formats (LAS, LAZ, PLY, TXT) and applies a cascaded denoising algorithm to separate structural lining from clutter. It registers scans through a coarse-to-fine fallback chain that combines target-based alignment, feature matching, and trimmed ICP, then extracts cross-sections via gravity-anchored Frenet frames derived from cubic B-spline centerlines. Deformation metrics are computed for each section, and a local retrieval-augmented generation (RAG) module drafts preliminary engineering summaries on-device without transmitting data to external servers. The principal contributions of this study are threefold:

1. We develop a three-stage cascaded auto-denoising algorithm combining morphological PCA-based classification, radial MAD statistical filtering, and cylindrical-grid wall-cable detection. The algorithm requires no labelled training data and includes a safety guard that prevents over-removal. On synthetic ground-truth data, it achieves a noise recall of 0.826 while retaining 99.99% of tunnel lining points. Algorithm parameters and implementation details are presented in Section 4.

2. We introduce a Frenet-frame cross-section extraction method that uses cubic B-spline centerline fitting, gravity-anchored local frames, and adaptive slice thickness to ensure geometric orthogonality to the tunnel axis. On synthetic reference geometry, the method recovers a median radius within 0.0005% of the design value, substantially reducing the ovality bias of world-frame slicing. The full formulation is given in Section 6.

3. We present an end-to-end open-source inspection pipeline that produces IFC4X3-compatible BIM models, professional PDF inspection reports, and structured CSV/Excel workbooks from raw LiDAR input. A local RAG module drafts preliminary engineering summaries by retrieving relevant standard excerpts and falls back to deterministic rule-based assessment when the LLM is unavailable. On synthetic test cases, the clearance detection module achieves 100% precision and recall against labelled intrusion points.

The remainder of this paper is organized as follows. Section 2 surveys related work, and Section 3 describes the system architecture. Sections 4 through 8 detail the denoising cascade, multi-scan registration, Frenet-frame geometric analysis, parameter extraction, and multi-epoch change detection, respectively. Section 9 covers the RAG engineering assistant, and Section 10 describes output generation. Section 11 reports experimental validation, and Section 12 concludes with a summary and future directions.

---

## Story-line check (rule #2 + #8 — first sentence of each paragraph, as an A–B → B–C chain)

1. Tunnels are critical infrastructure whose **structural condition must be monitored** over long service lives.  *(A–B: tunnels → condition monitoring)*
2. That **monitoring is mandated yet operationally demanding** at network scale.  *(B–C: condition monitoring → regulated but costly/hard)*
3. To supply the data such monitoring needs, **terrestrial LiDAR has become a standard acquisition technology**.  *(C–D: demanding monitoring → LiDAR acquisition)*
4. Building on LiDAR, **researchers have automated individual geometric inspection subtasks**.  *(D–E: acquisition → automated subtasks)*
5. In parallel, **registration and change detection enabled rigorous multi-epoch deformation analysis**.  *(E–F: subtask automation → multi-epoch analysis)*
6. Despite these advances, **three limitations still prevent a complete automated workflow**.  *(F–G: advances → remaining gaps)*
7. To address them, **this study proposes the SSL Smart Tunnel Monitoring System**.  *(G–H: gaps → proposed system)*
8. **The remainder of the paper is organized as follows.**  *(H: roadmap)*

→ Each topic sentence advances exactly one step from the previous; no topic sentence carries a citation; each paragraph develops only its own A–B relationship.

## Paragraph function + sentence count (rule #1, #9)
| ¶ | Function | Sentences | One logical step? |
|---|---|---|---|
| 1 | Background / current status | 5 | tunnels → must monitor condition |
| 2 | Problem statement | 5 | monitoring mandated → but demanding at scale |
| 3 | Existing technology (acquisition) | 5 | scalable monitoring → LiDAR acquisition |
| 4 | Recent trends I (geometric subtasks) | 5 | LiDAR → automated subtasks |
| 5 | Recent trends II (registration/change) | 5 | subtasks → multi-epoch analysis |
| 6 | Limitations (three gaps, parallel support) | 5 | advances → gaps remain |
| 7 | Purpose & novelty (+ 3 contributions) | 5 + list | gaps → proposed system |
| 8 | Paper structure | 4 | roadmap |

## Pending (citations) — target journal = KSCE JCE
- Add lab papers (user to supply) and recent (≤2 yr) KSCE JCE & JSIM papers, in supporting sentences only.
- Replace placeholder metrics (0.826 / 99.99% / 0.0005% / 100%) with real validated values when available.
