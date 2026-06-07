param(
    [string]$Python = "..\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Python)) {
    throw "Python interpreter not found: $Python"
}

Write-Host "[1/5] Compile tunnel_analysis"
& $Python -m compileall -q tunnel_analysis
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/5] Smoke: geometry"
& $Python run_all_smoke.py geometry
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/5] Smoke: txt_reader"
& $Python run_all_smoke.py txt_reader
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/5] Guard: user-site isolation"
& $Python test_usersite_guard.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[5/5] Guard: headless render imports"
& $Python test_headless_imports.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "QUICK VERIFICATION PASSED"
