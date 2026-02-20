#!/bin/bash
echo "=================================================="
echo "   SOLUCIÓN FINAL CORREGIDA PARA WSL"
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

echo "🔧 PASO 1: Corrigiendo importación traceback..."
# Corregir el error de importación en fix_wsl_browser.py
sed -i 's/import traceback/import traceback as traceback_module/' fix_wsl_browser.py
sed -i 's/traceback.format_exc()/traceback_module.format_exc()/' fix_wsl_browser.py

echo "🔧 PASO 2: Desinstalando playwright para reinstalar completamente..."
./venv_wsl/bin/pip uninstall -y playwright playwright-stealth pyee greenlet

echo "🔧 PASO 3: Limpiando instalación anterior..."
rm -rf ./venv_wsl/lib/python3.12/site-packages/playwright*
rm -rf ./venv_wsl/lib/python3.12/site-packages/pyee*
rm -rf ./venv_wsl/lib/python3.12/site-packages/playwright_stealth*

echo "🔧 PASO 4: Instalando dependencias correctas..."
./venv_wsl/bin/pip install playwright==1.40.0
./venv_wsl/bin/pip install pyee==13.0.0
./venv_wsl/bin/pip install greenlet==3.2.4
./venv_wsl/bin/pip install playwright-stealth==2.0.0
./venv_wsl/bin/pip install typing-extensions

echo "🔧 PASO 5: Instalando navegadores Playwright..."
./venv_wsl/bin/playwright install chromium --force

echo "🔧 PASO 6: Verificando instalación de navegadores..."
if [ -d "./venv_wsl/lib/python3.12/site-packages/playwright/driver/package/.local-browsers" ]; then
    echo "✅ Navegadores Playwright encontrados"
    ls -la ./venv_wsl/lib/python3.12/site-packages/playwright/driver/package/.local-browsers/
else
    echo "❌ Navegadores no encontrados, intentando instalación manual..."
    mkdir -p ./venv_wsl/lib/python3.12/site-packages/playwright/driver/package/.local-browsers
    ./venv_wsl/bin/playwright install chromium --with-deps
fi

echo "🔧 PASO 7: Configurando variables de entorno WSL..."
export DISPLAY=:99
export PLAYWRIGHT_BROWSERS_PATH=0
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
export PLAYWRIGHT_HEADLESS=true

echo "🔧 PASO 8: Creando script de prueba corregido..."
cat > test_wsl_final.py << 'EOF'
#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
import traceback as traceback_module

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Añadir raíz del proyecto
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

async def test_wsl_browser_final():
    """Prueba final del navegador WSL corregido"""
    try:
        from playwright.async_api import async_playwright
        
        logger.info("Iniciando Playwright corregido...")
        playwright = await async_playwright().start()
        
        # Argumentos específicos para WSL
        args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--headless'
        ]
        
        logger.info("Lanzando Chromium con configuración WSL corregida...")
        browser = await playwright.chromium.launch(headless=True, args=args)
        
        logger.info("Creando contexto...")
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            viewport={'width': 1366, 'height': 768}
        )
        
        logger.info("Creando página...")
        page = await context.new_page()
        
        logger.info("Navegando a example.com...")
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
        
        title = await page.title()
        logger.info(f"Título obtenido: {title}")
        
        logger.info("Cerrando navegador...")
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()
        
        logger.info("✅ Prueba WSL final exitosa")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en prueba WSL final: {e}")
        logger.error(f"Traceback: {traceback_module.format_exc()}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_wsl_browser_final())
    sys.exit(0 if result else 1)
EOF

chmod +x test_wsl_final.py

echo "🔧 PASO 9: Ejecutando prueba final..."
python test_wsl_final.py

if [ $? -eq 0 ]; then
    echo
    echo "✅ ¡PRUEBA FINAL EXITOSA!"
    echo "🎉 El navegador WSL está funcionando correctamente"
    echo
    echo "📋 Para iniciar el servidor:"
    echo "   ./iniciar_servidor_wsl_definitivo.sh"
    echo
    echo "🔍 Para verificar el estado:"
    echo "   tail -f logs/server.log"
    echo
else
    echo
    echo "❌ La prueba final falló"
    echo "🔄 Intentando solución alternativa..."
    
    echo "🔧 PASO 10: Instalando Chromium del sistema..."
    sudo apt-get update
    sudo apt-get install -y chromium-browser
    
    echo "🔧 PASO 11: Probando con Chromium del sistema..."
    export CHROME_BIN=/usr/bin/chromium-browser
    
    python test_wsl_final.py
    
    if [ $? -eq 0 ]; then
        echo "✅ ¡SOLUCIÓN ALTERNATIVA EXITOSA!"
        echo "🎉 Usando Chromium del sistema"
    else
        echo "❌ Todas las soluciones fallaron"
        echo "📋 Revisar manualmente:"
        echo "   1. Verificar instalación: dpkg -l | grep chromium"
        echo "   2. Revisar logs del sistema: journalctl -xe"
        echo "   3. Verificar espacio: df -h"
        echo "   4. Verificar memoria: free -h"
    fi
fi

echo
echo "=================================================="
echo "   FIN DE LA SOLUCIÓN FINAL WSL"
echo "=================================================="