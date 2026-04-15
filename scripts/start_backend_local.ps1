Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pythonExe = Join-Path $repoRoot ".venv311\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python environment not found at $pythonExe. Create it first with: py -3.11 -m venv .venv311"
}

# Local-safe backend config: SQLite + thread worker fallback.
$env:DATABASE_URL = "sqlite:///./backend/apexs.db"
$env:USE_CELERY = "false"
$env:ALLOW_THREAD_FALLBACK = "true"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:MINIO_ENDPOINT = "localhost:9000"
$env:ENFORCE_AUTH = "false"

& $pythonExe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
