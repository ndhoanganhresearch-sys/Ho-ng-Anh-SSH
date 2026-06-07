# Step 6 Parameter Review

Step 6 is the T1/Tn time-series and deformation-inspection workflow. It should
use a small set of primary parameters for decisions, and keep secondary geometry
as context so the 2D view stays readable.

## Required Inputs

- `T1` / reference epoch point cloud: baseline geometry.
- `Tn` / monitoring epoch point cloud: current geometry.
- Registered or pre-aligned epoch pair: needed before M3C2/C2C and section deltas are meaningful.
- Centerline and Frenet frames: needed for chainage-aware trend plots and 2D sections.
- Section geometries for T1 and Tn: needed for 2D overlay, deltas, warning markers, and dashboard alerts.

## Primary Decision Parameters

These should drive Step 6 warnings and reports.

- `dW = W1_Tn - W1_T1` in mm: clear-width change. Negative values mean convergence/reduced width.
- `dH = H1_Tn - H1_T1` in mm: clear-height change. Negative values mean clearance loss / settlement.
- `dR = R_Tn - R_T1` in mm: fitted-radius change. Negative values mean radius shrinkage.
- `dOval = ovality_Tn - ovality_T1` in percent: shape distortion change.
- `dEcc = eccentricity_Tn - eccentricity_T1` in mm: center-offset change.
- `clearance_min` in m: negative means the vehicle clearance envelope is violated.
- `M3C2/C2C distance_mm`: pointwise deformation map for heatmap and trend confirmation.
- `M3C2 quality_warning`: guards against partial coverage or unreliable epoch comparison.

## Context Parameters

These are useful for interpretation, but should not be the first warning driver
unless no reference epoch is available.

- `H1`, `W1`, `R`, `ovality`, `eccentricity` for the current Tn section.
- `H2`, `H3`, `W2`: shape context for crown/invert/base geometry.
- `wall_angle_L`, `wall_angle_R`: section-shape context, useful for box/U-type tunnels.
- `chainage`: positioning and navigation, not a deformation metric.
- `profile`: Circle/Box/U-type context, not a warning metric by itself.

## Visual-Only Parameters

These must never change numeric results or benchmark values.

- `Visual scale`: magnifies Tn-vs-T1 deformation in the 2D plot so small mm-level changes can be seen.
- `Animate alpha`: blends the T1/Tn display during animation.
- Overlay colors, warning marker colors, and chainage-ruler marker style.

## Parameters To Avoid As Primary Step 6 Warnings

- Raw `H1`, `W1`, or `R` without a T1 reference: absolute geometry can be a design/profile difference, not deformation.
- Raw point count difference: useful as a quality check, but not a deformation magnitude.
- RGB/intensity values: useful for loading/label/context, not structural deformation.
- Absolute global X/Y/Z positions after registration: use section-local deltas or M3C2/C2C instead.

## Current Warning Bands

- `dW`, `dH`, `dR`: caution at `10 mm`, critical at `25 mm`.
- `dOval`: caution at `0.5%`, critical at `1.0%`.
- `dEcc`: caution at `10 mm`, critical at `25 mm`.
- `clearance_min < 0`: critical.

## Dataset Coverage Needed

Two Blender-generated T1/Tn dataset versions are enough to test the full Step 6
surface:

- Version 1: small/subtle deformation. Tests trend/M3C2 sensitivity and 2D visual scaling without obvious geometry changes.
- Version 2: complex deformation with noise, occlusion, cable clutter, clearance intrusion, and local critical sections. Tests clean noise, warnings, heatmap, 2D overlay, 3D warning markers, and chainage navigation.
