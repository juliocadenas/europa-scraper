@echo off
echo ====================================
echo   INSTALANDO FASTAPI PARA EUROPA SCRAPER (WSL)
echo ====================================
echo.
echo Instalando FastAPI y dependencias esenciales en WSL...
echo.

wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && chmod +x instalar_fastapi_wsl.sh && ./instalar_fastapi_wsl.sh"

echo.
echo ✅ Instalación completada en WSL.
echo 🎯 Ahora puedes iniciar el servidor con: INICIAR_SERVIDOR_SIMPLE_WSL.bat
echo.
pause