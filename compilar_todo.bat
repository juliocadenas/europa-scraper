@echo off
rem Script para compilar el cliente y el servidor de Europa Scraper

echo =====================================
echo      COMPILANDO APLICACIONES
echo =====================================
echo.

echo --- 1. Compilando el Cliente ---
python build_client.py
if errorlevel 1 (
    echo.
    echo ERROR: La compilacion del cliente ha fallado.
    pause
    goto :eof
)
echo Cliente compilado exitosamente.

echo.
echo --- 2. Compilando el Servidor ---
python build_server.py
if errorlevel 1 (
    echo.
    echo ERROR: La compilacion del servidor ha fallado.
    pause
    goto :eof
)
echo Servidor compilado exitosamente.

echo.
echo =====================================
echo  PROCESO DE COMPILACION COMPLETADO
echo =====================================
echo.
echo Los ejecutables se encuentran en la carpeta 'dist'.
pause
