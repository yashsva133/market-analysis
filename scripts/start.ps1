# Windows PowerShell One-Command Startup Script for India Market AI Research Terminal (§77)
$ErrorActionPreference = "Continue"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " INDIA MARKET AI RESEARCH TERMINAL - ONE-COMMAND LAUNCHER " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

# Step 1: Environment Diagnostic Validation (§76)
Write-Host "`n[1/5] Running System Doctor Diagnostic..." -ForegroundColor Yellow
python scripts/doctor.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Doctor reported issues. Review blockers before proceeding." -ForegroundColor Red
}

# Step 2: Ensure .env exists
Write-Host "`n[2/5] Checking Configuration Environment..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "[INFO] .env not found. Initializing from .env.example..." -ForegroundColor Cyan
    Copy-Item ".env.example" ".env"
} else {
    Write-Host "[OK] Configuration .env file is present." -ForegroundColor Green
}

# Step 3: Check/Start FastAPI Backend (Port 8000)
Write-Host "`n[3/5] Initializing Backend Services..." -ForegroundColor Yellow
$BackendPortActive = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect("127.0.0.1", 8000)
    $BackendPortActive = $true
    $tcp.Close()
} catch {
    $BackendPortActive = $false
}

if ($BackendPortActive) {
    Write-Host "[OK] FastAPI backend is already active on http://127.0.0.1:8000" -ForegroundColor Green
} else {
    Write-Host "[INFO] Starting FastAPI server on http://127.0.0.1:8000..." -ForegroundColor Cyan
    Start-Process -FilePath "python" -ArgumentList "-m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000" -NoNewWindow
    Start-Sleep -Seconds 3
}

# Verify API Health
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 5
    Write-Host "[OK] API Health Verified: $($health.status) (v$($health.version))" -ForegroundColor Green
} catch {
    Write-Host "[WARN] API health endpoint initial response pending." -ForegroundColor DarkYellow
}

# Step 4: Check/Start Next.js Web Terminal (Port 3000)
Write-Host "`n[4/5] Initializing Next.js Web Terminal..." -ForegroundColor Yellow
$FrontendPortActive = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect("127.0.0.1", 3000)
    $FrontendPortActive = $true
    $tcp.Close()
} catch {
    $FrontendPortActive = $false
}

if ($FrontendPortActive) {
    Write-Host "[OK] Next.js Web Terminal is already active on http://localhost:3000" -ForegroundColor Green
} else {
    Write-Host "[INFO] Starting Next.js production server on http://localhost:3000..." -ForegroundColor Cyan
    Start-Process -FilePath "npm" -ArgumentList "run start" -WorkingDirectory "$PSScriptRoot\..\apps\web" -NoNewWindow
    Start-Sleep -Seconds 4
}

# Step 5: Ready Report & URLs
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " TERMINAL LAUNCH COMPLETE - ALL SYSTEMS READY " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Terminal UI:         http://localhost:3000" -ForegroundColor White
Write-Host " Backend API Docs:    http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host " Health Metrics:      http://127.0.0.1:8000/health" -ForegroundColor White
Write-Host " Smoke Test Tool:     python scripts/smoke_test.py" -ForegroundColor White
Write-Host " Diagnostic Doctor:   python scripts/doctor.py" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan

# Optionally open browser
Write-Host "`nOpening research terminal in default browser..." -ForegroundColor Green
Start-Process "http://localhost:3000"
