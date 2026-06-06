# Blender Test Suite

Synthetic tunnel point-cloud cases generated from Blender for testing the tunnel analysis tool. The `.blend` file keeps the visual scene; the `.txt` files are direct inputs for the Python tool.

Each case contains:

- T0.txt: reference scan, columns x y z r g b
- Tn.txt: candidate scan, columns x y z r g b
- T0_labels.txt / Tn_labels.txt: x y z r g b intensity label
- ground_truth.json: expected deformation/noise/clearance behavior

Use T0 as the reference scan and Tn as the compared scan. The longitudinal axis is Y, vertical is Z, and units are meters. Deformation truth is reported in millimeters.

## Case Map

| Case | Main purpose | Expected behavior |
| --- | --- | --- |
| case_01_clean_reference | Load, centerline, section fitting, clean no-warning baseline | T0 and Tn are effectively identical |
| case_02_local_deformation | Step 6 T0/Tn deformation and 2D/3D local warning | Local warning around chainage -6 m to +6 m |
| case_03_noise_and_cables | Clean-noise and label-aware denoise benchmark | Remove outliers/cable while preserving lining |
| case_04_clearance_intrusion | Clearance/headroom warning | Intruding duct should violate a 2.2 m gauge |
| case_05_curved_centerline | Curved centerline, section frames, registration, chainage order | Centerline should follow the curved tunnel |
| case_06_occlusion_sparse | Sparse/occluded section robustness and UI fit | Sections should remain stable despite missing arc |

## Recommended Verification

Run `..\.venv\Scripts\python.exe smoke_test_blender_dataset.py` from `tunnel_project` to verify the files can be loaded by the tool.
