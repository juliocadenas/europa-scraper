@echo off
echo ===============================================
echo   INSTALACIÓN FORZADA DE FASTAPI (WSL)
echo ===============================================
echo ⚠️  Esta opción usará --break-system-packages
echo    Solo usar si las otras opciones fallan
echo.

wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && chmod +x instalar_fastapi_forzado_wsl.sh && ./instalar_fastapi_forzado_wsl.sh"

echo.
echo ✅ Instalación forzada completada en WSL.
echo 🎯 Ahora puedes iniciar el servidor con: INICIAR_SERVIDOR_SIMPLE_WSL.bat
echo.
pause