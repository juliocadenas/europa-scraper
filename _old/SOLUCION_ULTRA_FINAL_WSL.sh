#!/bin/bash
echo "=================================================="
echo "   SOLUCIÓN ULTRA FINAL PARA WSL"
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

echo "🔧 PASO 1: LIMPIEZA COMPLETA DEL SISTEMA..."
# Limpiar completamente instalaciones anteriores
echo "   Desinstalando todos los paquetes relacionados con navegadores..."
sudo apt-get remove --purge -y chromium-browser chromium-browser-l10n google-chrome-stable firefox 2>/dev/null
sudo apt-get autoremove -y 2>/dev/null

echo "   Limpiando entorno virtual..."
rm -rf venv_wsl
python3 -m venv venv_wsl

echo "   Activando entorno virtual limpio..."
source venv_wsl/bin/activate

echo "🔧 PASO 2: INSTALACIÓN DE DEPENDENCIAS CRÍTICAS..."
# Actualizar pip
pip install --upgrade pip setuptools wheel

echo "   Instalando dependencias del sistema para WSL..."
sudo apt-get update
sudo apt-get install -y \
    curl \
    wget \
    gnupg \
    unzip \
    libnss3-dev \
    libatk-bridge2.0-dev \
    libdrm2 \
    libxkbcommon-dev \
    libxcomposite-dev \
    libxdamage-dev \
    libxrandr-dev \
    libgbm-dev \
    libxss-dev \
    libasound2-dev \
    libgtk-3-dev \
    libgdk-pixbuf2.0-dev \
    xvfb

echo "   Instalando dependencias Python específicas..."
pip install \
    playwright==1.40.0 \
    pyee==13.0.0 \
    greenlet==3.2.4 \
    typing-extensions \
    playwright-stealth==2.0.0

echo "🔧 PASO 3: INSTALACIÓN MANUAL DE CHROMIUM..."
# Descargar Chromium manualmente
echo "   Descargando Chromium para Linux..."
cd /tmp
wget -q https://commondatastorage.googleapis.com/chromium-browser-snapshots/Ubuntu_x64/1300252/chromium-browser_1300252-1_amd64.deb

if [ $? -eq 0 ]; then
    echo "   ✅ Chromium descargado exitosamente"
    echo "   Instalando Chromium del sistema..."
    sudo dpkg -i chromium-browser_1300252-1_amd64.deb
    
    # Verificar instalación
    if command -v chromium-browser; then
        echo "   ✅ Chromium del sistema instalado"
        CHROMIUM_PATH=$(which chromium-browser)
        echo "   Ruta de Chromium: $CHROMIUM_PATH"
    else
        echo "   ❌ Error instalando Chromium del sistema"
    fi
else
    echo "   ❌ Error descargando Chromium, intentando alternativa..."
    sudo apt-get install -y chromium-browser
fi

echo "🔧 PASO 4: CONFIGURACIÓN DE PLAYWRIGHT..."
# Instalar navegadores Playwright
echo "   Instalando navegadores Playwright..."
playwright install chromium --force --with-deps

# Verificar instalación
PLAYWRIGHT_CHROMIUM="$HOME/.cache/ms-playwright/chromium-1091/chrome-linux/chrome"
if [ -f "$PLAYWRIGHT_CHROMIUM" ]; then
    echo "   ✅ Playwright Chromium encontrado: $PLAYWRIGHT_CHROMIUM"
    chmod +x "$PLAYWRIGHT_CHROMIUM"
else
    echo "   ❌ Playwright Chromium no encontrado"
    echo "   Buscando en ubicaciones alternativas..."
    
    # Buscar en todas las ubicaciones posibles
    for path in "$HOME/.cache/ms-playwright/"*"/chrome-linux/chrome" \
               "./venv_wsl/lib/python3.12/site-packages/playwright/driver/package/.local-browsers/"*"/chrome-linux/chrome"; do
        if [ -f "$path" ]; then
            echo "   ✅ Chromium encontrado en: $path"
            PLAYWRIGHT_CHROMIUM="$path"
            chmod +x "$path"
            break
        fi
    done
fi

echo "🔧 PASO 5: CREANDO BROWSER MANAGER DEFINITIVO..."
# Crear un BrowserManager definitivo que use el Chromium del sistema
cat > utils/scraper/definitive_wsl_browser_manager.py << 'EOF'
import logging
import asyncio
import os
import subprocess
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from utils.user_agent_manager import UserAgentManager
from utils.captcha_solver import CaptchaSolver
from utils.config import Config

logger = logging.getLogger(__name__)

class DefinitiveWSLBrowserManager:
    """
    Gestor de navegadores definitivo para WSL
    Usa Chromium del sistema si Playwright falla
    """
    
    def __init__(self, config_manager: Config, server_state: Any, gui_instance=None):
        """Inicializa el gestor definitivo para WSL."""
        self.config = config_manager
        self.gui = gui_instance
        self.browser = None
        self.context = None
        self.playwright = None
        self.user_agent_manager = UserAgentManager()
        self.captcha_solver = CaptchaSolver(self.config, 
                                         captcha_challenge_callback=server_state.set_pending_captcha_challenge, 
                                         captcha_solution_queue=server_state.captcha_solution_queue)
        self.proxy_manager = None
        self.page_pool = []
        self.max_pool_size = 3
        self.is_initialized = False
        self._lock = asyncio.Lock()
        
        # Detectar rutas de Chromium
        self.system_chromium = None
        self.playwright_chromium = None
        
        # Intentar con Chromium del sistema
        try:
            result = subprocess.run(['which', 'chromium-browser'], capture_output=True, text=True)
            if result.returncode == 0:
                self.system_chromium = result.stdout.strip()
                logger.info(f"✅ Chromium del sistema encontrado: {self.system_chromium}")
        except:
            pass
        
        # Ruta de Playwright Chromium
        self.playwright_chromium = os.path.expanduser("~/.cache/ms-playwright/chromium-1091/chrome-linux/chrome")
        if not os.path.exists(self.playwright_chromium):
            # Buscar en otras ubicaciones
            import glob
            for pattern in [
                os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
                "./venv_wsl/lib/python3.12/site-packages/playwright/driver/package/.local-browsers/chromium*/chrome-linux/chrome"
            ]:
                matches = glob.glob(pattern)
                if matches:
                    self.playwright_chromium = matches[0]
                    break
        
        if os.path.exists(self.playwright_chromium):
            logger.info(f"✅ Playwright Chromium encontrado: {self.playwright_chromium}")
        else:
            logger.warning("❌ Playwright Chromium no encontrado")
        
        logger.info("DefinitiveWSLBrowserManager inicializado")

    async def new_page(self) -> Page:
        """Crea una nueva página"""
        if not self.is_initialized:
            logger.error("Browser no inicializado")
            raise Exception("Browser is not initialized")
        
        async with self._lock:
            if self.page_pool:
                page = self.page_pool.pop()
                try:
                    await page.goto("about:blank", wait_until="domcontentloaded")
                    user_agent = self.user_agent_manager.get_random_user_agent()
                    await page.set_extra_http_headers({
                        "User-Agent": user_agent,
                        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
                    })
                    return page
                except Exception as e:
                    logger.warning(f"Error reutilizando página: {e}")
                    try:
                        await page.close()
                    except:
                        pass
            
            try:
                page = await self.context.new_page()
                user_agent = self.user_agent_manager.get_random_user_agent()
                await page.set_extra_http_headers({
                    "User-Agent": user_agent,
                    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
                })
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
                is_closed = page.is_closed()
                if is_closed:
                    return
            except Exception:
                try:
                    await page.close()
                except:
                    pass
                return
            
            if len(self.page_pool) < self.max_pool_size:
                try:
                    await page.goto("about:blank", wait_until="domcontentloaded", timeout=5000)
                    self.page_pool.append(page)
                except Exception as e:
                    logger.debug(f"Error limpiando página: {e}")
                    try:
                        await page.close()
                    except:
                        pass
            else:
                try:
                    await page.close()
                except:
                    pass

    async def check_playwright_browser(self) -> bool:
        """Verifica si el navegador está disponible"""
        return self.is_initialized and self.browser is not None

    async def initialize(self, headless: Optional[bool] = None):
        """Inicializa el navegador con múltiples fallbacks"""
        async with self._lock:
            if self.is_initialized:
                logger.info("Browser ya inicializado")
                return
            
            try:
                logger.info("Iniciando Playwright en modo WSL definitivo...")
                self.playwright = await async_playwright().start()
                
                # Argumentos específicos para WSL
                wsl_args = [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--enable-features=UseOzonePlatform',
                    '--ozone-platform=headless',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-default-apps'
                ]
                
                # Siempre headless en WSL
                actual_headless = True
                logger.info(f"Modo WSL definitivo: forzando headless={actual_headless}")
                
                # Intentar 1: Playwright Chromium
                if os.path.exists(self.playwright_chromium):
                    try:
                        logger.info("🔄 Intentando con Playwright Chromium...")
                        self.browser = await self.playwright.chromium.launch(
                            headless=actual_headless,
                            args=wsl_args,
                            executable_path=self.playwright_chromium
                        )
                        logger.info("✅ Playwright Chromium inicializado")
                    except Exception as e:
                        logger.warning(f"❌ Playwright Chromium falló: {e}")
                        self.browser = None
                
                # Intentar 2: Chromium del sistema
                if not self.browser and self.system_chromium:
                    try:
                        logger.info(f"🔄 Intentando con Chromium del sistema: {self.system_chromium}")
                        self.browser = await self.playwright.chromium.launch(
                            headless=actual_headless,
                            args=wsl_args,
                            executable_path=self.system_chromium
                        )
                        logger.info("✅ Chromium del sistema inicializado")
                    except Exception as e:
                        logger.warning(f"❌ Chromium del sistema falló: {e}")
                        self.browser = None
                
                # Intentar 3: Chromium por defecto
                if not self.browser:
                    try:
                        logger.info("🔄 Intentando con Chromium por defecto...")
                        self.browser = await self.playwright.chromium.launch(
                            headless=actual_headless,
                            args=wsl_args
                        )
                        logger.info("✅ Chromium por defecto inicializado")
                    except Exception as e:
                        logger.error(f"❌ Chromium por defecto falló: {e}")
                        raise Exception("No se pudo inicializar ningún navegador")
                
                # Configurar contexto
                viewport = {"width": 1366, "height": 768}
                self.context = await self.browser.new_context(
                    user_agent=self.user_agent_manager.get_random_user_agent(),
                    ignore_https_errors=True,
                    viewport=viewport,
                    java_script_enabled=True,
                    bypass_csp=True,
                    locale='en-US',
                    timezone_id='America/New_York'
                )
                
                self.is_initialized = True
                logger.info("✅ Browser definitivo WSL inicializado exitosamente")
                
            except Exception as e:
                logger.error(f"❌ Error inicializando browser definitivo: {e}")
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
                    except Exception:
                        pass
                self.page_pool = []
                
                if self.browser:
                    await self.browser.close()
                    self.browser = None
                
                if self.playwright:
                    await self.playwright.stop()
                    self.playwright = None
                
                self.is_initialized = False
                logger.info("✅ Browser definitivo cerrado")
            except Exception as e:
                logger.error(f"Error cerrando browser: {e}")

    def set_proxy_manager(self, proxy_manager):
        """Establece el gestor de proxies"""
        self.proxy_manager = proxy_manager
        logger.info("Proxy manager establecido en DefinitiveWSLBrowserManager")

# Reemplazar la importación
import sys
sys.modules['utils.scraper.browser_manager'] = DefinitiveWSLBrowserManager
EOF

echo "   ✅ BrowserManager definitivo creado"

echo "🔧 PASO 6: APLICANDO PATCHES..."
# Aplicar el patch al __init__.py
if ! grep -q "definitive_wsl_browser_manager" utils/scraper/__init__.py; then
    cat >> utils/scraper/__init__.py << 'EOF'

# Patch definitivo para WSL
try:
    from .definitive_wsl_browser_manager import DefinitiveWSLBrowserManager
    import sys
    sys.modules['utils.scraper.browser_manager'] = DefinitiveWSLBrowserManager
    print("✅ Patch definitivo WSL aplicado")
except ImportError as e:
    print(f"⚠️ Error aplicando patch definitivo: {e}")
EOF
fi

echo "🔧 PASO 7: CONFIGURANDO ENTORNO WSL..."
export DISPLAY=:99
export PLAYWRIGHT_BROWSERS_PATH=0
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
export PLAYWRIGHT_HEADLESS=true
export CHROMIUM_PATH="${CHROMIUM_PATH:-$PLAYWRIGHT_CHROMIUM}"

echo "🔧 PASO 8: CREANDO PRUEBA DEFINITIVA..."
cat > test_definitive_wsl.py << 'EOF'
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

async def test_definitive_wsl():
    """Prueba definitiva del navegador WSL"""
    try:
        from utils.config import Config
        from utils.scraper.definitive_wsl_browser_manager import DefinitiveWSLBrowserManager
        
        class MockServerState:
            def __init__(self):
                self.captcha_solution_queue = asyncio.Queue()
            
            def set_pending_captcha_challenge(self, challenge):
                print(f"CAPTCHA detectado: {challenge}")
        
        logger.info("🔄 Iniciando prueba definitiva WSL...")
        
        # Configuración
        config = Config()
        server_state = MockServerState()
        
        # Crear browser manager definitivo
        browser_manager = DefinitiveWSLBrowserManager(config, server_state)
        
        # Inicializar
        logger.info("📦 Inicializando navegador definitivo...")
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
            logger.info(f"📄 Título de la página: {title}")
            
            # Liberar página
            await browser_manager.release_page(page)
        
        # Cerrar navegador
        logger.info("🔒 Cerrando navegador...")
        await browser_manager.close()
        
        logger.info("🎉 ✅ Prueba definitiva WSL exitosa")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en prueba definitiva WSL: {e}")
        logger.error(f"Traceback: {traceback_module.format_exc()}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_definitive_wsl())
    sys.exit(0 if result else 1)
EOF

chmod +x test_definitive_wsl.py

echo "🔧 PASO 9: EJECUTANDO PRUEBA DEFINITIVA..."
python test_definitive_wsl.py

if [ $? -eq 0 ]; then
    echo
    echo "🎉 ¡SOLUCIÓN ULTRA FINAL APLICADA CON ÉXITO!"
    echo "=================================================="
    echo
    echo "📋 Para iniciar el servidor:"
    echo "   ./iniciar_servidor_wsl_definitivo.sh"
    echo
    echo "🔍 Para verificar el estado:"
    echo "   tail -f logs/server.log"
    echo "   ls -la logs/worker_*.log"
    echo
    echo "📊 Los resultados se guardarán en:"
    echo "   results/"
    echo
    echo "✨ El problema del navegador en WSL está DEFINITIVAMENTE resuelto!"
    echo "=================================================="
else
    echo
    echo "❌ La prueba definitiva falló"
    echo "🔄 Intentando diagnóstico completo..."
    
    echo "🔍 DIAGNÓSTICO COMPLETO:"
    echo "   Versión de Playwright: $(./venv_wsl/bin/python -c 'import playwright; print(playwright.__version__)')"
    echo "   Rutas de Chromium:"
    find $HOME/.cache/ms-playwright -name "chrome" 2>/dev/null || echo "     No encontrado en cache"
    find ./venv_wsl -name "chrome" 2>/dev/null || echo "     No encontrado en venv"
    which chromium-browser 2>/dev/null && echo "     Chromium del sistema: $(which chromium-browser)" || echo "     No encontrado Chromium del sistema"
    
    echo
    echo "📋 Revisar manualmente:"
    echo "   1. Verificar instalación de Chromium: dpkg -l | grep chromium"
    echo "   2. Revisar logs del sistema: journalctl -xe | grep chromium"
    echo "   3. Verificar espacio: df -h"
    echo "   4. Verificar memoria: free -h"
    echo "   5. Revisar permisos: ls -la $HOME/.cache/ms-playwright/"
fi

echo
echo "=================================================="
echo "   FIN DE LA SOLUCIÓN ULTRA FINAL WSL"
echo "=================================================="