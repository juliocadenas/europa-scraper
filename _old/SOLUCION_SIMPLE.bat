@echo off
echo ================================================
echo   SOLUCIÓN SIMPLE - EUROPA SCRAPER
echo ================================================
echo.

echo 1. INICIAR SERVIDOR WSL:
echo    Ejecuta en otra terminal: ./iniciar_servidor_wsl_simple.sh
echo.

echo 2. OBTENER IP WSL:
echo    Ejecuta: ip route show | grep default | awk "{print $3}"
echo.

echo 3. INICIAR CLIENTE WINDOWS:
echo    En el cliente, ingresa la IP:8001
echo.

echo EJEMPLO:
echo    Si la IP es 172.20.144.1
echo    En el cliente ingresa: 172.20.144.1:8001
echo.

echo ================================================
echo    ESTOS SON LOS PASOS. NADA MAS.
echo ================================================
pause