import logging
import asyncio
import random
import time
import secrets
from typing import List, Dict, Any, Tuple, Optional, Set
from playwright.async_api import Page
from playwright_stealth import stealth_async

from utils.captcha_solver import CaptchaSolver
from utils.scraper.stealth_browser_manager import StealthBrowserManager
from utils.scraper.text_processor import TextProcessor
from utils.scraper.url_utils import URLUtils

logger = logging.getLogger(__name__)

class HumanLikeSearchEngine:
    """
    Motor de búsqueda altamente sigiloso que simula comportamiento humano completo.
    Implementa todas las técnicas avanzadas anti-detección para Google.
    """
    
    def __init__(self, browser_manager: StealthBrowserManager, text_processor: TextProcessor, config_manager=None):
        self.browser_manager = browser_manager
        self.text_processor = text_processor
        self.url_utils = URLUtils()
        self._search_cache = {}
        self.search_session_id = secrets.token_hex(8)
        self.last_search_time = 0
        self.request_intervals = []
        self.captcha_solver = CaptchaSolver(config_manager) if config_manager else None
        
    async def search_google_stealth(self, query: str, site_domain: str = None, max_pages: int = 20) -> List[Dict[str, Any]]:
        """
        Búsqueda en Google con técnicas stealth avanzadas y comportamiento humano completo.
        """
        start_time = time.time()
        search_query = f'"{query}"' if site_domain else query
        
        logger.info(f"🔍 Búsqueda stealth en Google - Session: {self.search_session_id} - Query: '{search_query}'")
        
        # Implementar delays humanos entre búsquedas
        await self._human_throttle(start_time)
        
        all_results = []
        unique_urls = set()
        page = None
        current_session_searches = 0
        
        try:
            # Crear instancia de página con huella anti-detección
            page = await self.browser_manager.create_anonymous_page("google_search")
            
            # Navigation inicial con comportamientos humanos
            logger.info("🌐 Navegando a Google con comportamiento humano...")
            await self._human_like_navigation(page, "https://www.google.com/", is_initial=True)
            
            # Simular actividad humana inicial (mover mouse, scroll, etc.)
            await self._simulate_human_pre_search_behavior(page)
            
            # Busca y acepta términos de servicio de forma realista
            await self._handle_google_consent(page)
            
            # Escribir consulta con delays humanos
            logger.info("⌨️  Escribiendo consulta con comportamiento humano...")
            await self._human_like_typing(page, search_query)
            
            # Simular pausa humana antes de presionar Enter - realista
            await asyncio.sleep(random.uniform(0.8, 2.2))

            # Presionar Enter con delays variables
            await self._human_like_key_press(page, 'Enter')
            
            # Manejar resultados con comportamientos humanos - más tiempo
            await asyncio.sleep(random.uniform(4.0, 8.0))
            
            # Esperar resultados con múltiples condiciones posibles
            await self._wait_for_search_results_or_captcha(page, start_time)
            
            # Procesar múltiples páginas de resultados
            for page_num in range(min(max_pages, 5)):  # Limitar a 5 páginas para reducir probabilidad de bloqueo
                logger.info(f"📄 Procesando página {page_num + 1} de resultados...")
                
                current_session_searches += 1
                
                # Simular comportamiento de lectura humana en la página
                await self._simulate_human_reading_behavior(page)
                
                # Extraer resultados con delays humanos
                page_results = await self._extract_search_results_realistic(page)
                
                if not page_results:
                    logger.info("No se encontraron resultados en esta página. Terminando búsqueda.")
                    break
                
                # Procesar resultados
                for result in page_results:
                    if result['url'] not in unique_urls:
                        unique_urls.add(result['url'])
                        all_results.append(result)
                        logger.debug(f"Resultado encontrado: {result['title']}")
                
                # Navegar a siguiente página con comportamiento humano
                if page_num < 4:  # Ir a la siguiente página hasta la 5
                    should_continue = await self._navigate_to_next_page_human_like(page, page_num + 1)
                    if not should_continue:
                        break
                    
                    # Delay entre páginas
                    await self._human_throttle(start_time, reason=f"page_transition_{page_num}")
                
                # Registrar tiempo de esta búsqueda
                search_duration = time.time() - start_time
                self.request_intervals.append(search_duration)
                
                # Limitar el total de búsquedas para evitar bloqueo
                if current_session_searches >= 10:
                    logger.warning("Límite de búsquedas alcanzado para esta sesión. Terminando.")
                    break
            
            # Registro final de la búsqueda
            total_duration = time.time() - start_time
            logger.info(f"✅ Búsqueda completada - {len(all_results)} resultados encontrados en {total_duration:.2f}s")
            
            return all_results
            
        except Exception as e:
            logger.error(f"❌ Error durante búsqueda stealth: {str(e)}", exc_info=True)
            
            # Procesar si fue error normal o de CAPTCHA
            if isinstance(e, ManualCaptchaPendingError):
                logger.warning("CAPTCHA requerida. Pausando ejecución...")
                await self._handle_captcha_interactive(page)
            
            return all_results
        
        finally:
            if page:
                await self.browser_manager.release_page(page, "google_search")
                self.last_search_time = time.time()
    
    async def _human_throttle(self, start_time: float, reason: str = "search"):
        """Implementa throttling humano realista entre búsquedas."""
        current_time = time.time()
        time_since_last_search = current_time - self.last_search_time

        # Minimum gap between searches (30-90 seconds) - More cautious to avoid detection
        min_gap = random.uniform(30, 90)
        if time_since_last_search < min_gap:
            wait_time = min_gap - time_since_last_search
            logger.info(f"⏰ Delay humano: {wait_time:.1f}s - Razón: {reason}")
            await asyncio.sleep(wait_time)

        # Simulate "thinking time" (3-12 seconds) - More reasonable pause
        thinking_time = random.uniform(3, 12)
        logger.info(f"🧠 Tiempo de simul: {thinking_time:.1f}s")
        await asyncio.sleep(thinking_time)
    
    async def _human_like_navigation(self, page: Page, url: str, is_initial: bool = False):
        """Navega como un humano real."""
        if is_initial:
            # Navigation inicial con delays humanos - más largos
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(random.uniform(5, 10))
        else:
            # Navigation interna con delays - más largos
            await page.click("body", position={"x": random.randint(100, 500), "y": random.randint(100, 300)})
            await page.keyboard.press("End")
            await asyncio.sleep(random.uniform(1.5, 3.0))
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)

        # Simular actividad de carga humana - más tiempo
        await asyncio.sleep(random.uniform(2.0, 4.0))
    
    async def _simulate_human_pre_search_behavior(self, page: Page):
        """Simula comportamientos humanos antes de buscar."""
        # Mover mouse a posiciones aleatorias
        mouse_positions = [
            (100, 200), (500, 300), (200, 400), (800, 150), (600, 500)
        ]
        for x, y in random.sample(mouse_positions, random.randint(2, 4)):
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Scroll humano
        scroll_amounts = [200, 300, 150, 250]
        for amount in random.sample(scroll_amounts, random.randint(1, 3)):
            await page.mouse.wheel(0, amount)
            await asyncio.sleep(random.uniform(0.3, 0.8))
        
        # Clicks humanos en elementos no relacionados
        try:
            await page.click("body", position={"x": random.randint(50, 1000), "y": random.randint(50, 600)})
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.click("body", position={"x": random.randint(50, 1000), "y": random.randint(50, 600)})
        except:
            pass
    
    async def _handle_google_consent(self, page: Page):
        """Manejar consentimiento de cookies de forma realista."""
        try:
            # Diferentes selectores para consentimiento
            consent_selectors = [
                'button:has-text("Accept all")',
                'button:has-text("Accept all and continue")',
                'button:has-text("Accept all cookies")',
                'button:has-text("Aceptar todo")',
                'form[action*="consent"] input[type="submit"]'
            ]
            
            for selector in consent_selectors:
                try:
                    accept_button = page.locator(selector).first()
                    if await accept_button.is_visible(timeout=3000):
                        logger.info("🍪 Consentimiento de detectado. Aceptando...")
                        
                        # Hovers y delays realistas
                        await accept_button.hover()
                        await asyncio.sleep(random.uniform(0.2, 0.6))
                        await accept_button.click()
                        await asyncio.sleep(random.uniform(0.8, 2.0))
                        return
                except Exception as e:
                    continue
            
            logger.info("🍪 No se encontró consentimiento o ya fue aceptado.")
            
        except Exception as e:
            logger.debug(f"Error handling consent: {e}")
    
    async def _human_like_typing(self, page: Page, query: str):
        """Escribe como un humano real con delays y corrección."""
        search_box_locator = page.locator('textarea[name="q"], input[name="q"]').first()
        
        # Hacer hover y click realistas
        await search_box_locator.hover()
        await asyncio.sleep(random.uniform(0.2, 0.5))
        await search_box_locator.click()
        
        # Limpiar input existente
        await search_box_locator.fill("")
        
        # Escribir con delays humanos y corrección
        type_delays = []
        
        for char in query:
            # Simulate human typing delays (80-250ms per character, more realistic)
            base_delay = random.uniform(80, 250)

            # Add some human-like variants but less extreme
            if random.random() < 0.12:  # 12% chance of "fat finger"
                base_delay *= 1.8

            if random.random() < 0.06:  # 6% chance of backspace
                await search_box_locator.press("Backspace")
                await asyncio.sleep(base_delay * 0.6)

            type_delays.append(base_delay)
            await search_box_locator.type(char, delay=base_delay)
            await asyncio.sleep(random.uniform(0.01, 0.08))  # Shorter pause between chars
        
        total_typing_time = sum(type_delays) / 1000
        logger.info(f"⌨️  Tiempo de escritura: {total_typing_time:.2f}s")
    
    async def _human_like_key_press(self, page: Page, key: str):
        """Presiona teclas como humano real."""
        await page.keyboard.press(key)
        await asyncio.sleep(random.uniform(0.1, 0.3))
    
    async def _wait_for_search_results_or_captcha(self, page: Page, start_time: float):
        """Espera resultados o CAPTCHA con múltiples escenarios."""
        logger.info("⏳ Esperando resultados o CAPTCHA...")
        
        # Multiple waiting conditions with different timeouts
        tasks = []
    
        # Task 1: Wait for search results (30s timeout)
        task_results = asyncio.create_task(page.wait_for_selector('#search, #search .g, .g, .tF2Cxc', timeout=30000))
        tasks.append(("results", task_results))
        
        # Task 2: Wait for CAPTCHA (25s timeout - shorter to detect faster)
        task_captcha = asyncio.create_task(page.wait_for_selector('#captcha-container, iframe[src*="recaptcha"], .g-recaptcha, div[class*="captcha"]', timeout=25000))
        tasks.append(("captcha", task_captcha))
        
        # Task 3: Wait for "unusual traffic" message (20s timeout)
        task_traffic = asyncio.create_task(page.locator('text=/unusual traffic/i, text=/unusual activity/i').first().wait_for(timeout=20000))
        tasks.append(("traffic", task_traffic))
        
        # Task 4: Wait for normal page load (15s timeout)
        task_load = asyncio.create_task(page.wait_for_load_state('domcontentloaded', timeout=15000))
        tasks.append(("load", task_load))
        
        # Wait for first task to complete
        task_results = {name: task for name, task in tasks}
        done, pending = await asyncio.wait(
            task_results.values(),
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel and clean up pending tasks
        for task in pending:
            task.cancel()
        
        # Process the completed task
        for name, task in task_results.items():
            if task in done:
                task_exception = task.exception()
                if task_exception:
                    logger.debug(f"Task {name} failed: {task_exception}")
                else:
                    logger.info(f"✅ Detection: {name} completed first")
                    
                    if name == "captcha":
                        logger.warning("🚫 CAPTCHA detectado. Attempting to solve automatically...")
                        if self.captcha_solver:
                            await self._try_solve_captcha(page)
                            # Re-check if captcha is solved
                            await asyncio.sleep(2)
                            captcha_still_present = await page.locator('iframe[src*="recaptcha"], .g-recaptcha').count() > 0
                            if not captcha_still_present:
                                logger.info("✅ CAPTCHA resolved successfully")
                                return True
                            else:
                                logger.warning("❌ CAPTCHA solving failed. Raising exception for manual resolution.")
                                raise ManualCaptchaPendingError("Bot detection - CAPTCHA required and auto-solving failed")
                        else:
                            logger.warning("❌ No CAPTCHA solver configured. Raising exception for manual resolution.")
                            raise ManualCaptchaPendingError("Bot detection - CAPTCHA required")
                    elif name == "traffic":
                        logger.warning("🚨 Traffic detection warning received")
                        return False
                    elif name == "results":
                        logger.info("🔍 Search results loaded successfully")
                        return True
                    elif name == "load":
                        # Basic page loaded, continue waiting for results
                        logger.info("📄 Page loaded, waiting...")
                        try:
                            # Extended wait specifically for search results
                            await asyncio.wait_for(page.wait_for_selector('#search, .g', timeout=20000), timeout=20)
                            logger.info("✅ Search results found after page load")
                            return True
                        except asyncio.TimeoutError:
                            logger.warning("⏰ Timeout waiting for search results after page load")
                            return False
                break
        
        # If we get here, all tasks failed or timed out
        timeout_time = time.time() - start_time
        logger.warning(f"⏰ All waiting tasks timed out after {timeout_time:.1f}s")
        return False
    
    async def _simulate_human_reading_behavior(self, page: Page):
        """Simula comportamiento de lectura humana."""
        # Random scrolling and looking - más intenso
        for _ in range(random.randint(3, 6)):
            scroll_height = random.randint(300, 800)

            # Human-like scrolling
            await page.mouse.wheel(0, scroll_height)
            await asyncio.sleep(random.uniform(0.5, 1.5))

            # Small mouse movements while "reading"
            for _ in range(random.randint(5, 10)):
                x = random.randint(100, 900)
                y = random.randint(100, 500)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.2, 0.6))

            # Occasional pause to "read"
            await asyncio.sleep(random.uniform(2.0, 5.0))
    
    async def _extract_search_results_realistic(self, page: Page) -> List[Dict[str, Any]]:
        """Extrae resultados con técnicas anti-detección."""
        try:
            # Cache-busting selector variation
            selectors_to_try = [
                '#search > div > div > div:has(> a:not([href*="google.com"])):has(> a > h3)',
                '#search .g',
                '#search .tF2Cxc',
                'div[style*="display:block"] > a > h3',
                'a:has(> h3):not([href*="google.com"])'
            ]
            
            results = []
            used_selectors = set()
            
            for selector in selectors_to_try:
                if selector in used_selectors:
                    continue
                    
                used_selectors.add(selector)
                logger.debug(f"Trying selector: {selector}")
                
                try:
                    # Extract with realistic delays
                    page_results = await page.evaluate('''
                        () => {
                            const results = [];
                            const elements = document.querySelectorAll('%s');
                            
                            for (const el of elements) {
                                try {
                                    const link = el.querySelector('a');
                                    const title_elem = el.querySelector('h3');
                                    const desc_elem = el.querySelector('[role="heading"] + div, .VwiC3b, .IsZvec, .s3v8d');
                                    
                                    if (link && title_elem && title_elem.textContent && link.href) {
                                        // Filter out internal google links
                                        if (link.href.includes('google.com/search?q=')) continue;
                                        
                                        results.push({
                                            title: title_elem.textContent.trim(),
                                            url: link.href,
                                            description: desc_elem ? desc_elem.textContent.trim() : ''
                                        });
                                    }
                                } catch (e) {
                                    // Silently continue with other elements
                                }
                            }
                            return results;
                    }''' % selector.replace("'", '"'))
                    
                    if page_results:
                        results = page_results[:10]  # Limit results to extract
                        logger.info(f"✅ Found {len(results)} results with selector: {selector}")
                        break
                        
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            return results[:10]  # Maximum 10 results per page
            
        except Exception as e:
            logger.error(f"Error extracting search results: {e}")
            return []
    
    async def _navigate_to_next_page_human_like(self, page: Page, page_num: int) -> bool:
        """Navega a página siguiente con comportamiento humano."""
        logger.info(f"📄 Navegando a página {page_num}...")
        
        next_selectors = [
            'a#pnnext',
            'a[aria-label="Next page"]',
            'a[aria-label="Página siguiente"]',
            'a:has-text("Next")',
            'a:has-text("More results")'
        ]
        
        for selector in next_selectors:
            try:
                next_button = page.locator(selector).first()
                
                if await next_button.count() > 0 and await next_button.is_visible():
                    logger.info(f"Found next button with selector: {selector}")
                    
                    # Human-like interaction
                    await next_button.hover()
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    await next_button.click()
                    
                    # Wait for page to load
                    try:
                        await page.wait_for_selector('#search, #search .g', timeout=30000)
                        await asyncio.sleep(random.uniform(5.0, 10.0))
                        return True
                    except Exception:
                        # Try to recover by loading URL directly
                        try:
                            await page.goto(f"https://www.google.com/search?q={await page.url.split('=')[1].split('&')[0]}&start={page_num * 10}")
                            await page.wait_for_selector('#search', timeout=20000)
                            return True
                        except:
                            return False
                            
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        logger.warning("No se encontró botón de navegación siguiente. Terminando búsqueda.")
        return False
    
    async def _handle_captcha_interactive(self, page: Page) -> bool:
        """Maneja CAPTCHA de forma interactiva."""
        logger.info("🔓 CAPTCHA detectado. Esperando solución manual...")
        
        # Take screenshot
        try:
            await page.screenshot(path=f"debug_screenshots/captcha_manual_{secrets.token_hex(4)}.png")
            logger.info("📸 Captura de CAPTCHA guardada")
        except:
            pass
        
        # Wait for manual intervention
        logger.warning("Por favor resuelva el CAPTCHA manualmente y presione Enter para continuar...")
        
    async def _try_solve_captcha(self, page: Page) -> bool:
        """Attempts to solve the CAPTCHA automatically."""
        try:
            logger.info("🔓 Attempting to extract CAPTCHA details and solve...")

            # Extract site_key from reCAPTCHA iframe
            site_key = None
            try:
                iframe = page.locator('iframe[src*="recaptcha"]').first
                if await iframe.count() > 0:
                    src = await iframe.get_attribute('src')
                    if src and 'k=' in src:
                        site_key = src.split('k=')[1].split('&')[0]
                        logger.info(f"Extracted site_key: {site_key}")
            except Exception as e:
                logger.debug(f"Error extracting site_key: {e}")

            # Check if it's a standard pattern without iframe
            if not site_key:
                try:
                    div = page.locator('.g-recaptcha').first
                    if await div.count() > 0:
                        site_key = await div.get_attribute('data-sitekey')
                        logger.info(f"Extracted site_key from div: {site_key}")
                except Exception as e:
                    logger.debug(f"Error extracting site_key from div: {e}")

            # Get current page URL
            page_url = page.url

            if site_key and page_url:
                # Attempt to solve CAPTCHA
                solution = await self.captcha_solver.solve_captcha(page=page, page_url=page_url, site_key=site_key)
                if solution:
                    # Try to submit the CAPTCHA
                    logger.info("⚙️  Attempting to submit CAPTCHA solution...")

                    # For reCAPTCHA V2, sometimes it auto-submits, sometimes needs script
                    await asyncio.sleep(3)  # Wait for auto-submit

                    # Check if solved
                    await page.reload()  # Refresh page to see if unblocked
                    await page.wait_for_load_state('domcontentloaded', timeout=10000)

                    # Navigate back to search if needed
                    await page.go_back()
                    await page.wait_for_load_state('domcontentloaded', timeout=10000)

                    return True
                else:
                    logger.warning("CAPTCHA solving returned no solution")
            else:
                logger.warning(f"Could not extract CAPTCHA details: site_key={site_key}, page_url={page_url}")

        except Exception as e:
            logger.error(f"Error during CAPTCHA solving attempt: {e}")

        return False
        # Interactive waiting for manual resolution
        while True:
            try:
                # Check if CAPTCHA is still present
                captcha_present = await page.locator('iframe[src*="recaptcha"], .g-recaptcha').count() > 0
                if not captcha_present:
                    logger.info("✅ CAPTCHA resuelto exitosamente")
                    return True
                
                # Small delay before next check
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.debug(f"Error checking CAPTCHA status: {e}")
                await asyncio.sleep(2)


class ManualCaptchaPendingError(Exception):
    """Custom exception to indicate that a manual CAPTCHA is pending."""
    pass