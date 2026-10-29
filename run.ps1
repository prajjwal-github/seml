<#
.SYNOPSIS
    SecureWipe - Local Development Runner (PowerShell)
    Launches PostgreSQL (port 5434), FastAPI (port 8001), and Vite (port 5173).
#>

Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host " SecureWipe - Certified IT Asset Recycling Platform (Simulation Mode)" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. PostgreSQL
$pgActive = (Get-NetTCPConnection -LocalPort 5434 -State Listen -ErrorAction SilentlyContinue)
if (-not $pgActive) {
    Write-Host "[1/3] Starting PostgreSQL daemon on port 5434..." -ForegroundColor Yellow
    Start-Process -FilePath "C:\Program Files\PostgreSQL\18\bin\postgres.exe" -ArgumentList "-D `"$Root\pgdata`" -p 5434" -WindowStyle Minimized
    Start-Sleep -Seconds 3
} else {
    Write-Host "[1/3] PostgreSQL is already listening on port 5434." -ForegroundColor Green
}

# 2. FastAPI Backend
$backendActive = (Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue)
if (-not $backendActive) {
    Write-Host "[2/3] Starting FastAPI backend on port 8001..." -ForegroundColor Yellow
    Start-Process -FilePath "$Root\.venv\Scripts\uvicorn.exe" -ArgumentList "backend.app.main:app --host 127.0.0.1 --port 8001 --reload" -WorkingDirectory $Root
    Start-Sleep -Seconds 2
} else {
    Write-Host "[2/3] FastAPI backend is already listening on port 8001." -ForegroundColor Green
}

# 3. Vite Frontend
$frontendActive = (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue)
if (-not $frontendActive) {
    Write-Host "[3/3] Starting Vite frontend on port 5173..." -ForegroundColor Yellow
    Start-Process -FilePath "npm.cmd" -ArgumentList "run dev" -WorkingDirectory "$Root\frontend"
} else {
    Write-Host "[3/3] Vite frontend is already listening on port 5173." -ForegroundColor Green
}

Write-Host "`nAll platform services are operational:" -ForegroundColor Cyan
Write-Host "  - Web UI:           http://127.0.0.1:5173" -ForegroundColor White
Write-Host "  - Backend API Docs: http://127.0.0.1:8001/docs" -ForegroundColor White
Write-Host "  - Health Check:     http://127.0.0.1:8001/health" -ForegroundColor White
Write-Host "  - Public Verifier:  http://127.0.0.1:5173/verify" -ForegroundColor White
Write-Host "`nPre-seeded Demo Personas:" -ForegroundColor Yellow
Write-Host "  Operator: operator@securewipe.local / Operator123!" -ForegroundColor Gray
Write-Host "  Approver: approver@securewipe.local / Approver123!" -ForegroundColor Gray
Write-Host "  Admin:    admin@securewipe.local    / Admin123!" -ForegroundColor Gray
