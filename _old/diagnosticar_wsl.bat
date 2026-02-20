@echo off
echo ========================================
echo   DIAGNÓSTICO WSL - EUROPA SCRAPER
echo ========================================
echo.

REM Ejecutar diagnóstico en WSL
wsl -d Ubuntu python3 /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/diagnosticar_wsl.py

echo.
echo ========================================
echo   DIAGNÓSTICO COMPLETADO
echo ========================================
echo.
echo Revisa la salida arriba para ver el estado del sistema.
echo.
pause