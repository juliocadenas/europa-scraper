@echo off
echo ================================================
echo   CONFIGURANDO FIREWALL DE WINDOWS
echo ================================================
echo.

echo 🔓 Paso 1: Abriendo puerto 8001 en el firewall...
netsh advfirewall firewall add rule name="Europa Scraper WSL" dir=in action=allow protocol=TCP localport=8001

echo.
echo ✅ Puerto 8001 abierto para conexiones entrantes

echo.
echo 🔍 Paso 2: Verificando regla creada...
netsh advfirewall firewall show rule name="Europa Scraper WSL"

echo.
echo 🌐 Paso 3: Verificando conexión de red...
echo IP del servidor: 172.23.48.1:8001
echo Intentando conectar...
curl -v http://172.23.48.1:8001/ping 2>nul || echo ⚠️  No se puede conectar desde Windows

echo.
echo ================================================
echo   INSTRUCCIONES FINALES:
echo ================================================
echo 1. ✅ Firewall configurado
echo 2. 🚀 Inicia el servidor en WSL
echo 3. 🖥️  Inicia el cliente en Windows  
echo 4. 📡  Usa: 172.23.48.1:8001
echo ================================================
echo.
pause