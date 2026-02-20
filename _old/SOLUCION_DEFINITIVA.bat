@echo off
echo ================================================
echo   SOLUCIÓN DEFINITIVA - EUROPA SCRAPER
echo ================================================
echo.

echo 🚀 Paso 1: Iniciando servidor con IP específica...
start "Servidor WSL" wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && ./iniciar_servidor_ip_especifica.sh"

echo.
echo ⏳ Esperando 10 segundos para que el servidor inicie...
timeout /t 10 /nobreak > nul

echo.
echo 🔓 Paso 2: Configurando firewall (EJECUTAR COMO ADMIN)...
echo    Clic derecho en CONFIGURAR_FIREWALL.bat y "Ejecutar como administrador"
pause

echo.
echo 🌐 Paso 3: Obteniendo IP de WSL...
for /f "tokens=*" %%i in ('wsl -d Ubuntu bash -c "ip route show ^| grep -i default ^| awk '{ print \$3}"') do set WSL_IP=%%i

echo IP de WSL: %WSL_IP%

echo.
echo 🖥️  Paso 4: Iniciando cliente...
cd client
start "Cliente Windows" python main.py

echo.
echo ================================================
echo ✅ SOLUCIÓN COMPLETA
echo ================================================
echo 📡 Servidor corriendo en: %WSL_IP%:8001
echo 🖥️  Cliente iniciado
echo 💡 En el cliente ingresa: %WSL_IP%:8001
echo ================================================
pause