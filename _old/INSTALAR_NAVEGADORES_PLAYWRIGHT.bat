@echo off
echo ============================================================
echo INSTALANDO NAVEGADORES DE PLAYWRIGHT
echo ============================================================
echo.

REM Activar entorno virtual
call venv_windows\Scripts\activate

echo.
echo 🚀 Instalando navegadores de Playwright...
echo Esto puede tardar varios minutos...
echo.

REM Instalar navegadores
playwright install

echo.
echo ✅ Instalación completada
echo.

REM Verificar instalación
echo 🔍 Verificando instalación...
if exist "%USERPROFILE%\AppData\Local\ms-playwright" (
    echo ✅ Navegadores instalados correctamente
    dir "%USERPROFILE%\AppData\Local\ms-playwright"
) else (
    echo ❌ No se encontraron navegadores instalados
)

echo.
echo ============================================================
echo Los navegadores de Playwright han sido instalados
echo Ahora el sistema de scraping debería funcionar correctamente
echo ============================================================
echo.
pause