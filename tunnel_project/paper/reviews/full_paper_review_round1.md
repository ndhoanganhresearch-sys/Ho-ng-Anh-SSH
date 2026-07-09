# Editorial Decision — SSL Smart Tunnel Monitoring System (Round 1)

**Manuscript:** The SSL Smart Tunnel Monitoring System: An Automated LiDAR-Based Point Cloud Processing Pipeline for SHM of Underground Tunnels
**Reviewed:** 2026-06-16 · ARS `academic-paper-reviewer` full mode (5 independent reviewers + editorial synthesis)
**Manuscript reviewed:** `paper/drafts/main_paper_full_assembled.md` (commit `84c02cc`)

## Decision: **MAJOR REVISION**

Unanimous across all five reviewers. The Devil's Advocate raised two CRITICAL findings, which by the panel's IRON RULE bars an Accept. The work is well-written and honestly bounded, the system architecture is sound, and the Frenet-frame ablation is publishable-quality. But the evidentiary base does not yet meet Q1 standards: validation is synthetic-only, one principal contribution (RAG) is unevaluated, and — most seriously — the denoising contribution is not supported by its own benchmark.

## Aggregate scores (0–100, mean of 4 scoring reviewers)

| Dimension | EiC | R1 Method | R2 Domain | R3 Cross-disc | Mean | Weight |
|---|---|---|---|---|---|---|
| Originality | 58 | 68 | 62 | 74 | **65** | 20% |
| Methodological Rigor | 64 | 42 | 66 | 72 | **61** | 25% |
| Evidence Sufficiency | 34 | 35 | 52 | 63 | **46** | 25% |
| Argument Coherence | 76 | 72 | 80 | 78 | **76** | 15% |
| Writing Quality | 82 | 80 | 83 | 86 | **83** | 15% |
| **Weighted total** | | | | | **~64** | |

All five reviewers independently recommended **Major Revision**.

## Consensus issues (raised by ≥2 reviewers)

1. **Synthetic-only validation, over-generalized** (EiC CRITICAL, DA CRITICAL, R1/R2/R3 major). Every number comes from author-built Blender scenes; abstract/contributions/conclusion state figures without the synthetic qualifier.
2. **RAG claimed as principal contribution but unevaluated** (R3 CRITICAL, EiC/DA major, R1/R2 noted). No QA set, no retrieval metric; mismatch between "principal contribution" and "no numerical claim."
3. **Frenet +171.5% from a single curved scene / single curvature** (R1 CRITICAL, DA major, EiC/R2 noted). Not generalizable without a curvature sweep.
4. **Magic-number thresholds, no ablation, probable train/test leakage** (EiC major, R1 major). Parameters likely tuned on the same scenes used to validate.
5. **Registration comparison confounded; table advertises a non-converged 71 mm run** (EiC/R1/R2/DA). Speedup conflates algorithm + implementation; full-chain RMSE buried in prose.
6. **No repository/DOI/license despite "open source" claim** (R1/R2/R3). The one unambiguous differentiator in Table 1 is uncited.
7. **Table 6 eccentricity unit error** (R1/R2): values in "m" but Eq 11 outputs mm (569.9 m is impossible).
8. **py4dgeo [28] dated 2026** (R1/R2/R3): verify before submission.

## CRITICAL findings (block Accept)

- **DA-C1 — Contribution 1 not evidenced by its own benchmark.** In `case_03` the semantic stages (`n_cable`, `n_light`, `n_person`) and the wall-cable detector (`n_wall_cable`) each removed **0** points; all 877 removals came from the radial-MAD stage (`n_radial: 877`). The novel Stages 1 and 3 — the parts distinguishing this from standard SOR [17] — were inert on the one labelled denoising scene, and the structured "crown cable" was not caught by the bespoke cable detector. The "82.6% three-stage cascade" headline is, on this evidence, a radial-statistics result.
- **DA-C2 / EiC — Synthetic results generalized to operational accuracy** without the qualifier in abstract/§1/§12.
- **R2-C1 — Headline use case (deformation accuracy) never quantified.** The geometry engine (radius 0.0005%) and clearance (100%/100%) are validated, but measured-vs-prescribed crown settlement / convergence / local defect in mm is never reported, despite `ground_truth.csv` existing for exactly this.

## Prioritized Revision Roadmap

### P1 — Blocking (must resolve before resubmission)
- **P1.1** Add a per-stage removal-attribution table for denoising, and a scene where the semantic + wall-cable stages demonstrably remove structured clutter — **or** retitle/reframe Contribution 1 honestly (e.g., "robust radial filtering with optional semantic gates"). [DA-C1]
- **P1.2** Add ≥1 real tunnel-scan demonstration of denoising + sectioning — **or** reframe the paper explicitly as a methods/reference-implementation contribution with a qualified title and abstract; propagate the "on synthetic ground truth" caveat into abstract, contributions, and conclusion. [EiC/DA]
- **P1.3** Add a table of measured-vs-prescribed deformation (crown settlement, convergence, local defect) in mm per epoch from the T0→Tn series, with detection latency for the defect onset (T3). [R2-C1]
- **P1.4** Either evaluate the RAG (retrieval recall@k / MRR on a 30–50 item QA set + a small expert faithfulness check) **or** demote it from a principal contribution to a system component (two contributions in abstract/§1). [R3-C1]

### P2 — Major
- **P2.1** Frenet bias: sweep curvature (5–10 radii), plot bias vs curvature with the oblique-cut prediction overlaid; reframe as "grows with curvature as predicted." [R1-C2]
- **P2.2** Threshold sensitivity/ablation for the high-impact constants; disclose whether parameters were tuned on data disjoint from the validation scenes. [EiC/R1]
- **P2.3** Registration table: add the GROR→GICP full-chain RMSE rows for straight and curved; label standalone curved rows as out-of-basin; caveat the 20–61× speedup. [R1-M1/R2-M4]
- **P2.4** Clearance: precision–recall / ROC over intrusion magnitudes (≈5–870 mm), not a single perfect score. [R1-M4/DA]
- **P2.5** Code & data availability statement: repository URL, license, Zenodo DOI pinned to `84c02cc`, datasets, pinned environment, hardware spec for timings. [R1-M6/R2-m8/R3-M3]
- **P2.6** Add missing literature: TLS cross-section/convergence in operational tunnels, ≥1 scan-to-BIM/IFC-for-infrastructure paper, ≥1 MLS/SLAM tunnel acquisition paper. [R2-M1]
- **P2.7** IFC: define what "valid" means (schema checker + independent-viewer round-trip of `IfcAlignment` + severity Psets); reconcile or drop the "digital twin" framing. [R3-M2]
- **P2.8** Privacy: soften "no survey data leaves the device" to "by default," add an endpoint guard / one-sentence threat model. [R3-M1]
- **P2.9** Denoising→geometry error propagation: show the surviving ~17% clutter does not materially shift ovality/clearance vs the clean reference. [EiC/R2-M2]

### P3 — Minor
- **P3.1** Fix Table 6 eccentricity unit (m → mm). [R1/R2]
- **P3.2** Add synthetic + single-scene caveats to the abstract; standardize metric precision (0.826 vs 0.83 vs 0.9999). [R2/R1]
- **P3.3** Rewrite Eq 5 with the full N-row design matrix. [R1-m1]
- **P3.4** Replace the fire-disaster opening with deformation/aging-asset motivation. [EiC; matches prior intro feedback]
- **P3.5** Verify [28] py4dgeo year and standards citations during `/ars-citation-check`. [R1/R2/R3]
- **P3.6** Insert the actual Figure 1 pipeline diagram. [EiC]
- **P3.7** Specify the forecast extrapolation model (Sec 8.3) or label it heuristic/untested. [R2/R3]
- **P3.8** State the M3C2 LoD confidence level and registration-error term; acknowledge identity-registration under-exercises LoD. [R1-M5/R2-M3]
- **P3.9** Acknowledge personnel-envelope brittleness (crouching/equipment). [R1/R2]

## Note on data integrity
The Devil's Advocate confirmed the reported numbers match the stored artifacts (`benchmark_report.json`: recall 0.826, retention 0.9999, clearance 1.0/1.0, curved radius 3.991 m). No fabrication — the issues are interpretation, generalization, and missing experiments, not data honesty.
