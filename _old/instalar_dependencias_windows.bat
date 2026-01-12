@echo off
echo ==================================================
echo    INSTALANDO DEPENDENCIAS PARA WINDOWS
echo ==================================================
echo.

echo Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado. Por favor instale Python desde python.org
    pause
    exit /b 1
)

echo ✅ Python encontrado
echo.

echo 📦 Instalando pandas para archivos Excel...
python -m pip install pandas openpyxl

echo 📦 Instalando dependencias del frontend...
python -m pip install requests

echo.
echo ==================================================
echo    ✅ DEPENDENCIAS INSTALADAS EN WINDOWS
echo ==================================================
echo.
echo 📋 Dependencias instaladas:
echo    - pandas: Para procesar archivos Excel
echo    - openpyxl: Para leer archivos .xlsx
echo    - requests: Para comunicación con servidor
echo    - tkinter: Para interfaz gráfica
echo.
echo 🚀 Ahora puedes ejecutar el frontend:
echo    cd client
echo    python main.py
echo ==================================================
pause