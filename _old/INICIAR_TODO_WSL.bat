@echo off
echo ================================================
echo   INICIANDO SISTEMA COMPLETO EUROPA SCRAPER
echo ================================================
echo.

echo 📦 Paso 1: Instalando dependencias si es necesario...
call INSTALAR_FASTAPI_WSL.bat

echo.
echo 🚀 Paso 2: Iniciando servidor en WSL...
start "Servidor WSL" wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && ./iniciar_servidor_wsl_simple.sh"

echo.
echo ⏳ Esperando 10 segundos para que el servidor inicie...
timeout /t 10 /nobreak

echo.
echo 🌐 Paso 3: Obteniendo IP de WSL...
wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && ./obtener_ip_wsl.sh"

echo.
echo 🖥️  Paso 4: Iniciando cliente en Windows...
cd client
start "Cliente Windows" python main.py

echo.
echo ✅ Sistema iniciado completamente
echo 💡 Usa la IP que se mostró en el paso 3 para configurar el cliente
echo 📝 Si el cliente no conecta, ciérralo y vuelve a iniciar con la IP correcta
echo.
pause