@echo off
echo ================================================
echo   SISTEMA EUROPA SCRAPER - SOLUCIÓN FINAL
echo ================================================
echo.

echo 🚀 Paso 1: Iniciando servidor en WSL...
start "Servidor WSL" wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && ./iniciar_servidor_wsl_simple.sh"

echo.
echo ⏳ Esperando 15 segundos para que el servidor inicie completamente...
timeout /t 15 /nobreak

echo.
echo 🌐 Paso 2: Obteniendo IP de WSL...
echo Tu IP de WSL es:
wsl -d Ubuntu bash -c "ip route show | grep -i default | awk '{ print \$3}'"

echo.
echo 🖥️  Paso 3: Iniciando cliente en Windows...
echo Usa la IP de arriba en el cliente (formato: IP:8001)
echo.
cd client
start "Cliente Windows" python main.py

echo.
echo ✅ Sistema iniciado
echo 💡 COPIA LA IP QUE APARECE ARRIBA Y ÚSALA EN EL CLIENTE
echo 📝 Formato: IP:8001 (ej: 172.x.x.x:8001)
echo.
pause