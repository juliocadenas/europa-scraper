@echo off
echo ====================================
echo   INICIANDO SERVIDOR EUROPA SCRAPER
echo ====================================
echo.
echo Iniciando servidor corregido en puerto 8001...
echo.

python server/server.py

echo.
echo Servidor detenido. Presiona cualquier tecla para cerrar...
pause > nul
