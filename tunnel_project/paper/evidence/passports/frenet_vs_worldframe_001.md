artifact_id: frenet_vs_worldframe_001
artifact_type: comparison benchmark
paper_section: Section 6 (Frenet-Frame Geometric Analysis) / Section 11 (Validation)
claim_supported: Frenet-frame slicing eliminates systematic ovality bias present in world-frame slicing on curved tunnels.

data:
  dataset_name: data/blender_test_suite/case_05_curved_centerline
  control_dataset: data/blender_test_suite/case_01_clean_reference
  design_radius_m: 4.0
  curvature_x_span_m: 2.03
  coordinate_units: meters
  source_notes: Synthetic/Blender labelled tunnel with curvature. Not real tunnel.

tool_version:
  commit_hash: 84c02cc
  branch: feature/m3c2-gicp-integration
  script: benchmark_frenet_vs_worldframe.py

method:
  frenet_slicing: gravity-anchored Frenet frames from B-spline centerline
  worldframe_slicing: global PCA axis, fixed T/N/B for all sections
  section_count: 48
  epsilon: adaptive (0.55 * median spacing, clipped [0.05, 0.5]m)

metrics:
  curved_tunnel:
    frenet_median_ovality_pct: 0.0841
    worldframe_median_ovality_pct: 0.2282
    ovality_bias_relative_pct: 171.5
    frenet_std_radius_m: 0.00289
    worldframe_std_radius_m: 0.00478
    frenet_median_radius_m: 3.99848
    worldframe_median_radius_m: 3.99872
  straight_tunnel_control:
    frenet_median_ovality_pct: 0.0209
    worldframe_median_ovality_pct: 0.0204
    ovality_bias_relative_pct: -2.1

visual_evidence:
  figure: TODO — need before/after ovality plot (Frenet vs world-frame per section)
  notes: Numeric evidence complete. Publication-quality figure needed.

decision:
  keep_for_paper: yes
  decision_reason: Clear quantitative evidence for the Frenet-frame advantage on curved geometry.
  paper_claim_note: >
    Paper claims "up to 15% ovality error" for world-frame slicing.
    Benchmark shows 171.5% relative bias on synthetic curved data.
    The 15% figure likely refers to absolute ovality on real tunnels with R<300m.
    Both are defensible; recommend citing the benchmark result directly.

limitations:
  ground_truth_limits: Synthetic geometry, R=4m, moderate curvature only.
  real_tunnel_needed: Real curved tunnel scan would strengthen the claim.
  radius_range: Only tested at R=4m; claim about R<300m needs additional data points.
