@echo off
echo ================================================
echo   CONFIGURANDO CLIENTE PARA WSL
echo ================================================
echo.

echo 🌐 Obteniendo IP de WSL...
for /f "tokens=*" %%i in ('wsl -d Ubuntu bash -c "ip route show ^| grep -i default ^| awk '{ print $3}"') do set WSL_IP=%%i

echo IP de WSL detectada: %WSL_IP%

echo.
echo 🔧 Configurando cliente para usar la IP de WSL...

cd client
echo {"server": {"host": "%WSL_IP%", "port": 8001, "auto_detect_wsl": true}} > server_config.json

echo ✅ Cliente configurado para conectar a: %WSL_IP%:8001

echo.
echo 🚀 Iniciando cliente configurado...
start "Cliente Windows" python main.py

echo.
echo 💡 El cliente ahora debería conectar automáticamente al servidor WSL
echo 📝 Si no conecta, verifica que el servidor esté corriendo
echo.
pause