$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".obsidian-mcp.env"
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
      [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
  }
}
if (-not $env:OBSIDIAN_API_KEY) {
  throw "OBSIDIAN_API_KEY is missing. Check .obsidian-mcp.env or Obsidian Local REST API settings."
}
& npx -y obsidian-mcp-server@3.2.8
