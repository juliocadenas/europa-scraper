@echo off
echo ====================================
echo   INICIANDO FRONTEND EUROPA SCRAPER
echo ====================================
echo.

echo [1/2] Conectando a red Tailscale correcta...
tailscale switch juliocadenas@gmail.com
if %errorlevel% neq 0 (
    echo ADVERTENCIA: No se pudo cambiar la red Tailscale.
    echo Continuando de todos modos...
)
echo.

echo [2/2] Iniciando interfaz grafica...
echo.

python gui/scraper_gui.py

echo.
echo Frontend detenido. Presiona cualquier tecla para cerrar...
pause > nul