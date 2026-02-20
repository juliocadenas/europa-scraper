@echo off
REM Script para iniciar Cloudflared Tunnel en Windows
REM Este script crea un túnel seguro sin necesidad de abrir puertos en el firewall

echo ========================================
echo   Cloudflared Tunnel - Resultados Viewer
echo ========================================
echo.

REM Verificar que cloudflared.exe existe
if not exist "cloudflared.exe" (
    echo ERROR: No se encontro cloudflared.exe
    echo Por favor, descarga cloudflared desde: https://github.com/cloudflare/cloudflared/releases
    pause
    exit /b 1
)

REM Puerto del servidor (debe coincidir con el puerto del servidor principal)
set SERVER_PORT=8001
echo Puerto del servidor: %SERVER_PORT%
echo.

REM Verificar que el servidor esta corriendo
echo Verificando que el servidor esta corriendo...
timeout /t 2 /nobreak >nul

curl -s "http://localhost:%SERVER_PORT%/ping" >nul 2>&1
if errorlevel 1 (
    echo ERROR: El servidor no esta corriendo en el puerto %SERVER_PORT%
    echo Por favor, inicia el servidor primero con: python server/main.py
    pause
    exit /b 1
)

echo [OK] Servidor detectado y funcionando
echo.

REM Iniciar cloudflared
echo Iniciando tunel de Cloudflare...
echo Esto creara una URL publica segura para acceder a los resultados
echo.
echo ========================================
echo   INSTRUCCIONES DE USO
echo ========================================
echo.
echo 1. Espera a que cloudflared genere la URL publica
echo 2. Copia la URL que aparece (termina en .trycloudflare.com)
echo 3. Abre esa URL en tu navegador
echo 4. Agrega '/viewer' al final de la URL para ver el visor de resultados
echo.
echo Ejemplo: https://random-string.trycloudflare.com/viewer
echo.
echo Para detener el tunel, presiona Ctrl+C
echo.
echo ========================================
echo.

REM Iniciar cloudflared en modo quick tunnel (subdominio gratuito)
cloudflared.exe tunnel --url "http://localhost:%SERVER_PORT%"

pause
