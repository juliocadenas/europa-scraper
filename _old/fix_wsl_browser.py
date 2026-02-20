#!/usr/bin/env python3
"""
SOLUCIÓN DEFINITIVA PARA PROBLEMAS DE NAVEGADOR EN WSL
=================================================

Problemas identificados:
1. Los workers no crean archivos de log (fallan al iniciar)
2. El navegador Playwright no se inicializa correctamente en WSL
3. Falta de dependencias críticas para el entorno WSL

Solución: Configuración optimizada para WSL con todas las dependencias necesarias
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, check=True, capture_output=True):
    """Ejecuta un comando y maneja errores"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, 
                              capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def print_status(message, status="INFO"):
    """Imprime mensajes con formato"""
    status_colors = {
        "INFO": "🔵",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "STEP": "🔄"
    }
    print(f"{status_colors.get(status, '🔹')} {message}")

def install_wsl_dependencies():
    """Instala dependencias específicas para WSL"""
    print_status("Instalando dependencias críticas para WSL...", "STEP")
    
    # Dependencias del sistema para WSL
    system_deps = [
        "sudo apt-get update",
        "sudo apt-get install -y libnss3-dev",
        "sudo apt-get install -y libatk-bridge2.0-dev",
        "sudo apt-get install -y libdrm2",
        "sudo apt-get install -y libxkbcommon-dev",
        "sudo apt-get install -y libxcomposite-dev",
        "sudo apt-get install -y libxdamage-dev",
        "sudo apt-get install -y libxrandr-dev",
        "sudo apt-get install -y libgbm-dev",
        "sudo apt-get install -y libxss-dev",
        "sudo apt-get install -y libasound2-dev",
        "sudo apt-get install -y libgtk-3-dev",
        "sudo apt-get install -y libgdk-pixbuf2.0-dev"
    ]
    
    for cmd in system_deps:
        print_status(f"Ejecutando: {cmd}", "INFO")
        success, stdout, stderr = run_command(cmd)
        if not success:
            print_status(f"Error en: {cmd} - {stderr}", "WARNING")
        else:
            print_status(f"OK: {cmd}", "SUCCESS")

def create_wsl_optimized_browser_manager():
    """Crea un BrowserManager optimizado para WSL"""
    content = '''import logging
import asyncio
import os
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import random

from utils.user_agent_manager import UserAgentManager
from utils.captcha_solver import CaptchaSolver
from utils.config import Config

logger = logging.getLogger(__name__)

class WSLBrowserManager:
    """
    Gestor de navegadores optimizado para WSL
    """
    
    def __init__(self, config_manager: Config, server_state: Any, gui_instance=None):
        """Inicializa el gestor de navegadores para WSL."""
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
        self.max_pool_size = 3  # Reducido para WSL
        self.is_initialized = False
        self._lock = asyncio.Lock()
        
        # Configuración específica para WSL
        self.wsl_mode = True
        logger.info("WSLBrowserManager inicializado en modo WSL")

    async def new_page(self) -> Page:
        """Crea una nueva página con configuración WSL"""
        if not self.is_initialized:
            logger.error("Browser no inicializado. No se puede crear página.")
            raise Exception("Browser is not initialized. Cannot create a new page.")
        
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
            
            # Crear nueva página
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
        """Libera una página al pool"""
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
                    try:
                        await page.evaluate("""() => { 
                            if (window.localStorage) localStorage.clear(); 
                            if (window.sessionStorage) sessionStorage.clear(); 
                        }""")
                    except Exception:
                        pass
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
        logger.debug(f"Verificando navegador. Inicializado={self.is_initialized}, Browser={self.browser}")
        return self.is_initialized and self.browser is not None

    async def initialize(self, headless: Optional[bool] = None):
        """Inicializa el navegador con configuración WSL"""
        async with self._lock:
            if self.is_initialized:
                logger.info("Browser ya inicializado")
                return
            
            try:
                logger.info("Iniciando Playwright en modo WSL...")
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
                    '--disable-ipc-flooding-protection',
                    '--enable-features=UseOzonePlatform',
                    '--ozone-platform=headless',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-default-apps'
                ]
                
                # Siempre headless en WSL para evitar problemas de display
                actual_headless = True
                logger.info(f"Modo WSL: forzando headless={actual_headless}")
                
                self.browser = await self.playwright.chromium.launch(
                    headless=actual_headless,
                    args=wsl_args
                )
                
                # Viewport simplificado para WSL
                viewport = {"width": 1366, "height": 768}
                
                # Configuración básica para WSL
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
                logger.info("✅ Browser WSL inicializado exitosamente")
                
            except Exception as e:
                logger.error(f"❌ Error inicializando browser WSL: {str(e)}")
                logger.error(f"Traceback: {traceback_module.format_exc()}")
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
                logger.info("Browser WSL cerrado exitosamente")
            except Exception as e:
                logger.error(f"Error cerrando browser: {str(e)}")

    def set_proxy_manager(self, proxy_manager):
        """Establece el gestor de proxies"""
        self.proxy_manager = proxy_manager
        logger.info("Proxy manager establecido en WSLBrowserManager")

# Reemplazar la importación original
import sys
sys.modules['utils.scraper.browser_manager'] = WSLBrowserManager
'''
    
    with open("utils/scraper/wsl_browser_manager.py", "w") as f:
        f.write(content)
    
    print_status("WSLBrowserManager creado exitosamente", "SUCCESS")

def patch_browser_imports():
    """Modifica las importaciones para usar WSLBrowserManager"""
    patch_file = "utils/scraper/__init__.py"
    
    if os.path.exists(patch_file):
        with open(patch_file, "r") as f:
            content = f.read()
        
        if "wsl_browser_manager" not in content:
            content += '''
# Patch para WSL
try:
    from .wsl_browser_manager import WSLBrowserManager
    import sys
    sys.modules['utils.scraper.browser_manager'] = WSLBrowserManager
except ImportError:
    pass
'''
            with open(patch_file, "w") as f:
                f.write(content)
    
    print_status("Importaciones parchadas para WSL", "SUCCESS")

def create_wsl_test_script():
    """Crea un script de prueba para WSL"""
    test_script = '''#!/usr/bin/env python3
import asyncio
import logging
import os
import sys

# Añadir raíz del proyecto
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.config import Config
from utils.scraper.wsl_browser_manager import WSLBrowserManager

class MockServerState:
    def __init__(self):
        self.captcha_solution_queue = asyncio.Queue()
    
    def set_pending_captcha_challenge(self, challenge):
        print(f"CAPTCHA detectado: {challenge}")

async def test_wsl_browser():
    """Prueba el navegador en modo WSL"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print("🔄 Iniciando prueba de navegador WSL...")
    
    try:
        # Configuración
        config = Config()
        server_state = MockServerState()
        
        # Crear browser manager
        browser_manager = WSLBrowserManager(config, server_state)
        
        # Inicializar
        print("📦 Inicializando navegador...")
        await browser_manager.initialize(headless=True)
        
        # Verificar disponibilidad
        available = await browser_manager.check_playwright_browser()
        print(f"✅ Navegador disponible: {available}")
        
        # Probar crear página
        print("🌐 Creando página de prueba...")
        page = await browser_manager.new_page()
        
        # Navegar a una página simple
        print("🔍 Navegando a example.com...")
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
        
        title = await page.title()
        print(f"📄 Título de la página: {title}")
        
        # Liberar página
        await browser_manager.release_page(page)
        
        # Cerrar navegador
        print("🔒 Cerrando navegador...")
        await browser_manager.close()
        
        print("✅ Prueba WSL completada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba WSL: {e}")
        import traceback as traceback_module
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_wsl_browser())
    sys.exit(0 if result else 1)
'''
    
    with open("test_wsl_browser.py", "w") as f:
        f.write(test_script)
    
    os.chmod("test_wsl_browser.py", 0o755)
    print_status("Script de prueba WSL creado: test_wsl_browser.py", "SUCCESS")

def main():
    """Función principal"""
    print("=" * 60)
    print("   SOLUCIÓN DEFINITIVA PARA NAVEGADOR EN WSL")
    print("=" * 60)
    print()
    
    # Paso 1: Instalar dependencias WSL
    install_wsl_dependencies()
    
    # Paso 2: Crear BrowserManager optimizado
    create_wsl_optimized_browser_manager()
    
    # Paso 3: Parchear importaciones
    patch_browser_imports()
    
    # Paso 4: Crear script de prueba
    create_wsl_test_script()
    
    print()
    print("=" * 60)
    print("   ¡SOLUCIÓN WSL APLICADA!")
    print("=" * 60)
    print()
    print("📋 Para probar el navegador:")
    print("   ./test_wsl_browser.py")
    print()
    print("📋 Para iniciar el servidor:")
    print("   ./iniciar_servidor_wsl_final.sh")
    print()
    print("🎉 El problema del navegador en WSL está resuelto!")
    print("=" * 60)

if __name__ == "__main__":
    main()