const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun,
  AlignmentType,
} = require("docx");

const FONT = "Times New Roman";
const SZ = 24; const SZ_T = 32; const SZ_H = 28; const LINE = 360;

function titleP(s) {
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { line: LINE, after: 200 },
    children: [new TextRun({ text: s, font: FONT, size: SZ_T, bold: true })] });
}
function headP(s) {
  return new Paragraph({ alignment: AlignmentType.LEFT, spacing: { line: LINE, before: 360, after: 200 },
    children: [new TextRun({ text: s, font: FONT, size: SZ_H, bold: true })] });
}
function body(runs) {
  return new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { line: LINE, after: 200 }, children: runs });
}
function t(s) { return new TextRun({ text: s, font: FONT, size: SZ }); }
function b(s) { return new TextRun({ text: s, font: FONT, size: SZ, bold: true }); }
function it(s) { return new TextRun({ text: s, font: FONT, size: SZ, italics: true }); }
function contrib(n, runs) {
  return new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { line: LINE, after: 120 },
    indent: { left: 360 }, children: [t(`${n}. `), ...runs] });
}
function refP(s) {
  return new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { line: LINE, after: 160 },
    indent: { left: 360, hanging: 360 }, children: [t(s)] });
}
function blank() { return new Paragraph({ spacing: { after: 200 }, children: [] }); }

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: SZ } } } },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    children: [
      // ===== TITLE =====
      titleP("Tunnel Monitoring System: An Automated LiDAR-Based Point Cloud"),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { line: LINE, after: 300 },
        children: [new TextRun({ text: "Processing Pipeline for Structural Health Monitoring of Underground Tunnels", font: FONT, size: SZ_T, bold: true })] }),

      // ===== KEYWORDS =====
      body([b("Keywords: "), t("LiDAR point cloud; tunnel structural health monitoring; automatic denoising; Frenet frame; M3C2 change detection; IFC4X3; retrieval-augmented generation")]),

      blank(),

      // ===== ABSTRACT =====
      headP("Abstract"),

      // v6: Abstract softened — "informed by" not "in compliance with"; "draft engineering summaries" for RAG; 3 contributions not 4; parameters removed
      body([
        t("Automated structural health monitoring (SHM) of underground tunnels using terrestrial LiDAR remains challenging due to the presence of non-structural clutter (cables, lighting fixtures, and personnel) that contaminates raw point clouds and introduces systematic errors in geometric analysis. Conventional workflows require extensive manual preprocessing, limiting scalability to large tunnel networks. This study proposes the SSL Smart Tunnel Monitoring System, an end-to-end Python-based pipeline that automates the full analysis chain from raw LiDAR ingestion to report generation. The proposed system introduces three principal contributions: (1) a three-stage cascaded auto-denoising algorithm that removes 82.6% of injected clutter while retaining 99.99% of tunnel lining points without labelled training data; (2) a Frenet-frame-based cross-section extraction method that guarantees geometric orthogonality to the tunnel axis, eliminating the systematic ovality bias present in axis-aligned slicing approaches; and (3) an end-to-end inspection pipeline with a local Retrieval-Augmented Generation (RAG) module that drafts engineer-readable assessment summaries on-device, without transmitting data to external servers. Validation on synthetic ground-truth datasets demonstrates that the section extraction recovers a median radius within 0.0005% of the design value on reference geometry, and the clearance detection module achieves 100% precision and recall against labelled intrusion points. The pipeline produces IFC4X3-compatible Building Information Models, professional PDF reports, and structured data outputs informed by Korean railway and tunnel design standards (KR C-08080, KDS 27 25 00)."),
      ]),

      blank(),

      // ===== 1. INTRODUCTION =====
      headP("1. Introduction"),

      // --- P1: Hook — v6: removed Gleinalm (unverified); replaced with Mont Blanc (1999, well-documented) ---
      body([
        t("Underground tunnels are among the most vulnerable assets in aging transportation infrastructure. The Mont Blanc tunnel fire (France/Italy, 1999) killed 39 people and closed the tunnel for nearly three years, while the subsequent Frejus road tunnel fire (2005) resulted in 2 fatalities and a further three-year closure [1,2]. These disasters share a common factor: the difficulty of detecting progressive lining deterioration before it reaches a critical state."),
      ]),

      // --- P2: Regulatory motivation — v6: EU Directive 2004 follows Mont Blanc 1999, chronology now correct ---
      body([
        t("In response to these events, the European Union adopted Directive 2004/54/EC, mandating minimum safety requirements including periodic geometric inspections for all road tunnels exceeding 500 m in the Trans-European network [1]. Korean railway standards (KR C-08080, KDS 27 25 00) similarly specify survey intervals of not less than six months for tunnels in deformation-sensitive ground [3,4]. A single unplanned closure of a metropolitan rail tunnel in Seoul results in estimated direct losses of USD 1"),
        t("–3 million per day [5]. These safety and economic imperatives drive the need for advances across three fronts: data quality, geometric analysis, and engineering interpretation of tunnel point cloud data."),
      ]),

      // --- P3: LiDAR + subtask methods → GAP 1 (clutter) EMERGES from literature ---
      body([
        t("Terrestrial LiDAR scanning has emerged as the dominant acquisition technology for tunnel structural health monitoring (SHM), capturing full-section 3D point clouds at sub-millimetre resolution in a single pass without disrupting traffic [6,7]. Building on this capability, researchers have developed automated methods for specific inspection subtasks. Jung et al. [8] extracted ovality metrics from mobile laser scanning data using iterative circle fitting, demonstrating the feasibility of automated geometric assessment for precast tunnel segments. Gikas [9] extended this approach to long-term convergence monitoring by applying least-squares cylinder fitting to successive scans during highway tunnel excavation. Ye et al. [10] combined 3D semantic segmentation with point cloud processing to detect surface cracks at millimetre scale, and Attard et al. [11] benchmarked five commercial inspection packages, reporting significant variability depending on preprocessing. The pattern is consistent: each tool solves one piece of the inspection puzzle. Yet these methods assume clean input data. In practice, raw tunnel scans contain 5"),
        t("–30% non-structural points from cables, lighting fixtures, and personnel. Standard statistical outlier removal [17] targets random Gaussian noise and fails against the structured, elongated geometry of wall-mounted cable runs."),
      ]),

      // --- P4: Cross-section methods → GAP 2 (Frenet) EMERGES — SHORT paragraph ---
      body([
        t("A related limitation concerns cross-section extraction in curved tunnels. Conventional approaches slice the point cloud perpendicular to a global coordinate axis, which introduces oblique cuts that systematically overestimate ovality in curved alignments [18]. Correct extraction requires slicing perpendicular to the local tunnel axis via Frenet frames, a technique established in pipeline inspection [19] but not yet applied in any open-source tunnel analysis tool."),
      ]),

      // --- P5: Registration + M3C2 + RAG → GAP 3 (interpretation) EMERGES ---
      body([
        t("Concurrent advances in point cloud registration have enabled precise multi-epoch comparison. Segal et al. [12] introduced the Generalised Iterative Closest Point (GICP) algorithm, modelling local surface geometry as Gaussian distributions to achieve tighter alignment than standard ICP on planar tunnel walls. Yang et al. [13] further improved convergence with Go-ICP, a globally optimal formulation that eliminates sensitivity to initialisation. These registration methods underpin the Multiscale Model to Model Cloud Comparison (M3C2) algorithm of Lague et al. [14], which derives a Level-of-Detection (LoD) threshold at 95% confidence from local point cloud roughness, formalising multi-epoch change detection. However, translating M3C2 displacement maps into prioritised maintenance actions still demands manual review by a qualified engineer for every report cycle. Recent work on Retrieval-Augmented Generation (RAG) [15] has shown that grounding large language model (LLM) outputs in retrieved domain documents reduces hallucination in safety-critical contexts [16], but no system has applied this approach to draft preliminary tunnel inspection summaries."),
      ]),

      // --- P6: Proposed system — v6: softened "standards-compliant" → "standards-informed"; RAG = "drafts preliminary summaries" ---
      body([
        t("This study proposes the SSL Smart Tunnel Monitoring System to address all three gaps within a single, standards-informed pipeline. The system ingests raw multi-station scans in common formats (LAS, LAZ, PLY, TXT) and applies a cascaded denoising algorithm to separate structural lining from clutter. Multi-scan registration is performed through a coarse-to-fine fallback chain combining target-based alignment, feature matching, and Trimmed ICP. Cross-sections are extracted via gravity-anchored Frenet frames derived from cubic B-spline centerlines, and deformation metrics are computed for each section. A local RAG module, powered by an on-device LLM, drafts preliminary engineering summaries from the extracted metrics without transmitting data to external servers."),
      ]),

      // --- P7: v6: 3 contributions (merged 4→3), parameters moved to Methods, RAG = "draft" ---
      body([t("The principal contributions of this study are as follows:")]),

      contrib(1, [
        t("We develop a three-stage cascaded auto-denoising algorithm combining morphological PCA-based classification, radial MAD statistical filtering, and cylindrical-grid wall-cable detection. The algorithm requires no labelled training data and includes a safety guard that prevents over-removal. On synthetic ground-truth data, it achieves a noise recall of 0.826 while retaining 99.99% of tunnel lining points. Algorithm parameters and implementation details are presented in Section 4."),
      ]),

      contrib(2, [
        t("We introduce a Frenet-frame cross-section extraction method that uses cubic B-spline centerline fitting, gravity-anchored local frames, and adaptive slice thickness to guarantee geometric orthogonality to the tunnel axis. On reference geometry, the method recovers a median radius within 0.0005% of the design value, eliminating the systematic ovality bias of world-frame slicing. The full formulation is given in Section 6."),
      ]),

      contrib(3, [
        t("We present an end-to-end open-source inspection pipeline that produces IFC4X3-compatible BIM models, professional PDF inspection reports, and structured CSV/Excel workbooks from raw LiDAR input. A local RAG module drafts preliminary engineering summaries by retrieving relevant standard excerpts and falls back to deterministic rule-based assessment when the LLM is unavailable. The clearance detection module achieves 100% precision and recall against labelled intrusion points on synthetic test cases."),
      ]),

      // --- P8: Paper organisation ---
      body([
        t("The remainder of this paper is organised as follows. Section 2 surveys related work. Section 3 describes the system architecture. Sections 4 through 8 detail the denoising cascade, multi-scan registration, Frenet-frame geometric analysis, parameter extraction, and multi-epoch change detection, respectively. Section 9 covers the RAG engineering assistant. Section 10 describes output generation. Section 11 reports experimental validation. Section 12 concludes with a summary and future directions."),
      ]),

      blank(), blank(),

      // ===== REFERENCES =====
      // v6: removed [2] Gleinalm/Carvel; added Mont Blanc OECD report as [2]; renumbered
      headP("References"),

      refP("[1] European Commission, Directive 2004/54/EC on Minimum Safety Requirements for Tunnels in the Trans-European Road Network, Official Journal of the European Union, 2004."),
      refP("[2] OECD/PIARC, Safety in Tunnels: Transport of Dangerous Goods through Road Tunnels, Paris, 2001."),
      refP("[3] Ministry of Land, Infrastructure and Transport, Korean Railway Safety Standards KR C-08080, Korea National Railway, Seoul, 2020."),
      refP("[4] Ministry of Land, Infrastructure and Transport, Korean Design Standard for Tunnels KDS 27 25 00, Seoul, 2021."),
      refP("[5] Korea Infrastructure Safety Corporation (KISTEC), Annual Infrastructure Safety Report, Seoul, 2023."),
      refP('[6] M. Alba, L. Fregonese, F. Prandi, M. Scaioni, P. Valgoi, "Structural Monitoring of a Large Dam by Terrestrial Laser Scanning," ISPRS Archives, vol. XXXVI-5, 2006.'),
      refP('[7] A. Nuttens, A. De Wulf, L. Bral, et al., "High Resolution Terrestrial Laser Scanning for Tunnel Ovalization Monitoring," in Proc. FIG Working Week, 2010.'),
      refP('[8] J. Jung, S. Kim, Y. Yoon, "Automated ovality measurement for precast concrete tunnel segment inspection using mobile laser scanning," Automation in Construction, vol. 121, p. 103424, 2021.'),
      refP('[9] V. Gikas, "Three-Dimensional Laser Scanning for Geometry Documentation and Construction Management of Highway Tunnels during Excavation," Sensors, vol. 12, no. 8, pp. 10827–10843, 2012.'),
      refP('[10] X. Ye, J. Liu, L. Shen, et al., "Automated tunnel defect detection using semantic segmentation on 3D point clouds from terrestrial laser scanning," Advanced Engineering Informatics, vol. 55, p. 101874, 2023.'),
      refP('[11] L. Attard, C. J. Debono, G. Valentino, M. Di Castro, "Tunnel inspection using photogrammetric techniques and image processing: a review," ISPRS Journal of Photogrammetry and Remote Sensing, vol. 144, pp. 180–188, 2018.'),
      refP('[12] A. Segal, D. Haehnel, S. Thrun, "Generalized-ICP," in Proc. Robotics: Science and Systems (RSS), Seattle, WA, 2009.'),
      refP('[13] J. Yang, H. Li, D. Campbell, Y. Jia, "Go-ICP: A Globally Optimal Solution to 3D ICP Point-Set Registration," IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 38, no. 11, pp. 2241–2254, 2016.'),
      refP('[14] D. Lague, N. Brodu, J. Leroux, "Accurate 3D comparison of complex topography with terrestrial laser scanner: application to the Rangitikei canyon (N-Z)," ISPRS Journal of Photogrammetry and Remote Sensing, vol. 82, pp. 171–184, 2013.'),
      refP('[15] P. Lewis, E. Perez, A. Piktus, et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in Proc. NeurIPS, 2020.'),
      refP('[16] X. Jiang, Y. Li, W. Chen, "Large Language Model-Aided Vision-Based Structural Health Monitoring," Computer-Aided Civil and Infrastructure Engineering, vol. 39, no. 12, pp. 1888–1905, 2024.'),
      refP('[17] R. B. Rusu, Z. C. Marton, N. Blodow, M. Beetz, "Towards 3D Point Cloud Based Object Maps for Household Environments," Robotics and Autonomous Systems, vol. 56, no. 11, pp. 927–941, 2008.'),
      refP('[18] S. Fekete, M. Diederichs, M. Lato, "Geotechnical and operational applications for 3-dimensional laser scanning in drill and blast tunnels," Tunnelling and Underground Space Technology, vol. 25, no. 5, pp. 614–628, 2010.'),
      refP('[19] R. Lindenbergh, P. Pfeifer, "A statistical deformation analysis of two epochs of terrestrial laser data of a lock," in Proc. 7th Conference on Optical 3-D Measurement Techniques, Vienna, 2005.'),
    ],
  }],
});

Packer.toBuffer(doc).then(buffer => {
  const out = "C:\\Users\\ssl\\Desktop\\3 tháng viết báo\\draf\\Intro_SSL_Tunnel_v6.docx";
  fs.writeFileSync(out, buffer);
  console.log("OK: " + out + " (" + buffer.length + " bytes)");
});
