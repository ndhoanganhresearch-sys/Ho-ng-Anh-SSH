artifact_id: auto_denoise_blender_001
artifact_type: benchmark table
paper_section: Section 4 / Section 11
claim_supported: The tunnel-specific denoising cascade reduces labelled clutter while preserving tunnel lining points.

data:
  dataset_name: data/blender_test_suite/case_03_noise_and_cables
  t0_file: N/A
  tn_file: N/A
  section_index_or_chainage: N/A
  coordinate_units: meters
  source_notes: Synthetic/Blender labelled tunnel fixture, not real tunnel validation.

tool_version:
  commit_hash: 84c02cc
  branch: feature/m3c2-gicp-integration
  baseline_version: N/A (no prior method to compare)
  candidate_version: current auto_denoise implementation (3-stage cascade)

method:
  workflow_step: auto-denoise benchmark
  command_or_ui_action: ..\.venv\Scripts\python.exe benchmark_blender_dataset.py
  clean_noise_config: PCA k=20, linearity>=0.30, sphericity>=0.12; MAD k=2.5, factor=1.4826; grid 60x180, protrusion=0.05m; safety_guard=30%
  registration_config: N/A
  centerline_config: N/A
  section_config: N/A
  deformation_threshold_mm: N/A

metrics:
  noise_recall: 0.8264
  lining_retention: 0.9999
  raw_points: 8068
  clean_points: 7191
  removed_points: 877
  runtime_seconds: 0.10

visual_evidence:
  figure_2d: TODO
  figure_3d: TODO
  before_after: TODO
  notes: Need a publication-quality before/after figure before using this in Results.

decision:
  keep_for_paper: pending
  decision_reason: Numeric benchmark exists, but commit hash and visual evidence are missing.
  rollback_or_reproduce_path: data/blender_test_suite/benchmark_report.json and benchmark_blender_dataset.py

limitations:
  ground_truth_limits: Synthetic labels; not a substitute for real tunnel field validation.
  data_quality_limits: Single benchmark case currently summarized.
  threshold_sensitivity: TODO
  interpretation_notes: Claim should be limited to the benchmark fixture until real labelled data are available.
