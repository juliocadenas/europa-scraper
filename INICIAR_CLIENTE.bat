@echo off
chcp 65001 > nul
setlocal

:: Asegurar que el directorio de trabajo es el del script
cd /d "%~dp0"

echo ========================================
echo   INICIANDO CLIENTE EUROPA SCRAPER
echo ========================================
echo.
echo Asegúrate de que el servidor esté corriendo
echo en otra terminal antes de iniciar el cliente.
echo.

python client/main.py

echo.
echo ========================================
echo   CLIENTE DETENIDO
echo ========================================
pause