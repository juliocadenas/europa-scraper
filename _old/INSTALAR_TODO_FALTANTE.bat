@echo off
echo ========================================
echo   INSTALANDO TODAS LAS DEPENDENCIAS FALTANTES
echo ========================================
echo.
echo Instalando httpx, aiohttp y todas las dependencias faltantes...
echo.

REM Instalar todas las dependencias faltantes
wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && ./venv_wsl/bin/pip install httpx aiohttp aiofiles beautifulsoup4 lxml openpyxl selenium webdriver-manager playwright pyee greenlet typing-extensions python-multipart python-dotenv pandas requests fastapi uvicorn[standard]"

echo.
echo Verificando instalación principal...
wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && ./venv_wsl/bin/python -c 'import httpx; import aiohttp; print(\"httpx y aiohttp instalados correctamente\")'"

echo.
echo ========================================
echo   INSTALACIÓN COMPLETADA
echo ========================================
echo.
echo Ahora intenta iniciar el servidor:
echo INICIAR_SERVIDOR.bat
echo.
pause