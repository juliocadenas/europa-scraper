@echo off
echo ========================================
echo   REINSTALACIÓN COMPLETA EUROPA SCRAPER
echo ========================================
echo.
echo Esto eliminará todo y lo reinstalará desde cero
echo para asegurar que httpx esté instalado.
echo.

REM Ejecutar reinstalación completa en WSL
wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && rm -rf venv_wsl && python3 EUROPA_SCRAPER_WSL.py"

echo.
echo ========================================
echo   REINSTALACIÓN COMPLETADA
echo ========================================
echo.
echo Ahora intenta iniciar el servidor:
echo INICIAR_SERVIDOR.bat
echo.
pause