@echo off
echo ============================================================
echo LIMPIANDO CACHE DE PYTHON Y EJECUTANDO CLIENTE
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/2] Borrando __pycache__ de todos los modulos...
if exist gui\__pycache__ (
    rmdir /s /q gui\__pycache__
    echo    - Borrado: gui\__pycache__
)
if exist client\__pycache__ (
    rmdir /s /q client\__pycache__
    echo    - Borrado: client\__pycache__
)
if exist utils\__pycache__ (
    rmdir /s /q utils\__pycache__
    echo    - Borrado: utils\__pycache__
)
if exist controllers\__pycache__ (
    rmdir /s /q controllers\__pycache__
    echo    - Borrado: controllers\__pycache__
)
if exist server\__pycache__ (
    rmdir /s /q server\__pycache__
    echo    - Borrado: server\__pycache__
)

echo.
echo [2/2] Ejecutando cliente...
echo ============================================================
echo.
echo DEBES VER EN LA CONSOLA: "BOTON 'VER CURSOS FALLIDOS' AGREGADO"
echo ============================================================
echo.

python client\main.py

pause
