import logging
import asyncio
import random
import time
from typing import Optional, Dict, Any, List
from fake_useragent import UserAgent
from playwright.async_api import Browser, BrowserContext, Page, async_playwright, Request
from playwright_stealth import stealth_async
import os
import json

logger = logging.getLogger(__name__)

class StealthBrowserManager:
    """
    Gestor avanzado de navegador con técnicas de evasión anti-detección profesional.
    Implementa Playwright Stealth, huellas digitales aleatorias y simulación humana.
    """
    
    def __init__(self, config_manager, server_state=None):
        self.config = config_manager
        self.server_state = server_state
        self.browser = None
        self.contexts = {}  # Múltiples contextos con huellas diferentes
        self.playwright = None
        self.user_agent_manager = UserAgent()
        self.fingerprint_generator = FingerprintGenerator()
        self.browser_pool = BrowserPool()
        self.is_initialized = False
        self.browser_lock = asyncio.Lock()
        
        # Logging anti-detección
        self.anti_detection_log = []
        
    async def initialize(self, headless: Optional[bool] = None):
        """Inicializa el navegador con técnicas de evasión avanzadas."""
        async with self.browser_lock:
            if self.is_initialized:
                return
            
            try:
                logger.info("🚀 Iniciando navegador con técnicas de evasión avanzadas...")
                self.playwright = await async_playwright().start()
                
                # Configuración avanzada de navegación anti-detección
                actual_headless_mode = headless if headless is not None else self.config.get("headless_mode", True)
                logger.info(f"Modo headless: {actual_headless_mode}")
                
                # Argumentos de Chromium para evasión máxima
                chromium_args = [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-ipc-flooding-protection',
                    '--disable-renderer-backgrounding',
                    '--disable-ipc-flooding-info',
                    '--force-color-profile=srgb',
                    '--enable-automation',
                    '--password-store=basic',
                    '--use-mock-keychain',
                    '--disable-component-update',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-field-trial-config',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-client-side-phishing-detection'
                ]
                
                # Añadir aleatorización a los argumentos
                if random.choice([True, False]):
                    chromium_args.append('--disable-web-security')
                
                if random.choice([True, False]):
                    chromium_args.append('--aggressive-cache-discard')
                
                logger.info("💻 Iniciando Chromium con configuración anti-detección...")
                self.browser = await self.playwright.chromium.launch(
                    headless=actual_headless_mode,
                    args=chromium_args,
                    ignore_https_errors=True,
                    timeout=60000
                )
                
                # Aplicar técnicas de stealth avanzadas al contexto principal
                await self._apply_stealth_techniques()
                
                self.is_initialized = True
                logger.info("✅ Navegador inicializado con éxito - Sistema de evasión activo")
                
            except Exception as e:
                logger.error(f"❌ Error al inicializar navegador: {e}")
                raise
    
    async def _apply_stealth_techniques(self):
        """Aplica todas las técnicas de stealth avanzadas."""
        try:
            context_options = await self._generate_stealth_context_options()
            
            # Crear contexto principal
            self.contexts['main'] = await self.browser.new_context(**context_options)
            
            # Aplicar Playwright Stealth
            await stealth_async(self.contexts['main'])
            
            logger.info("🔒 Técnicas de stealth aplicadas con éxito")
            
        except Exception as e:
            logger.error(f"❌ Error al aplicar técnicas de stealth: {e}")
    
    async def _generate_stealth_context_options(self) -> Dict[str, Any]:
        """Genera opciones de contexto con huella digital aleatoria y chống chỉa."""
        # Generar huella digital única
        fingerprint = await self.fingerprint_generator.generate_fingerprint()
        
        # Configuración anti-huella
        context_options = {
            # User-Agent dinámico y realista
            "user_agent": self.user_agent_manager.random,
            
            # Configuración de viewport realista
            "viewport": {
                "width": random.randint(1366, 1920),
                "height": random.randint(768, 1080)
            },
            
            # Configuración geográfica aleatoria
            "geolocation": fingerprint['geolocation'],
            "timezone_id": fingerprint['timezone'],
            "locale": fingerprint['locale'],
            
            # Emulación de dispositivo
            "device_scale_factor": random.choice([1, 1.25, 1.5, 2]),
            
            # Cookies limpias pero con huella
            "http_credentials": {
                "username": secrets.token_hex(8),
                "password": secrets.token_hex(16)
            },
            
            # Configuración de red anti-detección
            "ignore_https_errors": random.choice([True, False]),
            
            # Headers anti-bot
            "extra_http_headers": await self._generate_realistic_headers(),
            
            # JavaScript emulación humana
            "java_script_enabled": True,
            
            # WebRTC anti-fingerprinting
            "bypass_csp": True,
            
            # Permisos aleatorios
            "permissions": self._generate_random_permissions(),
            
            # Emulación de red lenta (a veces)
            "offline": random.choice([True, False]) if random.random() < 0.1 else False,
        }
        
        # Variable de entorno para evitar detección
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = self.config.get('browsers_path', 'default')
        
        return context_options
    
    async def _generate_realistic_headers(self) -> Dict[str, str]:
        """Genera headers HTTP realistas anti-bot."""
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Language": self.fingerprint_generator.get_random_language(),
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
        
        # Headers opcionales realistas
        if random.random() < 0.8:
            headers["Sec-Ch-Ua"] = await self.fingerprint_generator.generate_sec_ch_ua()
            headers["Sec-Ch-Ua-Mobile"] = "?0"
            headers["Sec-Ch-Ua-Platform"] = await self.fingerprint_generator.generate_platform()
        
        # Headers anti-detección (más realistas)
        headers.update({
            "Referer": "https://www.google.com/",
            "Sec-Gpc": "1",
            "Sec-Fetch-User": "?1",
            "TE": "Trailers",
            "Accept-CH": "Sec-CH-UA-Platform, Sec-CH-UA-Mobile, Sec-CH-UA-Arch, Sec-CH-UA-Model",
            "Sec-Fetch-Dest": "empty",
            "Priority": "u=0, i"
        })
        
        # Marsenne Twister for random delays more human-like
        import time
        if random.random() < 0.3:
            time.sleep(random.uniform(0.1, 0.5))
        
        # Headers anti-detección (más realistas)
        headers.update({
            "Referer": "https://www.google.com/",
            "Sec-Gpc": "1",
            "Sec-Fetch-User": "?1",
            "TE": "Trailers",
            "Accept-CH": "Sec-CH-UA-Platform, Sec-CH-UA-Mobile, Sec-CH-UA-Arch, Sec-CH-UA-Model",
            "Sec-Fetch-Dest": "empty",
            "Priority": "u=0, i"
        })
        
        # Marsenne Twister for random delays more human-like
        import time
        if random.random() < 0.3:
            time.sleep(random.uniform(0.1, 0.5))
        
        return headers
    
    def _generate_random_permissions(self) -> List[str]:
        """Genera permisos aleatorios para parecer humano."""
        permissions = [
            "geolocation", "notifications", "camera", "microphone", 
            "clipboard-read", "clipboard-write", "display-capture"
        ]
        
        # Seleccionar 1-3 permisos aleatorios
        selected = random.sample(permissions, random.randint(1, 3))
        return selected
    
    async def create_anonymous_page(self, context_name: str = None, fingerprint_seed: str = None) -> Page:
        """
        Crea una página completamente anónima con huella digital única.
        """
        if not self.is_initialized:
            raise Exception("Browser not initialized")
        
        # Generar huella única
        unique_fingerprint = await self.fingerprint_generator.generate_fingerprint(seed=fingerprint_seed)
        
        # Crear nuevo contexto si es necesario
        if context_name not in self.contexts:
            context_options = await self._generate_stealth_context_options()
            context_options.update(unique_fingerprint)
            self.contexts[context_name] = await self.browser.new_context(**context_options)
            await stealth_async(self.contexts[context_name])
        
        context = self.contexts[context_name]
        
        # Crear página con emulación humana
        page = await context.new_page()
        
        # Configurar comportamiento humano en la página
        await self._configure_human_behavior(page, unique_fingerprint)
        
        # Registrar evento anti-detección
        self._log_anti_detection_event(f"CreatePage-{context_name}", unique_fingerprint['fingerprint_id'])
        
        return page
    
    async def _configure_human_behavior(self, page: Page, fingerprint: Dict[str, Any]):
        """Configura comportamiento humano en la página."""
        # Emular tiempos de carga humano
        await page.set_default_timeout(fingerprint['response_timeout'])
        await page.set_default_navigation_timeout(fingerprint['navigation_timeout'])
        
        # Configurar throttling aleatorio
        await page.route('**', lambda route: route.abort() if random.random() < 0.05 else route.continue_())
        
        # Inyectar scripts anti-bot
        await page.add_init_script("""
            // Evitar detección de bot
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined,
            });
            
            // Simular comportamiento humano en queries
            window.navigator.permissions.query = (parameters) => {
              return Promise.resolve({ state: (parameters.name == 'notifications') ? 'prompt' : 'granted' });
            };
        """)
        
        # Configurar emulación de red
        await page.route('**', self._human_like_network_request)
    
    async def _human_like_network_request(self, route):
        """Simula solicitudes de red humanas."""
        request = route.request
        
        # Simular tráfico humano con delays
        if random.random() < 0.1:  # 10% de probabilidad de delay
            await asyncio.sleep(random.uniform(0.1, 2.0))
        
        # Continuar la solicitud normalmente
        await route.continue_()
    
    async def pool_manager(self) -> Page:
        """Gestiona un pool de páginas con rotación de huellas."""
        return await self.browser_pool.get_available_page(self)
    
    async def release_page(self, page: Page, context_name: str = 'main'):
        """Libera una página al pool."""
        if await page.is_closed():
            return
        
        # Clear estado de la página
        try:
            await page.goto("about:blank")
            await page.evaluate("""
                localStorage.clear();
                sessionStorage.clear();
                if (window.indexedDB) {
                    indexedDB.databases().then(dbs => {
                        dbs.forEach(db => indexedDB.deleteDatabase(db.name));
                    });
                }
            """)
            
            # Limpiar cookies del contexto si es necesario
            if random.random() < 0.3:  # 30% de limpiar cookies
                context_cookies = await self.contexts[context_name].cookies()
                if context_cookies:
                    await self.contexts[context_name].clear_cookies()
        except Exception as e:
            logger.debug(f"Cleaning page state: {e}")
        
        # Añadir al pool
        await self.browser_pool.return_to_pool(page, context_name)
    
    async def close(self):
        """Cierra el navegador y limpia todos los recursos."""
        async with self.browser_lock:
            if not self.is_initialized:
                return
            
            # Cerrar todos los contextos
            for context_name, context in self.contexts.items():
                try:
                    await context.close()
                    logger.info(f"Context '{context_name}' cerrado")
                except Exception as e:
                    logger.debug(f"Error cerrando contexto {context_name}: {e}")
            
            # Cerrar browser
            if self.browser:
                await self.browser.close()
            
            # Cerrar playwright
            if self.playwright:
                await self.playwright.stop()
            
            self.contexts.clear()
            self.is_initialized = False
            logger.info("🔒 Navegador cerrado - Sistema de evasión desactivado")
    
    def _log_anti_detection_event(self, event_type: str, details: Dict[str, Any]):
        """Registra eventos anti-detección para análisis."""
        event = {
            "timestamp": time.time(),
            "event_type": event_type,
            "details": details,
            "context": {
                "contexts_count": len(self.contexts),
                "pool_size": len(self.browser_pool.pages)
            }
        }
        self.anti_detection_log.append(event)
        
        # Limitar log size
        if len(self.anti_detection_log) > 1000:
            self.anti_detection_log = self.anti_detection_log[-500:]
    
    def get_anti_detection_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema anti-detección."""
        return {
            "active_contexts": len(self.contexts),
            "pool_size": len(self.browser_pool.pages) if hasattr(self, 'browser_pool') else 0,
            "total_events": len(self.anti_detection_log),
            "browser_status": "active" if self.is_initialized else "inactive"
        }
    
    async def test_stealth_mode(self) -> Dict[str, Any]:
        """Prueba el modo stealth y reporta resultados."""
        test_results = {
            "user_agent_test": False,
            "fingerprint_test": False,
            "stealth_test": False,
            "headers_test": False,
            "human_behavior_test": False
        }
        
        try:
            page = await self.create_anonymous_page("test_stealth")
            
            # Test User-Agent
            ua = await page.evaluate("navigator.userAgent")
            test_results["user_agent_test"] = "bot" not in ua.lower() and "headless" not in ua.lower()
            
            # Test fingerprinting
            canvas_fingerprint = await page.evaluate("window.canvas ? new OffscreenCanvas(1, 1).getContext('2d').getImageData(0,0,1,1).data : null")
            webgl_fingerprint = await page.evaluate("new WebGLRenderingContext ? new OffscreenCanvas(1,1).getContext('webgl') : null")
            test_results["fingerprint_test"] = canvas_fingerprint is not None or webgl_fingerprint is not None
            
            # Test stealth
            webdriver_prop = await page.evaluate("Object.getOwnPropertyDescriptor(navigator, 'webdriver')")
            test_results["stealth_test"] = webdriver_prop is None
            
            # Test headers
            headers = await page.request.get("https://httpbin.org/headers").json()
            test_results["headers_test"] = "User-Agent" in headers
            
            # Test humano con vigilancia de red
            network_requests = []
            await page.route('**', lambda route: network_requests.append(route.request.url))
            await page.goto("https://www.google.com")
            test_results["human_behavior_test"] = len(network_requests) > 3
            
            await page.close()
            
        except Exception as e:
            logger.error(f"Error en test de stealth: {e}")
        
        return test_results


class FingerprintGenerator:
    """Generador de huellas digitales aleatorias y realistas."""
    
    def __init__(self):
        self.languages = ["es-US", "en-US", "en-GB", "fr-FR", "de-DE", "it-IT", "pt-BR"]
        self.timezones = ["America/New_York", "Europe/London", "Europe/Paris", "Asia/Tokyo", "Australia/Sydney"]
        self.locales = ["es", "en", "fr", "de", "it", "pt"]
        self.platforms = ["Windows", "macOS", "Linux", "Android", "iOS"]
        
    async def generate_fingerprint(self, seed: str = None) -> Dict[str, Any]:
        """Genera una huella digital única y realista."""
        if seed:
            random.seed(seed)
        
        fingerprint = {
            "fingerprint_id": secrets.token_hex(8),
            "geolocation": {
                "latitude": random.uniform(-90, 90),
                "longitude": random.uniform(-180, 180),
                "accuracy": random.randint(10, 100)
            },
            "timezone": random.choice(self.timezones),
            "locale": random.choice(self.locales),
            "language": random.choice(self.languages),
            
            # Configuración de timeouts humanos
            "response_timeout": random.randint(30000, 60000),
            "navigation_timeout": random.randint(60000, 120000),
            
            # Emulación de hardware
            "cpu_concurrency": random.choice([2, 4, 8]),
            "memory_mb": random.choice([4096, 8192, 16384]),
            
            # Pixel ratio realista
            "device_pixel_ratio": random.choice([1, 1.25, 1.5, 2]),
            
            # Carga humana simulada
            "human_load_factor": random.uniform(0.1, 0.8)
        }
        
        return fingerprint
    
    def get_random_language(self) -> str:
        """Obtiene lenguaje aleatorio para headers."""
        return ", ".join(random.sample(self.languages, random.randint(1, 3)))
    
    async def generate_sec_ch_ua(self) -> str:
        """Genera header Sec-Ch-UA realista."""
        browsers = [
            '"Not A;Brand";v="99", "Chromium";v="114"',
            '"Not A;Brand";v="99", "Google Chrome";v="114"',
            '"Not_A Brand";v="99", "Microsoft Edge";v="114"'
        ]
        return ", ".join(random.sample(browsers, 2))
    
    async def generate_platform(self) -> str:
        """Genera plataforma realista para headers."""
        return random.choice(self.platforms)


class BrowserPool:
    """Pool de navegadores para rotación y reutilización optimizada."""
    
    def __init__(self, max_size: int = 10):
        self.pages = []
        self.max_size = max_size
        self.used_pages = set()
        self.page_lock = asyncio.Lock()
    
    async def get_available_page(self, browser_manager) -> Page:
        """Obtiene una página disponible del pool."""
        async with self.page_lock:
            # Buscar página reutilizable
            for page in self.pages:
                if page not in self.used_pages and not page.is_closed():
                    self.used_pages.add(page)
                    return page
            
            # Si no hay disponibles, crear nueva
            if len(self.pages) < self.max_size:
                context_name = f"anon_{len(self.pages)}"
                page = await browser_manager.create_anonymous_page(context_name)
                self.pages.append(page)
                self.used_pages.add(page)
                return page
            
            # Si el pool está lleno, esperar y liberar
            await self._cleanup_closed_pages()
            await asyncio.sleep(0.5)
            return await self.get_available_page(browser_manager)
    
    async def return_to_pool(self, page: Page, context_name: str):
        """Libera una página al pool."""
        async with self.page_lock:
            self.used_pages.discard(page)
            
            # Limpiar estado de la página
            try:
                await page.goto("about:blank")
            except:
                pass
    
    async def _cleanup_closed_pages(self):
        """Limpia páginas cerradas del pool."""
        self.pages = [p for p in self.pages if not p.is_closed()]