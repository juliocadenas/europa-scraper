import logging
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
