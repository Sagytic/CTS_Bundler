# Save pytest + vitest logs to docs/E2E_EVIDENCE/test-outputs/
# Run from repo root: .\scripts\capture-test-results.ps1

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Root "docs\E2E_EVIDENCE\test-outputs"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$PyPy = Join-Path $Root "backend\venv\Scripts\python.exe"
if (-not (Test-Path $PyPy)) {
    Write-Warning "backend venv not found; using python on PATH"
    $PyPy = "python"
}

$PytestOut = Join-Path $OutDir "pytest-output.txt"
$HtmlOut = Join-Path $OutDir "pytest-report.html"

Write-Host "== pytest (backend) ==" -ForegroundColor Cyan
Push-Location (Join-Path $Root "backend")

$pytestCmd = @("-m", "pytest", ".", "-v", "--tb=short")
& $PyPy -c "import pytest_html" 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    $pytestCmd += @("--html=$HtmlOut", "--self-contained-html")
    Write-Host "(pytest-html: also writing HTML)"
}

& $PyPy @pytestCmd 2>&1 | Tee-Object -FilePath $PytestOut
$pytestExit = $LASTEXITCODE
Pop-Location

if (-not (Test-Path $HtmlOut)) {
    Write-Host "No HTML: pip install pytest-html to enable" -ForegroundColor DarkYellow
}

Write-Host "== vitest (frontend) ==" -ForegroundColor Cyan
Push-Location (Join-Path $Root "frontend")
$VitestOut = Join-Path $OutDir "vitest-output.txt"
npm run test:run 2>&1 | Tee-Object -FilePath $VitestOut
$vitestExit = $LASTEXITCODE
Pop-Location

Write-Host ""
Write-Host "Done: $OutDir" -ForegroundColor Green
Write-Host "  - pytest-output.txt"
Write-Host "  - vitest-output.txt"
if (Test-Path $HtmlOut) {
    Write-Host "  - pytest-report.html"
}

if ($pytestExit -ne 0 -or $vitestExit -ne 0) {
    exit 1
}
