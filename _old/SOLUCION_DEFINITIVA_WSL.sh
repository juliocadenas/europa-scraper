#!/bin/bash
echo "=================================================="
echo "   SOLUCIÓN DEFINITIVA PARA SCRAPER EN WSL"
echo "=================================================="
echo

# Detectar si estamos en WSL
if grep -q Microsoft /proc/version; then
    echo "✅ Entorno WSL detectado"
    WSL_MODE=true
else
    echo "ℹ️  Entorno WSL no detectado"
    WSL_MODE=false
fi

echo "🔄 PASO 1: Aplicando diagnóstico y solución automática..."
python diagnosticar_y_solucionar_wsl.py

if [ $? -ne 0 ]; then
    echo "❌ Error en diagnóstico automático"
    echo "🔄 Intentando solución manual..."
    
    echo "📦 PASO 2: Instalando dependencias del sistema..."
    sudo apt-get update
    sudo apt-get install -y libnss3-dev libatk-bridge2.0-dev libdrm2 libxkbcommon-dev
    sudo apt-get install -y libxcomposite-dev libxdamage-dev libxrandr-dev libgbm-dev
    sudo apt-get install -y libxss-dev libasound2-dev libgtk-3-dev libgdk-pixbuf2.0-dev
    
    echo "🐍 PASO 3: Instalando dependencias Python..."
    ./venv_wsl/bin/pip install --upgrade pip
    ./venv_wsl/bin/pip install playwright==1.40.0 pyee==13.0.0 greenlet==3.2.4 typing-extensions
    
    echo "🌐 PASO 4: Instalando navegadores Playwright..."
    ./venv_wsl/bin/playwright install chromium
    ./venv_wsl/bin/playwright install-deps
fi

echo "🔧 PASO 5: Aplicando parches WSL..."
python fix_wsl_browser.py

echo "🌍 PASO 6: Configurando variables de entorno WSL..."
export DISPLAY=:99
export PLAYWRIGHT_BROWSERS_PATH=0
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
export PLAYWRIGHT_HEADLESS=true

echo "🧪 PASO 7: Probando navegador..."
python test_wsl_browser.py

if [ $? -eq 0 ]; then
    echo "✅ Prueba de navegador exitosa"
    echo
    echo "🎉 ¡SOLUCIÓN APLICADA CORRECTAMENTE!"
    echo "=================================================="
    echo
    echo "📋 Para iniciar el servidor con la solución:"
    echo "   ./iniciar_servidor_wsl_definitivo.sh"
    echo
    echo "🔍 Para verificar el estado:"
    echo "   tail -f logs/server.log"
    echo "   ls -la logs/worker_*.log"
    echo
    echo "📊 Los resultados se guardarán en:"
    echo "   results/"
    echo
    echo "✨ El problema del navegador en WSL está resuelto!"
    echo "=================================================="
else
    echo "❌ Error en prueba de navegador"
    echo "🔄 Intentando configuración alternativa..."
    
    # Configuración alternativa
    export DISPLAY=:0
    export PLAYWRIGHT_BROWSERS_PATH=1
    
    echo "🧪 Reintentando prueba con configuración alternativa..."
    python test_wsl_browser.py
    
    if [ $? -eq 0 ]; then
        echo "✅ Configuración alternativa funcionó"
        echo "🎉 ¡SOLUCIÓN APLICADA CON CONFIGURACIÓN ALTERNATIVA!"
    else
        echo "❌ Todas las configuraciones fallaron"
        echo "📋 Revisar manualmente:"
        echo "   1. Verificar instalación de dependencias del sistema"
        echo "   2. Verificar instalación de navegadores Playwright"
        echo "   3. Revisar logs en logs/ para más detalles"
        echo "   4. Considerar ejecutar en modo no-headless para debugging"
    fi
fi

echo
echo "=================================================="
echo "   FIN DE LA SOLUCIÓN DEFINITIVA WSL"
echo "=================================================="