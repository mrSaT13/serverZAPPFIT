#Requires -Version 5.1
# ZAPFIT backend: apply all Alembic migrations (requires a reachable PostgreSQL)
$ErrorActionPreference = 'Stop'

$backend = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$venvPython = Join-Path $backend '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) { throw 'Virtual environment missing. Run scripts\dev\setup.ps1 first.' }

Set-Location (Join-Path $backend 'app')
& $venvPython -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'alembic upgrade failed.' }
