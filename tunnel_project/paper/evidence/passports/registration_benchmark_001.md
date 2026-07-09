artifact_id: registration_benchmark_001
artifact_type: benchmark table
paper_section: Section 5 (Registration) / Section 11 (Validation)
claim_supported: GICP registration achieves sub-millimetre RMSE on tunnel geometry and 20-60x speedup over Open3D ICP.

data:
  dataset_1: data/sample_pcd/circle_tunnel_dw.las (400K pts, straight)
  dataset_2: data/full_test/T0_full.las (150K pts, curved)
  coordinate_units: meters
  source_notes: Synthetic rigid transform recovery (1.2 deg yaw + 7cm translation).

tool_version:
  commit_hash: 84c02cc
  branch: feature/m3c2-gicp-integration
  script: benchmark_registration.py

metrics:
  circle_tunnel_straight:
    small_gicp_rmse_mm: 0.198
    small_gicp_time_ms: 587
    open3d_p2plane_rmse_mm: 31.735
    open3d_p2plane_time_ms: 11953
    speedup: 20.35x
  full_test_curved:
    small_gicp_rmse_mm: 70.958
    small_gicp_time_ms: 410
    open3d_p2plane_rmse_mm: 115.915
    open3d_p2plane_time_ms: 25182
    speedup: 61.36x
  pipeline_icp_recovery:
    full_test_rmse_mm: 0.224
    case_03_rmse_mm: 0.041

decision:
  keep_for_paper: yes
  decision_reason: Clear sub-mm RMSE on straight geometry; curved geometry RMSE is high because the 1.2-degree perturbation exceeds convergence basin without coarse alignment. In production, GROR runs first.

limitations:
  synthetic_transform: Known rigid transform, not real multi-station misalignment.
  curved_note: High RMSE on curved data reflects missing coarse alignment step, not algorithm failure.
