# Script para hacer ejecutables los scripts .sh en WSL
Write-Host "🔧 Haciendo ejecutables los scripts de WSL..." -ForegroundColor Green

# Ruta del proyecto
$projectPath = "C:\Users\julio\Documents\DOCUPLAY\Proyecto\Python\EUROPA\V3.1-LINUX"

# Hacer ejecutables los scripts .sh
Write-Host "📝 Dando permisos de ejecución a los scripts .sh..." -ForegroundColor Yellow
bash -c "cd '$projectPath' && chmod +x iniciar_servidor_wsl_optimizado.sh iniciar_frontend_wsl.sh"

Write-Host "✅ Scripts .sh ahora son ejecutables" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Ahora puedes ejecutar:" -ForegroundColor Cyan
Write-Host "   wsl ./iniciar_servidor_wsl_optimizado.sh" -ForegroundColor White
Write-Host "   wsl ./iniciar_frontend_wsl.sh" -ForegroundColor White
Write-Host ""
Write-Host "🚀 O ejecuta los scripts .bat para Windows:" -ForegroundColor Cyan
Write-Host "   .\INICIAR_SERVIDOR_WSL.bat" -ForegroundColor White
Write-Host "   .\INICIAR_FRONTEND_WSL.bat" -ForegroundColor White