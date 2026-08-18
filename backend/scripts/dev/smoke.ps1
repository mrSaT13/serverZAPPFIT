#Requires -Version 5.1
# ZAPFIT backend: smoke checks against a running API instance
param(
    [string]$BaseUrl = 'http://localhost:8080'
)
$ErrorActionPreference = 'Stop'

# Bypass the system proxy so localhost checks are direct (IE/proxy settings
# from the interactive session can leak into a fresh PowerShell process).
[System.Net.WebRequest]::DefaultWebProxy = $null
$env:NO_PROXY = $BaseUrl

$checks = @(
    @{ Name = 'OpenAPI schema';      Path = '/openapi.json';                                 Expect = 'openapi' },
    @{ Name = 'About';               Path = '/api/v1/about';                                 Expect = '"name"' },
    @{ Name = 'Setup status';        Path = '/api/v1/public/server_settings/setup-status';   Expect = 'setup_completed' },
    @{ Name = 'Setup options';       Path = '/api/v1/public/server_settings/setup-options';  Expect = '"themes"' }
)

$failed = $false
foreach ($check in $checks) {
    try {
        $response = Invoke-WebRequest -Uri ($BaseUrl + $check.Path) -Method Get -TimeoutSec 10 -UseBasicParsing
        if ($response.StatusCode -ne 200) {
            Write-Host ("[FAIL] {0}  {1}  -> HTTP {2}" -f $check.Name, $check.Path, $response.StatusCode)
            $failed = $true
            continue
        }
        $body = [string]$response.Content
        if ($body -match $check.Expect) {
            Write-Host ("[OK]   {0}  {1}" -f $check.Name, $check.Path)
        } else {
            Write-Host ("[FAIL] {0}  {1}  -> response missing '{2}'" -f $check.Name, $check.Path, $check.Expect)
            $failed = $true
        }
    } catch {
        Write-Host ("[FAIL] {0}  {1}  -> {2}" -f $check.Name, $check.Path, $_.Exception.Message)
        $failed = $true
    }
}

if ($failed) {
    Write-Host ''
    Write-Host 'Some smoke checks failed.'
    exit 1
}
Write-Host ''
Write-Host 'All smoke checks passed.'
