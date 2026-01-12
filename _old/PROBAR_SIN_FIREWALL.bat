@echo off
echo ================================================
echo   PROBANDO CONEXIÓN SIN FIREWALL
echo ================================================
echo.

echo 🔓 DESACTIVANDO FIREWALL TEMPORALMENTE...
netsh advfirewall set allprofiles state off

echo.
echo 🚀 Iniciando servidor WSL...
start "Servidor WSL" wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && ./iniciar_servidor_wsl_simple.sh"

echo.
echo ⏳ Esperando 10 segundos...
timeout /t 10 /nobreak > nul

echo.
echo 🖥️ Iniciando cliente...
cd client
start "Cliente Windows" python main.py

echo.
echo ================================================
echo   ESPERANDO CONEXIÓN...
echo ================================================
echo 📡 Revisa si el cliente conecta exitosamente
echo 💡 Si conecta, el problema era el firewall
echo 📝 Si no conecta, puede ser antivirus o red
echo.
echo 🔓 REACTIVANDO FIREWALL...
netsh advfirewall set allprofiles state on

echo ✅ Firewall reactivado
echo ================================================
pause