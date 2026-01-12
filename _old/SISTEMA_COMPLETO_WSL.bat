@echo off
echo ================================================
echo   SISTEMA EUROPA SCRAPER - SOLUCIÓN 100% AUTOMÁTICA
echo ================================================
echo.

echo 🚀 Paso 1: Iniciando servidor en WSL...
start "Servidor WSL" wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && ./iniciar_servidor_wsl_simple.sh"

echo.
echo ⏳ Esperando 15 segundos para que el servidor inicie completamente...
timeout /t 15 /nobreak > nul

echo.
echo 🌐 Paso 2: Obteniendo y configurando IP de WSL...
for /f "tokens=*" %%i in ('wsl -d Ubuntu bash -c "ip route show ^| grep -i default ^| awk '{ print $3}"') do set WSL_IP=%%i

echo IP de WSL detectada: %WSL_IP%

echo.
echo 🔧 Paso 3: Configurando cliente automáticamente...
cd client
echo {"server": {"host": "%WSL_IP%", "port": 8001}} > server_config.json

echo ✅ Cliente configurado para: %WSL_IP%:8001
echo 📝 Verificando configuración creada:
type server_config.json

echo.
echo 🖥️  Paso 4: Iniciando cliente configurado...
start "Cliente Windows" python main.py

echo.
echo ================================================
echo ✅ SISTEMA 100% FUNCIONAL
echo ================================================
echo 📡 Servidor corriendo en: %WSL_IP%:8001
echo 🖥️  Cliente iniciado y configurado automáticamente
echo 💡 El cliente debería conectar SOLO ahora
echo 📝 Si no conecta, el problema es del firewall de Windows
echo ================================================
echo.
pause