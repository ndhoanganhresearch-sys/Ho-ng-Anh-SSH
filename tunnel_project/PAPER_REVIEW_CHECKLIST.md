# Paper Review Checklist

Use this checklist before considering a tunnel-tool manuscript ready for submission, supervisor review, or internal reporting.

## Core Claim Audit

- Does every major claim have numeric evidence, visual evidence, or a cited source?
- Is each result tied to a commit hash and dataset identifier?
- Are T0 and Tn roles clearly defined?
- Is T0 described as a reference scan, not absolute ground truth, unless independent ground truth exists?
- Are deformation units and sign convention clearly stated?
- Are thresholds reported in millimeters and kept consistent across baseline/candidate comparisons?

## Benchmark Quality

- Is the first tool version included when the paper discusses improvement over the original implementation?
- Is the current candidate compared against the best measured baseline, not only the immediately previous version?
- Are input data, thresholds, and commands identical for baseline and candidate?
- Are RMSE, MAE, max deviation, warning counts, and runtime reported where relevant?
- Are worse metrics explained instead of hidden?
- Is rollback or reproduction possible from the report?

## MATLAB / Manual Workflow Comparison

- Is the comparison type clear: algorithm-level, workflow-level, runtime-level, or visual/manual?
- Are MATLAB inputs and preprocessing steps equivalent to the tool inputs?
- Are both workflows judged by the same metric and same T0/Tn pair?
- Are UI/convenience advantages separated from numeric accuracy claims?
- Are limitations of the MATLAB comparison stated if exact method parity is unavailable?

## Clean Noise Review

- Does the paper show before/after point counts?
- Does it show whether tunnel lining geometry was preserved?
- Does it measure whether denoising improves or worsens deformation detection?
- Are noisy outliers and true deformation treated separately?
- If a previous clean-noise fix made results worse, does the paper explain which version became the baseline?

## Centerline and Section Review

- Are section generation and chainage ordering described clearly?
- Are section frames oriented consistently across T0 and Tn?
- Are section fit failures or window-fit UI issues excluded from benchmark claims?
- Is the effect of centerline error on deformation measurement discussed?

## Deformation Warning Review

- Are warnings local to affected sections?
- Is the same deformation example visible in both 2D and 3D evidence?
- Are false warnings and missed warnings counted when labels or manual inspection are available?
- Is inward/outward deformation direction defined?
- Are global registration errors separated from local tunnel deformation?

## Figures and Tables

- Does every figure have a material passport?
- Are 2D and 3D figures readable without relying on UI explanation text?
- Are axes, units, thresholds, and color meaning clear?
- Are tables aligned with the benchmark report schema?
- Are screenshots taken from the tested commit rather than a later UI state?

## Related Work

- Does related work cover tunnel point-cloud monitoring, denoising, centerline/section fitting, registration/comparison, and visualization?
- Are strengths of prior tools acknowledged fairly?
- Is the paper gap specific and defensible?
- Does the paper avoid claiming novelty where the contribution is integration and reproducibility?

## Limitations

- Does the paper state ground-truth limitations?
- Does it describe threshold sensitivity?
- Does it describe data quality limits such as sparse scans, occlusion, reflective surfaces, or heavy noise?
- Does it describe cases where clean noise may remove meaningful deformation evidence?
- Does it distinguish engineering usefulness from formal metrology certification?

## Submission Gate

The manuscript is not ready if any of these are true:

- A major claim has no evidence.
- A benchmark lacks commit hash, command/source, or input identifiers.
- MATLAB comparison is described as superior/inferior without controlled metrics.
- Deformation warning examples do not prove local section behavior.
- Clean-noise improvement is claimed without before/after metrics.
- Figures cannot be reproduced from the recorded workflow.

