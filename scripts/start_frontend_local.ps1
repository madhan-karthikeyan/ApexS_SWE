Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendPath = Join-Path $repoRoot "frontend"
Set-Location $frontendPath

npm run dev -- --host 0.0.0.0 --port 5173
