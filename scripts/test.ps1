# Windows PowerShell One-Command Test Runner for India Market AI Research Terminal
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " RUNNING COMPLETE TEST SUITE — INDIA MARKET TERMINAL " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Run Pytest Suite
Write-Host "[1/2] Running Pytest Unit & Integration Tests..." -ForegroundColor Yellow
pytest -v -k "not playwright"
$PytestExit = $LASTEXITCODE

# 2. Run Playwright Headless Browser Test
Write-Host "[2/2] Running Playwright Headless Terminal UI Test..." -ForegroundColor Yellow
pytest -v tests/test_ui_playwright.py
$PlaywrightExit = $LASTEXITCODE

if ($PytestExit -eq 0 -and $PlaywrightExit -eq 0) {
    Write-Host "`n[SUCCESS] ALL TEST SUITES PASSED 100%!" -ForegroundColor Green
} else {
    Write-Host "`n[FAIL] One or more test suites failed. Pytest: $PytestExit, Playwright: $PlaywrightExit" -ForegroundColor Red
}
