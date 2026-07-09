param(
    [Parameter(Position = 0)]
    [ValidateSet("quick", "step6", "box", "weekly", "ai", "compile", "status")]
    [string]$Mode = "quick",

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Files = @(),

    [string]$Python = "..\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [string]$Label,
        [string]$Command,
        [string[]]$Arguments
    )

    Write-Host "==> $Label"
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Failed: $Label (exit code $LASTEXITCODE)"
    }
}

function Assert-Python {
    if (-not (Test-Path $Python)) {
        throw "Python interpreter not found: $Python"
    }
}

function Show-Status {
    Write-Host "==> Git status"
    git status --short

    Write-Host "`n==> Suggested gates"
    Write-Host "quick   : .\agent_verify.ps1 quick"
    Write-Host "step6   : .\agent_verify.ps1 step6"
    Write-Host "box     : .\agent_verify.ps1 box"
    Write-Host "weekly  : .\agent_verify.ps1 weekly"
    Write-Host "ai      : .\agent_verify.ps1 ai"
    Write-Host "compile : .\agent_verify.ps1 compile <files>"
}

Push-Location $PSScriptRoot
try {
    switch ($Mode) {
        "status" {
            Show-Status
        }
        "quick" {
            Assert-Python
            Invoke-Checked -Label "Quick verification" -Command ".\verify_quick.ps1" -Arguments @($Python)
        }
        "step6" {
            Assert-Python
            Invoke-Checked -Label "Step 6 / T0-Tn verification" -Command ".\verify_step6.ps1" -Arguments @($Python)
        }
        "box" {
            Assert-Python
            Invoke-Checked -Label "Box four spots smoke" -Command $Python -Arguments @("smoke_test_box_four_spots.py")
            Invoke-Checked -Label "Box ICP shift smoke" -Command $Python -Arguments @("smoke_test_box_icp_shift.py")
        }
        "weekly" {
            Assert-Python
            Invoke-Checked -Label "Quick verification" -Command ".\verify_quick.ps1" -Arguments @($Python)
            Invoke-Checked -Label "Box four spots smoke" -Command $Python -Arguments @("smoke_test_box_four_spots.py")
            Invoke-Checked -Label "Box ICP shift smoke" -Command $Python -Arguments @("smoke_test_box_icp_shift.py")
        }
        "ai" {
            Assert-Python
            $aiFiles = @(
                "tunnel_analysis\headroom_adapter.py",
                "tunnel_analysis\rag_ai.py",
                "tunnel_analysis\digital_twin.py"
            )
            Invoke-Checked -Label "Compile AI integration files" -Command $Python -Arguments (@("-m", "py_compile") + $aiFiles)
            Invoke-Checked -Label "Headroom adapter smoke test" -Command $Python -Arguments @("smoke_test_headroom_adapter.py")
            Invoke-Checked -Label "Advanced integrations smoke test" -Command $Python -Arguments @("smoke_test_advanced_integrations.py")
        }
        "compile" {
            Assert-Python
            if ($Files.Count -eq 0) {
                throw "Provide at least one file for compile mode. Example: .\agent_verify.ps1 compile tunnel_analysis\parameters.py"
            }
            Invoke-Checked -Label "Compile selected Python files" -Command $Python -Arguments (@("-m", "py_compile") + $Files)
        }
    }
}
finally {
    Pop-Location
}
