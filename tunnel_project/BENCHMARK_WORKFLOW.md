# Tunnel Benchmark Workflow

Use this workflow whenever changing clean noise, centerline extraction, registration, deformation comparison, or warning visualization.

## Required Baseline

Before promoting a change, identify:

- The exact input data or fixture.
- The current baseline version.
- The candidate version.
- The correctness gate that must stay green.
- The metrics used to judge improvement.

For this project, useful metrics include:

- RMSE and MAE when reference geometry is available.
- Runtime in seconds.
- Number of raw, kept, and removed points for denoising.
- Noise precision, recall, and F1 when labels are available.
- Number of warning sections, false warning sections, and missed warning sections.
- Deformation max/min/mean in millimeters.

## Variant Table

Record comparisons in this shape:

```text
Variant | Input | Command | RMSE | Runtime | Warnings | Correct? | Notes
baseline-best | sample A | python validate_auto_denoise_stsd.py | ... | ... | ... | yes | current main
candidate-1 | sample A | python validate_auto_denoise_stsd.py --variant candidate | ... | ... | ... | yes/no | reason
```

## Research-Grade Report Schema

Use this schema when a benchmark may be cited in the paper, thesis, report, or project decision log:

```text
experiment_id:
date:
operator_or_agent:
research_question:
claim_supported:

versions:
  first_tool_version:
  best_measured_baseline:
  candidate_version:
  matlab_or_manual_workflow:
  commit_hash:
  branch:

input_data:
  dataset_name:
  t0_file:
  tn_file:
  section_range:
  coordinate_units:
  notes:

configuration:
  clean_noise_config:
  registration_config:
  centerline_config:
  section_config:
  deformation_threshold_mm:
  warning_rule:

commands_or_ui_steps:
  baseline_command:
  candidate_command:
  matlab_or_manual_steps:

metrics:
  rmse:
  mae:
  max_deviation_mm:
  mean_deviation_mm:
  runtime_seconds:
  raw_points:
  kept_points:
  removed_points:
  warning_sections:
  false_warning_sections:
  missed_warning_sections:

visual_evidence:
  two_d_plot:
  three_d_view:
  before_after_noise:
  exported_report:

decision:
  result: promote | keep_baseline | rollback | inconclusive
  reason:
  accepted_tradeoffs:
  rollback_path:

limitations:
  ground_truth:
  data_quality:
  threshold_sensitivity:
  reproducibility_notes:
```

If any required field is unknown, write `TBD` rather than silently omitting it. Paper-facing results should not remain at `TBD` for input data, commit hash, metrics, or visual evidence.

## Paper Evidence Link

When a benchmark supports a paper figure or table, create or update a material passport in the format described in `MATERIAL_PASSPORT.md`. The benchmark report is the numeric source; the material passport is the provenance and claim-audit record.

## Promotion Rules

A candidate can become the main version only when:

- It passes the relevant smoke test or validation script.
- It is compared against the best measured baseline, not only the immediately previous version.
- The same input and thresholds are used for baseline and candidate.
- Any worse metric is explained and accepted deliberately.
- Rollback is clear from git diff or notes.

## Feature-Specific Gates

### Clean Noise

- Compare point counts before/after filtering.
- Preserve tunnel lining where possible.
- Do not overfit to a single sample if STSD or labeled data is available.
- If a previous fix made results worse, search older/better benchmark variants before continuing.
- For paper claims, report whether denoising improved deformation metrics, not only whether the point cloud looks cleaner.

### Deformation Warning

- Use T0 as reference and Tn as candidate/comparison scan.
- Warnings must be local: only affected sections should be highlighted.
- Verify both 2D and 3D displays.
- Record threshold in millimeters and whether positive/negative means inward/outward deformation.
- Separate local deformation from global registration drift before reporting warning accuracy.
- Save 2D and 3D evidence for any deformation example used in a paper or report.

### Centerline and Sections

- Check section fit in the window.
- Verify chainage order, section count, and frame orientation.
- Preserve tunnel aspect ratio in 3D views.
- State how centerline or section-fitting error may affect deformation metrics.

### MATLAB / Manual Workflow Comparison

- Define whether the comparison is algorithm-level, workflow-level, visual/manual, runtime, or usability.
- Use the same T0/Tn input pair and thresholds whenever possible.
- Keep UI convenience claims separate from numeric accuracy claims.
- Record any MATLAB preprocessing or manual parameter choices that are not reproduced by the Python tool.
