# Script de PowerShell para iniciar el sistema completo
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  INICIANDO SISTEMA EUROPA SCRAPER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si el servidor está corriendo
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/status" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✅ Servidor ya está corriendo en localhost:8000" -ForegroundColor Green
    $serverRunning = $true
} catch {
    Write-Host "❌ Servidor no está corriendo. Iniciando servidor..." -ForegroundColor Yellow
    $serverRunning = $false
}

# Iniciar servidor si no está corriendo
if (-not $serverRunning) {
    Write-Host "Iniciando servidor en WSL..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-Command", "wsl -d Ubuntu bash -c 'cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && source venv_wsl/bin/activate && cd server && python main.py'"
    Write-Host "Servidor iniciado en nueva ventana" -ForegroundColor Green
    Write-Host "Esperando 10 segundos para que el servidor inicie..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}

# Iniciar cliente
Write-Host "Iniciando cliente..." -ForegroundColor Yellow
Set-Location client
python main.py

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SISTEMA DETENIDO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan