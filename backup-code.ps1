param(
    [Parameter(Mandatory = $false)]
    [string]$SourcePath = ".",

    [Parameter(Mandatory = $false)]
    [string]$BackupRoot = "$HOME\CodeBackups"
)

$ErrorActionPreference = "Stop"

$resolvedSource = (Resolve-Path $SourcePath).Path

if (-not (Test-Path $BackupRoot)) {
    New-Item -Path $BackupRoot -ItemType Directory | Out-Null
}

$projectName = Split-Path -Path $resolvedSource -Leaf
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zipName = "$projectName-$timestamp.zip"
$zipPath = Join-Path $BackupRoot $zipName

Write-Host "Backing up: $resolvedSource"
Write-Host "Output file: $zipPath"

# Zip only the project contents to keep extraction clean.
$sourceItems = Join-Path $resolvedSource "*"
Compress-Archive -Path $sourceItems -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host "Backup completed successfully."
