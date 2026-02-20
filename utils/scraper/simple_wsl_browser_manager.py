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
