param(
    [string]$Python = "..\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Python)) {
    throw "Python interpreter not found: $Python"
}

$tests = @(
    "test_t0_reference.py",
    "test_register_epochs.py",
    "test_curved_eccentricity.py",
    "test_deformation_groundtruth.py",
    "test_step6_evaluation.py",
    "test_pipeline_end_to_end.py",
    "test_2d_consistency.py",
    "test_section_controls.py",
    "test_section_widget.py",
    "smoke_test_step6_t1_tn_dataset.py"
)

for ($i = 0; $i -lt $tests.Count; $i++) {
    $name = $tests[$i]
    Write-Host ("[{0}/{1}] {2}" -f ($i + 1), $tests.Count, $name)
    & $Python $name
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "STEP 6 / T0-Tn VERIFICATION PASSED"
