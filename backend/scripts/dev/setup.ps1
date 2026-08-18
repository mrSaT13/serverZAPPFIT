#Requires -Version 5.1
# ZAPFIT backend: one-time local environment setup (venv + deps + .env)
$ErrorActionPreference = 'Stop'

$backend = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $backend

# 1) Check Python and uv
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw 'Python not found on PATH.' }
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) { throw 'uv not found on PATH. Install it first (pip install uv or https://docs.astral.sh/uv/).' }

# 2) Create venv and install dependencies
if (-not (Test-Path '.venv')) {
    Write-Host '[1/5] Creating virtual environment...'
    uv venv .venv
} else {
    Write-Host '[1/5] Virtual environment already exists.'
}
Write-Host '[2/5] Installing dependencies (uv sync)...'
uv sync
Write-Host '[3/5] Installing Windows-only python-magic-bin (not tracked in uv.lock)...'
uv pip install python-magic-bin

# 3) Verify the Windows resource shim loads
Write-Host '[4/5] Verifying resource shim...'
& '.venv\Scripts\python.exe' -c "import sitecustomize; import resource; print('resource shim OK:', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)"

# 4) Create a local .env if missing
$envFile = Join-Path $backend '.env'
if (-not (Test-Path $envFile)) {
    Write-Host '[5/5] Creating local .env...'
    $fernet = & '.venv\Scripts\python.exe' -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    $secret = & '.venv\Scripts\python.exe' -c "import secrets; print(secrets.token_urlsafe(48))"
    @"
# Local development environment for ZAPFIT (created by scripts\dev\setup.ps1)
DB_PASSWORD=zapfit_local
DB_USER=zapfit
DB_DATABASE=zapfit
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=$secret
FERNET_KEY=$fernet
ZAPFIT_HOST=http://localhost:8080
RATE_LIMIT_ENABLED=false
# Extra CORS origins to reach the app by LAN IP, e.g.:
#CORS_ALLOWED_ORIGINS=http://192.168.1.50:8080,http://192.168.1.50:5173
"@ | Set-Content -Path $envFile -Encoding UTF8
    Write-Host "Created $envFile. Edit DB_* to match your local PostgreSQL."
} else {
    Write-Host '[5/5] .env already exists, leaving it untouched.'
}

Write-Host ''
Write-Host 'Done. Next steps:'
Write-Host '  1. Create a local PostgreSQL database (user/db from .env).'
Write-Host '  2. Run scripts\dev\migrate.ps1 to apply migrations.'
Write-Host '  3. Run scripts\dev\run.ps1 to start the API.'
Write-Host '  4. Run scripts\dev\smoke.ps1 to verify endpoints.'
