@echo off
echo ========================================
echo   EUROPA SCRAPER - WSL SETUP
echo ========================================
echo.
echo Este script instalara las dependencias y luego iniciara el servidor en WSL/Linux
echo.

REM Paso 1: Instalar dependencias
echo [PASO 1/3] Instalando dependencias en WSL/Linux...
echo.
wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && chmod +x instalar_dependencias_wsl.sh && ./instalar_dependencias_wsl.sh"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] La instalacion de dependencias fallo.
    echo Por favor, revisa los errores arriba y corrige el problema manualmente.
    pause
    exit /b 1
)

echo.
echo [PASO 1/3] Dependencias instaladas correctamente!
echo.

REM Paso 2: Verificar instalación
echo [PASO 2/3] Verificando instalacion...
wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && python3 -c 'import fastapi; import uvicorn; print(\"✅ Dependencias verificadas\")'"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] La verificacion de dependencias fallo.
    echo Intentando instalacion manual...
    wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && python3 -m pip install fastapi uvicorn[standard]"
)

echo.
echo [PASO 2/3] Verificacion completada!
echo.

REM Paso 3: Iniciar servidor
echo [PASO 3/3] Iniciando servidor...
echo.
wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && chmod +x iniciar_servidor_linux.sh && ./iniciar_servidor_linux.sh"

echo.
echo ========================================
echo   SERVIDOR INICIADO EN WSL
echo ========================================
echo.
echo Para detener el servidor, cierra esta ventana o presiona Ctrl+C en la ventana de WSL.
echo.
pause