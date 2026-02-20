@echo off
echo ========================================
echo   EUROPA SCRAPER - SOLUCIÓN DEFINITIVA
echo ========================================
echo.
echo Este script resolverá TODOS los problemas de dependencias
echo y limpiará los archivos innecesarios.
echo.

REM Ejecutar el script Python definitivo
wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && python3 EUROPA_SCRAPER_WSL.py"

echo.
echo ========================================
echo   PROCESO COMPLETADO
echo ========================================
echo.
echo Si la instalación fue exitosa, ahora puedes:
echo.
echo 1. Para iniciar el servidor:
echo    INICIAR_SERVIDOR.bat
echo.
echo 2. Para iniciar el cliente:
echo    INICIAR_CLIENTE.bat
echo.
echo ========================================
pause