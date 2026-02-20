@echo off
echo ========================================
echo   INSTALANDO HTTPX MANUALMENTE
echo ========================================
echo.
echo Instalando httpx directamente en el entorno virtual...
echo.

REM Instalar httpx directamente en el entorno virtual
wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && ./venv_wsl/bin/pip install httpx>=0.25.0"

echo.
echo Verificando instalación...
wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && ./venv_wsl/bin/python -c 'import httpx; print(\"httpx instalado correctamente\")'"

echo.
echo ========================================
echo   INSTALACIÓN COMPLETADA
echo ========================================
echo.
echo Ahora intenta iniciar el servidor:
echo INICIAR_SERVIDOR.bat
echo.
pause