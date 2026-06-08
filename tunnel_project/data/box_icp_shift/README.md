# Box ICP Shift Dataset

Short centered box tunnel with a rigidly shifted Tn for ICP registration.

- Rigid transform: yaw 9.0 deg, shift [1.8, 7.5, 0.55] m.
- Use `T0_box_icp.las` / `.txt` as reference.
- Use `Tn_box_icp.las` / `.txt` as monitoring.
- LAS offsets are zero; the shift is in the point coordinates.
- Designed to test ICP / register_epochs plus the rest of the pipeline.
