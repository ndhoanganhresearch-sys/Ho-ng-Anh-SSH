# Tunnel Tool Research Workflow

Use this workflow when turning project results into a research paper, thesis chapter, benchmark report, or technical manuscript. The goal is to keep every paper claim tied to reproducible tool evidence.

## Research Objective

Primary research direction:

```text
An integrated Python-based workflow for tunnel point-cloud inspection using T0/Tn comparison, denoising, centerline/section analysis, local deformation detection, and 2D/3D warning visualization.
```

Prefer positioning the work as an integrated and reproducible engineering workflow unless a truly novel algorithm is added and benchmarked.

## Literature Review Tracks

Review papers and tools in these tracks before writing the related-work section:

- Tunnel point-cloud inspection and deformation monitoring.
- Centerline extraction and cross-section fitting for tunnel scans.
- Point-cloud denoising for LiDAR/tunnel lining data.
- Registration methods such as ICP, GICP, and M3C2-style comparison.
- Clearance/headroom detection and tunnel safety assessment.
- MATLAB, CloudCompare, and other manual or semi-automated workflows.
- 2D/3D deformation visualization and warning interfaces.

For each source, record:

```text
Source | Problem | Data | Method | Metrics | Strength | Limitation | Relevance to this tool
```

## Paper Pipeline

Follow this order:

1. Define the exact research question and target claim.
2. Build a literature matrix for the relevant tracks.
3. Identify the gap: fragmented workflow, weak reproducibility, limited local warning visualization, or limited benchmark transparency.
4. Freeze the benchmark protocol before changing the algorithm again.
5. Compare the first tool version, the best measured baseline, the current candidate, and MATLAB/manual workflow when available.
6. Create a material passport for each result used in the paper.
7. Draft methodology only after the pipeline and parameters are stable.
8. Draft results only from benchmark reports with commit hashes and commands.
9. Run the paper review checklist before treating the draft as ready.
10. Keep limitations explicit, especially for ground truth, noisy scans, threshold sensitivity, and local/global deformation interpretation.

## Paper Structure

Recommended structure:

```text
Title
Abstract
Introduction
Related Work
System Overview
Methodology
Benchmark Design
Results
Discussion
Limitations
Conclusion
Reproducibility Notes
```

## Required Evidence Types

Every major claim should have one or more of these evidence types:

- Numeric metrics: RMSE, MAE, max deviation, warning count, false/missed warning count, runtime.
- Visual evidence: 2D section plot, 3D tunnel view, warning overlay, before/after denoising view.
- Version evidence: commit hash, baseline version, candidate version, rollback path.
- Data evidence: T0/Tn file names, section index, chainage, scan date when known.
- Parameter evidence: thresholds, denoising settings, fitting settings, registration settings.

## Recommended Paper Claims

Strong claims for this project should be phrased narrowly:

- The tool supports a reproducible T0/Tn tunnel deformation workflow.
- The tool can localize deformation warnings to affected sections when the threshold and section mapping are valid.
- The tool provides linked 2D and 3D evidence for deformation review.
- The benchmark workflow can compare clean-noise, centerline, deformation, and MATLAB/manual baselines under the same inputs.

Avoid broad claims unless directly benchmarked:

- Do not claim general superiority over MATLAB without a controlled comparison.
- Do not claim automatic ground-truth accuracy when T0 is only a reference scan.
- Do not claim denoising improves deformation detection unless before/after metrics support it.

## Reproducibility Package

For paper-ready experiments, keep these artifacts together:

```text
benchmark report
material passport
input data identifiers
commands
config/thresholds
commit hash
2D figures
3D figures or screenshots
decision notes
limitations
```

