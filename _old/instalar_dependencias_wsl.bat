@echo off
echo Instalando dependencias para Europa Scraper en WSL/Linux...
echo.

REM Iniciar instalación de dependencias en WSL
wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && chmod +x instalar_dependencias_wsl.sh && ./instalar_dependencias_wsl.sh"

echo.
echo Dependencias instaladas en WSL.
echo Ahora puedes iniciar el servidor con: .\iniciar_servidor_wsl.bat
pause