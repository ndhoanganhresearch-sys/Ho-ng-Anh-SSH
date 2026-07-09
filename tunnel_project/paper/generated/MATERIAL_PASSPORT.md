# Material Passport

Use a material passport for every benchmark result, paper figure, table, screenshot, or claim-supporting artifact. A result should not be used in the paper if its source, version, command, and interpretation are unclear.

## Passport Template

```text
artifact_id:
artifact_type: benchmark | figure | table | screenshot | note
paper_section:
claim_supported:

data:
  dataset_name:
  t0_file:
  tn_file:
  section_index_or_chainage:
  coordinate_units:
  source_notes:

tool_version:
  commit_hash:
  branch:
  baseline_version:
  candidate_version:

method:
  workflow_step:
  command_or_ui_action:
  clean_noise_config:
  registration_config:
  centerline_config:
  section_config:
  deformation_threshold_mm:

metrics:
  rmse:
  mae:
  max_deviation_mm:
  mean_deviation_mm:
  warning_sections:
  false_warning_sections:
  missed_warning_sections:
  runtime_seconds:

visual_evidence:
  figure_2d:
  figure_3d:
  before_after:
  notes:

decision:
  keep_for_paper: yes | no | pending
  decision_reason:
  rollback_or_reproduce_path:

limitations:
  ground_truth_limits:
  data_quality_limits:
  threshold_sensitivity:
  interpretation_notes:
```

## When to Create One

Create or update a passport when:

- A benchmark number is reported.
- A 2D/3D warning image is used as evidence.
- A clean-noise result is promoted or rolled back.
- A centerline or section-fitting result is used in the paper.
- A MATLAB/manual workflow comparison is reported.
- A deformation example is used to support a claim.

## Paper Evidence Rules

- Every figure must map to a dataset, commit hash, and workflow step.
- Every table must define baseline, candidate, metric units, and command/source.
- Every warning example must identify T0, Tn, threshold, section index, and whether the warning is local.
- Every clean-noise claim must compare before/after point counts and at least one quality metric.
- Every MATLAB comparison must state whether the comparison is algorithmic, workflow-level, or visual/manual.

## Example: Local Deformation Warning

```text
artifact_id: deform_warning_sample_001
artifact_type: figure
paper_section: Results
claim_supported: The tool highlights only the locally affected tunnel section in 2D and 3D.

data:
  dataset_name: sample_tunnel_case
  t0_file: T0_reference.pcd
  tn_file: Tn_deformed.pcd
  section_index_or_chainage: section 57 / chainage TBD
  coordinate_units: meters, deformation reported in millimeters
  source_notes: T0 used as reference scan, not absolute ground truth.

tool_version:
  commit_hash: TBD
  branch: feature/m3c2-gicp-integration
  baseline_version: first tool version
  candidate_version: current best warning implementation

method:
  workflow_step: step 6 deformation comparison
  command_or_ui_action: load T0/Tn, run deformation analysis, view 2D/3D warning
  clean_noise_config: TBD
  registration_config: TBD
  centerline_config: TBD
  section_config: TBD
  deformation_threshold_mm: TBD

metrics:
  rmse: TBD
  mae: TBD
  max_deviation_mm: TBD
  mean_deviation_mm: TBD
  warning_sections: TBD
  false_warning_sections: TBD
  missed_warning_sections: TBD
  runtime_seconds: TBD

visual_evidence:
  figure_2d: TBD
  figure_3d: TBD
  before_after: TBD
  notes: Verify warning does not spread to unaffected sections.

decision:
  keep_for_paper: pending
  decision_reason: Needs final benchmark numbers.
  rollback_or_reproduce_path: git checkout or rerun benchmark command from report.

limitations:
  ground_truth_limits: T0 is a reference scan unless independent truth exists.
  data_quality_limits: TBD
  threshold_sensitivity: TBD
  interpretation_notes: Negative/positive deformation direction must be defined.
```

