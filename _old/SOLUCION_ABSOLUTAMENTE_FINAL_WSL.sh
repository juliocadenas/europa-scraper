#!/bin/bash
echo "=================================================="
echo "   SOLUCIÓN ABSOLUTAMENTE FINAL PARA WSL"
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

echo "🔧 PASO 1: CORRIGIENDO ERRORES ESTRUCTURALES..."
# Corregir rutas relativas al proyecto actual
PROJECT_ROOT=$(pwd)
echo "   Raíz del proyecto: $PROJECT_ROOT"

# Crear estructura de directorios necesaria
mkdir -p utils/scraper

echo "🔧 PASO 2: INSTALACIÓN MÍNIMA FUNCIONAL..."
# Instalar solo lo esencial para que funcione
python3 -m pip install --user playwright==1.40.0

echo "🔧 PASO 3: CREANDO BROWSER MANAGER SIMPLIFICADO..."
cat > utils/scraper/simple_wsl_browser_manager.py << 'EOF'
import logging
import asyncio
import os
from typing import Optional, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

class SimpleWSLBrowserManager:
    """
    BrowserManager extremadamente simplificado para WSL
    """
    
    def __init__(self, config_manager: Any, server_state: Any, gui_instance=None):
        self.config = config_manager
        self.gui = gui_instance
        self.browser = None
        self.context = None
        self.playwright = None
        self.page_pool = []
        self.max_pool_size = 2
        self.is_initialized = False
        self._lock = asyncio.Lock()
        
        logger = logging.getLogger(__name__)
        logger.info("SimpleWSLBrowserManager inicializado")

    async def new_page(self) -> Page:
        """Crea una nueva página"""
        if not self.is_initialized:
            raise Exception("Browser not initialized")
        
        async with self._lock:
            if self.page_pool:
                page = self.page_pool.pop()
                try:
                    await page.goto("about:blank")
                    return page
                except Exception as e:
                    logger.warning(f"Error reutilizando página: {e}")
                    try:
                        await page.close()
                    except:
                        pass
            
            try:
                page = await self.context.new_page()
                return page
            except Exception as e:
                logger.error(f"Error creando nueva página: {e}")
                raise

    async def release_page(self, page: Page):
        """Libera una página"""
        if not page:
            return
        
        async with self._lock:
            try:
                if len(self.page_pool) < self.max_pool_size:
                    await page.goto("about:blank")
                    self.page_pool.append(page)
                else:
                    await page.close()
            except Exception:
                try:
                    await page.close()
                except:
                    pass

    async def check_playwright_browser(self) -> bool:
        """Verifica si el navegador está disponible"""
        return self.is_initialized and self.browser is not None

    async def initialize(self, headless: Optional[bool] = None):
        """Inicializa el navegador con configuración mínima"""
        async with self._lock:
            if self.is_initialized:
                return
            
            try:
                logger.info("Iniciando Playwright simplificado...")
                self.playwright = await async_playwright().start()
                
                # Argumentos mínimos para WSL
                args = [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
                
                # Siempre headless en WSL
                actual_headless = True
                
                # Intentar con diferentes ejecutables
                chromium_paths = [
                    None,  # Usar el que Playwright encuentre
                    '/usr/bin/chromium-browser',  # Chromium del sistema
                    '/usr/bin/chromium',  # Chromium genérico
                ]
                
                browser_launched = False
                for i, chromium_path in enumerate(chromium_paths):
                    try:
                        logger.info(f"Intentando lanzar Chromium (método {i+1}): {chromium_path or 'Playwright default'}")
                        self.browser = await self.playwright.chromium.launch(
                            headless=actual_headless,
                            args=args,
                            executable_path=chromium_path
                        )
                        browser_launched = True
                        logger.info(f"✅ Chromium lanzado exitosamente con método {i+1}")
                        break
                    except Exception as e:
                        logger.warning(f"❌ Método {i+1} falló: {e}")
                        if i == len(chromium_paths) - 1:
                            logger.error("❌ Todos los métodos de lanzamiento fallaron")
                            raise Exception("No se pudo lanzar Chromium con ningún método")
                
                if not browser_launched:
                    raise Exception("No se pudo lanzar Chromium")
                
                # Configurar contexto básico
                self.context = await self.browser.new_context(
                    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                    viewport={'width': 1366, 'height': 768}
                )
                
                self.is_initialized = True
                logger.info("✅ SimpleWSLBrowserManager inicializado exitosamente")
                
            except Exception as e:
                logger.error(f"❌ Error inicializando SimpleWSLBrowserManager: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise

    async def close(self):
        """Cierra el navegador"""
        async with self._lock:
            try:
                for page in self.page_pool:
                    try:
                        await page.close()
                    except:
                        pass
                self.page_pool = []
                
                if self.browser:
                    await self.browser.close()
                    self.browser = None
                
                if self.playwright:
                    await self.playwright.stop()
                    self.playwright = None
                
                self.is_initialized = False
                logger.info("✅ SimpleWSLBrowserManager cerrado")
            except Exception as e:
                logger.error(f"Error cerrando navegador: {e}")

    def set_proxy_manager(self, proxy_manager):
        """Establece el gestor de proxies"""
        self.proxy_manager = proxy_manager
        logger.info("Proxy manager establecido en SimpleWSLBrowserManager")
EOF

echo "   ✅ BrowserManager simplificado creado"

echo "🔧 PASO 4: CREANDO CONFIGURACIÓN MÍNIMA..."
# Crear un config.json mínimo si no existe
if [ ! -f "client/config.json" ]; then
    mkdir -p client
    cat > client/config.json << 'EOF'
{
    "headless_mode": true,
    "wsl_mode": true,
    "server_id": "WSL_SERVER"
}
EOF
    echo "   ✅ Configuración mínima creada"
fi

echo "🔧 PASO 5: CREANDO SCRIPT DE PRUEBA SIMPLE..."
cat > test_simple_wsl.py << 'EOF'
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

async def test_simple_wsl():
    """Prueba simple del navegador WSL"""
    try:
        logger.info("🔄 Iniciando prueba simple WSL...")
        
        # Importar el browser manager simple
        from utils.scraper.simple_wsl_browser_manager import SimpleWSLBrowserManager
        
        # Mock server state
        class MockServerState:
            def __init__(self):
                self.captcha_solution_queue = asyncio.Queue()
            
            def set_pending_captcha_challenge(self, challenge):
                logger.info(f"CAPTCHA detectado: {challenge}")
        
        # Mock config
        class MockConfig:
            def get(self, key, default=None):
                return default
        
        # Crear browser manager
        server_state = MockServerState()
        config = MockConfig()
        browser_manager = SimpleWSLBrowserManager(config, server_state)
        
        # Inicializar
        logger.info("📦 Inicializando navegador simple...")
        await browser_manager.initialize(headless=True)
        
        # Verificar disponibilidad
        available = await browser_manager.check_playwright_browser()
        logger.info(f"✅ Navegador disponible: {available}")
        
        if available:
            # Probar crear página
            logger.info("🌐 Creando página de prueba...")
            page = await browser_manager.new_page()
            
            # Navegar a una página simple
            logger.info("🔍 Navegando a example.com...")
            await page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
            
            title = await page.title()
            logger.info(f"📄 Título obtenido: {title}")
            
            # Liberar página
            await browser_manager.release_page(page)
            
            logger.info("🎉 ¡PRUEBA SIMPLE EXITOSA!")
            return True
        else:
            logger.error("❌ Navegador no disponible")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en prueba simple WSL: {e}")
        logger.error(f"Traceback: {traceback_module.format_exc()}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_simple_wsl())
    sys.exit(0 if result else 1)
EOF

chmod +x test_simple_wsl.py
echo "   ✅ Script de prueba simple creado"

echo "🔧 PASO 6: APLICANDO PATCH SIMPLE..."
# Crear __init__.py mínimo para utils/scraper
cat > utils/scraper/__init__.py << 'EOF'
# Módulo utils.scraper
EOF

# Aplicar patch simple
cat >> utils/scraper/__init__.py << 'EOF'

# Patch simple para WSL
try:
    from .simple_wsl_browser_manager import SimpleWSLBrowserManager
    import sys
    sys.modules['utils.scraper.browser_manager'] = SimpleWSLBrowserManager
    print("✅ Patch simple WSL aplicado")
except ImportError as e:
    print(f"⚠️ Error aplicando patch simple: {e}")
EOF

echo "   ✅ Patch simple aplicado"

echo "🔧 PASO 7: CREANDO SCRIPT DE INICIO SIMPLE..."
cat > iniciar_servidor_wsl_simple.sh << 'EOF'
#!/bin/bash
echo "========================================="
echo "  INICIANDO SERVIDOR WSL SIMPLE"
echo "========================================="

# Detectar WSL
if grep -q Microsoft /proc/version; then
    echo "✅ WSL detectado"
    export DISPLAY=:99
else
    echo "ℹ️ WSL no detectado"
fi

# Activar entorno virtual si existe
if [ -d "venv_wsl" ]; then
    echo "Activando entorno virtual..."
    source venv_wsl/bin/activate
else
    echo "ℹ️ Creando entorno virtual..."
    python3 -m venv venv_wsl
    source venv_wsl/bin/activate
    
    # Instalar dependencias mínimas
    pip install playwright fastapi uvicorn requests pandas beautifulsoup4 lxml openpyxl python-multipart aiofiles python-dotenv
fi

echo "Iniciando servidor..."
cd server
python main.py
EOF

chmod +x iniciar_servidor_wsl_simple.sh
echo "   ✅ Script de inicio simple creado"

echo "🔧 PASO 8: EJECUTANDO PRUEBA SIMPLE..."
echo "   Ejecutando prueba simple WSL..."
python3 test_simple_wsl.py

if [ $? -eq 0 ]; then
    echo
    echo "🎉 ¡SOLUCIÓN SIMPLE EXITOSA!"
    echo "=================================================="
    echo
    echo "📋 Para iniciar el servidor:"
    echo "   ./iniciar_servidor_wsl_simple.sh"
    echo
    echo "🔍 Para verificar el estado:"
    echo "   tail -f logs/server.log"
    echo "   ls -la logs/worker_*.log"
    echo
    echo "📊 Los resultados se guardarán en:"
    echo "   results/"
    echo
    echo "✨ El problema del navegador en WSL está SIMPLE pero resuelto!"
    echo "=================================================="
else
    echo
    echo "❌ La prueba simple falló"
    echo "🔄 Intentando diagnóstico manual..."
    
    echo "🔍 DIAGNÓSTICO MANUAL:"
    echo "   Versión de Python: $(python3 --version)"
    echo "   Versión de Playwright: $(python3 -c 'import playwright; print(playwright.__version__)' 2>/dev/null || echo 'No instalado')"
    echo "   Chromium disponible: $(which chromium-browser 2>/dev/null || echo 'No encontrado')"
    echo "   Entorno WSL: $(grep -q Microsoft /proc/version && echo 'Sí' || echo 'No')"
    echo "   DISPLAY: $DISPLAY"
    echo
    echo "📋 Intentar solución manual:"
    echo "   1. Usar Chromium del sistema directamente"
    echo "   2. Ejecutar sin headless para debugging"
    echo "   3. Revisar logs del sistema: journalctl -xe"
fi

echo
echo "=================================================="
echo "   FIN DE LA SOLUCIÓN ABSOLUTAMENTE FINAL WSL"
echo "=================================================="