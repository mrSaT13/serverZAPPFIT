#Requires -Version 5.1
# ZAPFIT backend: start the API with uvicorn
# Usage: .\scripts\dev\run.ps1 [[--reload]] [extra uvicorn args...]
$ErrorActionPreference = 'Stop'

$backend = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$venvPython = Join-Path $backend '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) { throw 'Virtual environment missing. Run scripts\dev\setup.ps1 first.' }

Set-Location (Join-Path $backend 'app')
& $venvPython -m uvicorn app.main:app --host 0.0.0.0 --port 8080 @args
