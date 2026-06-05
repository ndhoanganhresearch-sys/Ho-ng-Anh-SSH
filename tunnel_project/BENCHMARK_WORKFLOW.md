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

### Deformation Warning

- Use T0 as reference and Tn as candidate/comparison scan.
- Warnings must be local: only affected sections should be highlighted.
- Verify both 2D and 3D displays.
- Record threshold in millimeters and whether positive/negative means inward/outward deformation.

### Centerline and Sections

- Check section fit in the window.
- Verify chainage order, section count, and frame orientation.
- Preserve tunnel aspect ratio in 3D views.
