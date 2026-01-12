@echo off
echo ================================================
echo   DESACTIVANDO FIREWALL TEMPORALMENTE
echo ================================================
echo.

echo 🔓 Paso 1: Desactivando firewall de Windows...
netsh advfirewall set allprofiles state off

echo.
echo ✅ Firewall desactivado temporalmente

echo.
echo 🚀 Paso 2: Iniciando servidor WSL...
start "Servidor WSL" wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && ./iniciar_servidor_wsl_simple.sh"

echo.
echo ⏳ Esperando 10 segundos...
timeout /t 10 /nobreak > nul

echo.
echo 🖥️ Paso 3: Iniciando cliente...
cd client
start "Cliente Windows" python main.py

echo.
echo ================================================
echo   FIREWALL DESACTIVADO - PROBANDO CONEXIÓN
echo ================================================
echo 💡 Si conecta, el problema era el firewall
echo 📝 Si no conecta, reactiva el firewall:
echo    netsh advfirewall set allprofiles state on
echo ================================================
pause