@echo off
rem Script corregido para compilar el cliente de Europa Scraper
echo =====================================
echo      COMPILANDO APLICACIONES
echo =====================================
echo.

echo --- 1. Compilando el Cliente (Frontend) ---
python build_client_v3.py
if errorlevel 1 (
    echo.
    echo ERROR: La compilacion del cliente ha fallado.
    pause
    goto :eof
)

echo.
echo =====================================
echo  PROCESO DE COMPILACION COMPLETADO
echo =====================================
echo.
echo El ejecutable se encuentra en la carpeta 'dist'.
pause
