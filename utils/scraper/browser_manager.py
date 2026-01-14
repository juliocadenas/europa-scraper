import logging
import os
import asyncio
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import random
import sys

from utils.user_agent_manager import UserAgentManager
from utils.captcha_solver import CaptchaSolver
from utils.config import Config
import random

logger = logging.getLogger(__name__)

class BrowserManager:
  """
  Gestiona una instancia global y única del navegador para el scraping.
  """
  
  def __init__(self, config_manager: Config, server_state: Any, gui_instance=None):
      """Inicializa el gestor de navegadores."""
      self.config = config_manager
      self.gui = gui_instance
      self.browser = None
      self.context = None
      self.playwright = None
      self.user_agent_manager = UserAgentManager()
      self.captcha_solver = CaptchaSolver(self.config, captcha_challenge_callback=server_state.set_pending_captcha_challenge, captcha_solution_queue=server_state.captcha_solution_queue)
      self.proxy_manager = None
      self.page_pool = []
      self.max_pool_size = 5
      self.is_initialized = False
      self._lock = asyncio.Lock()
      logger.debug(f"BrowserManager instance created: {id(self)}")

  async def navigate_and_handle_captcha(self, page: Page, url: str) -> bool:
      """
      Navega a una URL y maneja cualquier CAPTCHA que aparezca.

      Args:
          page: La instancia de la página de Playwright a usar.
          url: La URL a la que navegar.

      Returns:
          True si la navegación y el manejo del CAPTCHA fueron exitosos, False en caso contrario.
      """
      try:
          await page.goto(url, wait_until="domcontentloaded", timeout=60000)
          await self.handle_captcha(page)
          return True
      except Exception as e:
          logger.error(f"Error durante la navegación a {url}: {e}")
          return False

  async def handle_captcha(self, page: Page) -> bool:
      """
      Detecta y resuelve un CAPTCHA en la página actual.

      Args:
          page: La página de Playwright a analizar.

      Returns:
          True si un CAPTCHA fue detectado y resuelto, False en caso contrario.
      """
      if not self.config.get("captcha_solving_enabled"):
          return False

      logger.info("Buscando CAPTCHA en la página...")
      html_content = await page.content()
      logger.debug(f"Contenido HTML de la página al buscar CAPTCHA:\n{html_content}")

      try:
          # Selectores comunes para imágenes y campos de entrada de CAPTCHA
          captcha_image_selector = "img[src*='captcha'], img[id*='captcha']"
          captcha_input_selector = "input[name*='captcha'], input[id*='captcha']"

          # Detectar reCAPTCHA directamente en la página principal
          site_key_element = await page.query_selector('div.g-recaptcha')
          logger.debug(f"Resultado de page.query_selector('div.g-recaptcha'): {site_key_element}")
          site_key = None
          logger.debug(f"Intentando encontrar div.g-recaptcha. Elemento: {site_key_element}")
          if site_key_element:
              site_key = await site_key_element.get_attribute('data-sitekey')
              logger.debug(f"site_key encontrado directamente: {site_key}")
              if site_key:
                  logger.info(f"Sitekey de reCAPTCHA encontrado directamente: {site_key}")
                  
                  solution = None
                  if self.config.get("captcha_solving_enabled", False): # Si la resolución automática está habilitada
                      logger.debug(f"Intentando resolución automática de reCAPTCHA. page_url: {page.url}, site_key: {site_key}")
                      solution = await self.captcha_solver.solve_captcha(page=page, page_url=page.url, site_key=site_key)
                  
                  if not solution: # Si la resolución automática falló o no estaba habilitada
                      logger.warning("Resolución automática de reCAPTCHA fallida o deshabilitada. Intentando resolución manual.")
                      html_content = await page.content() # Obtener el contenido actual de la página para el desafío manual
                      solution = await self.captcha_solver._solve_manually(page_content=html_content)
                      
                      if not solution:
                          logger.error("No se pudo resolver el reCAPTCHA manualmente. Manteniendo la página abierta para intervención.")
                          return False # Indicar que no se resolvió automáticamente.

                  if solution:
                      logger.info("reCAPTCHA resuelto. Inyectando respuesta.")
                      # Inyectar la respuesta en el campo oculto de reCAPTCHA
                      await page.evaluate(f"""(token) {{
                          const element = document.getElementById('g-recaptcha-response');
                          if (element) {{
                              element.value = token; // Use .value for textarea
                          }} else {{
                              console.error("Elemento g-recaptcha-response no encontrado.");
                          }}
                          // Trigger the submitCallback if it exists
                          if (typeof submitCallback === 'function') {{
                              submitCallback(token);
                          }} else if (window.grecaptcha && window.grecaptcha.execute) {{
                              // Fallback if submitCallback is not directly available in this context
                              const form = document.getElementById('captcha-form');
                              if (form) {{
                                  form.submit();
                              }}
                          }}
                      }}""", solution) 
                      
                      logger.info("Respuesta de reCAPTCHA inyectada y formulario enviado (si es aplicable).")
                      await asyncio.sleep(random.uniform(3, 7)) # Esperar después de resolver reCAPTCHA
                      return True
                  else:
                      logger.error("No se pudo resolver el reCAPTCHA.")
                      return False
          
          # Si no se encontró directamente, intentar en iframe (lógica original)
          recaptcha_iframe = page.locator('iframe[src*="recaptcha"]')
          logger.debug(f"Intentando encontrar iframe de recaptcha. Count: {await recaptcha_iframe.count()}")
          if await recaptcha_iframe.count() > 0:
              logger.info("reCAPTCHA iframe detectado. Entrando en el bloque de manejo de reCAPTCHA.")
              try:
                  # Intentar encontrar el sitekey
                  site_key_element = await page.query_selector('div.g-recaptcha')
                  site_key = None
                  logger.info(f"site_key_element: {site_key_element}")
                  if site_key_element:
                      site_key = await site_key_element.get_attribute('data-sitekey')
                      logger.info(f"site_key: {site_key}")
                  
                  if site_key:
                      logger.info(f"Sitekey de reCAPTCHA encontrado: {site_key}")
                      
                      solution = None
                      if self.config.get("captcha_solving_enabled", False): # Si la resolución automática está habilitada
                          logger.debug(f"Intentando resolución automática de reCAPTCHA. page_url: {page.url}, site_key: {site_key}")
                          solution = await self.captcha_solver.solve_captcha(page=page, page_url=page.url, site_key=site_key)
                      
                      if not solution: # Si la resolución automática falló o no estaba habilitada
                          logger.warning("Resolución automática de reCAPTCHA fallida o deshabilitada. Intentando resolución manual.")
                          html_content = await page.content() # Obtener el contenido actual de la página para el desafío manual
                          
                          # Asegurarse de que el navegador no esté en modo headless para la interacción manual
                          # Esto ya se configura al inicio, pero es un recordatorio de la necesidad.
                          
                          logger.info("Esperando solución manual del reCAPTCHA. Por favor, resuelva el CAPTCHA en la ventana del navegador.")
                          solution = await self.captcha_solver._solve_manually(page_content=html_content)
                          
                          if not solution:
                              logger.error("No se pudo resolver el reCAPTCHA manualmente o el usuario no proporcionó una solución a tiempo.")
                              return False # Indicar que no se resolvió.

                      if solution:
                          logger.info("reCAPTCHA resuelto. Inyectando respuesta.")
                          # Inyectar la respuesta en el campo oculto de reCAPTCHA
                          await page.evaluate(f"""(token) {{
                              const element = document.getElementById('g-recaptcha-response');
                              if (element) {{
                                  element.value = token; // Use .value for textarea
                              }} else {{
                                  console.error("Elemento g-recaptcha-response no encontrado.");
                              }}
                              // Trigger the submitCallback if it exists
                              if (typeof submitCallback === 'function') {{
                                  submitCallback(token);
                              }}
                          }}""", solution) 
                          
                          logger.info("Respuesta de reCAPTCHA inyectada y formulario enviado (si es aplicable).")
                          return True
                      else:
                          logger.error("No se pudo resolver el reCAPTCHA.")
                          return False
                  else:
                      logger.error("No se pudo encontrar el sitekey de reCAPTCHA.")
                      return False
              except Exception as e:
                  logger.error(f"Error al manejar reCAPTCHA: {e}")
                  return False

          # Selectores comunes para imágenes y campos de entrada de CAPTCHA (si no es reCAPTCHA)
          captcha_image_selector = "img[src*='captcha'], img[id*='captcha']"
          captcha_input_selector = "input[name*='captcha'], input[id*='captcha']"

          image_element = await page.query_selector(captcha_image_selector)
          input_element = await page.query_selector(captcha_input_selector)

          if image_element and input_element:
              logger.info("CAPTCHA de imagen detectado.")
              image_url = await image_element.get_attribute('src')

              # Asegurarse de que la URL de la imagen sea absoluta
              if image_url.startswith('/'):
                  page_url = page.url
                  base_url = page_url.split('/')[0] + '//' + page_url.split('/')[2]
                  image_url = base_url + image_url

              solution = None
              if self.config.get("captcha_solving_enabled", False): # Si la resolución automática está habilitada
                  logger.debug(f"Intentando resolución automática de CAPTCHA de imagen. image_url: {image_url}")
                  solution = await self.captcha_solver.solve_captcha(image_url=image_url)

              if not solution: # Si la resolución automática falló o no estaba habilitada
                  logger.warning("Resolución automática de CAPTCHA de imagen fallida o deshabilitada. Intentando resolución manual.")
                  solution = await self.captcha_solver._solve_manually(image_url=image_url)
                  
                  if not solution:
                      logger.error("No se pudo resolver el CAPTCHA de imagen manualmente. Manteniendo la página abierta para intervención.")
                      return False # Indicar que no se resolvió automáticamente.

              if solution:
                  logger.info(f"Rellenando campo de CAPTCHA con la solución: {solution}")
                  await input_element.fill(solution)
                  
                  # Intentar enviar el formulario
                  await page.keyboard.press('Enter')
                  await page.wait_for_load_state('domcontentloaded')
                  await asyncio.sleep(random.uniform(3, 7)) # Esperar después de enviar CAPTCHA de imagen
                  logger.info("Formulario de CAPTCHA enviado.")
                  return True
              else:
                  logger.error("No se pudo resolver el CAPTCHA.")
                  return False
          else:
              logger.info("No se detectó ningún CAPTCHA en la página.")
              return False
      except Exception as e:
          logger.error(f"Error al manejar el CAPTCHA: {e}")
          return False

  
  async def new_page(self) -> Page:
      """
      Creates a new page or reuses one from the pool with optimized settings.
      """
      logger.debug("[NP_D] 1 - Entering new_page function.")
      if not self.is_initialized:
          logger.error("[NP_D] CRITICAL: Browser not initialized. Cannot create a new page.")
          raise Exception("Browser is not initialized. Cannot create a new page.")
      
      logger.debug("[NP_D] 2 - Attempting to acquire lock.")
      async with self._lock:  # Use lock to prevent race conditions
          logger.debug("[NP_D] 3 - Lock acquired.")
          # Check if we have pages in the pool
          if self.page_pool:
              page = self.page_pool.pop()
              logger.debug("[NP_D] 4a - Reusing page from pool.")
              
              # Reset page state
              try:
                  logger.debug("[NP_D] 5a - Navigating to about:blank to clear state.")
                  await page.goto("about:blank", wait_until="domcontentloaded")
                  logger.debug("[NP_D] 6a - Navigation to about:blank successful.")
                  
                  # Set a random user agent for each reused page
                  user_agent = self.user_agent_manager.get_random_user_agent()
                  await page.set_extra_http_headers({
                      "User-Agent": user_agent,
                      "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
                  })
                  logger.debug("[NP_D] 7a - Extra HTTP headers set.")

                  # Stealth is disabled for diagnostics
                  # await Stealth().apply_stealth_async(page)
                  
                  logger.debug("[NP_D] 8a - Returning reused page.")
                  return page
              except Exception as e:
                  logger.warning(f"[NP_D] 9a - Error resetting page state: {str(e)}. Closing page and creating new.")
                  try:
                      await page.close()
                  except:
                      pass # Ignore errors on close
          
          # If pool is empty or reuse failed, create a new page
          logger.debug("[NP_D] 4b - Pool empty or reuse failed. Creating new page.")
          try:
              page = await self.context.new_page()
              logger.debug("[NP_D] 5b - self.context.new_page() successful.")
          except Exception as e:
              logger.error(f"[NP_D] CRITICAL: self.context.new_page() failed: {e}", exc_info=True)
              raise

          # Stealth is disabled for diagnostics
          # await Stealth().apply_stealth_async(page)
          
          # Set a random user agent
          user_agent = self.user_agent_manager.get_random_user_agent()
          await page.set_extra_http_headers({
              "User-Agent": user_agent,
              "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
          })
          logger.debug("[NP_D] 6b - Extra HTTP headers set for new page.")
          
          logger.debug("[NP_D] 7b - Returning new page.")
          return page
  
  async def release_page(self, page: Page):
      """
      Releases a page back to the pool or closes it with improved resource management.
      
      Args:
          page: Page to release
      """
      if not page:
          return
      
      async with self._lock:  # Use lock to prevent race conditions
          # Check if the page is still usable
          try:
              is_closed = page.is_closed()
              if is_closed:
                  logger.debug("Page already closed, cannot return to pool")
                  return
          except Exception:
              # If we can't check if the page is closed, assume it's unusable
              logger.debug("Error checking page state, cannot return to pool")
              try:
                  await page.close()
              except:
                  pass
              return
          
          # If the pool is not full, try to clear the page and return it to the pool
          if len(self.page_pool) < self.max_pool_size:
              try:
                  # Clear page state
                  await page.goto("about:blank", wait_until="domcontentloaded", timeout=5000)
                  
                  # Try to clear JavaScript state, but don't fail if it doesn't work
                  try:
                      await page.evaluate("""() => { if (window.localStorage) localStorage.clear(); if (window.sessionStorage) sessionStorage.clear(); }""",)
                  except Exception as e:
                      logger.debug(f"Non-critical error clearing page storage: {str(e)}")
                  
                  # Add to pool
                  self.page_pool.append(page)
                  logger.debug("Page returned to pool")
              except Exception as e:
                  # If clearing fails, close the page
                  logger.debug(f"Failed to clear page: {str(e)}")
                  try:
                      await page.close()
                  except:
                      pass
                  logger.debug("Failed to clear page, closed instead")
          else:
              # Pool is full, close the page
              try:
                  await page.close()
              except:
                  pass
              logger.debug("Page pool full, closed page")
  
  async def check_playwright_browser(self) -> bool:
      """
      Checks if the browser has been initialized successfully.
      
      Returns:
          True if the browser is available, False otherwise.
      """
      logger.debug(f"Checking browser availability. Instance ID: {id(self)}. is_initialized={self.is_initialized}, browser={self.browser}")
      return self.is_initialized and self.browser is not None
  
  async def ensure_browser(self, headless: Optional[bool] = None):
      """
      Ensures the browser is initialized and returns the current browser context.
      This provides backward compatibility for callers that expect an `ensure_browser` helper.
      """
      if not self.is_initialized:
          await self.initialize(headless=headless)
      return self.context

  async def close(self):
      """Closes the browser and cleans up resources."""
      async with self._lock:  # Use lock to prevent race conditions
          try:
              # Close all pooled pages
              for page in self.page_pool:
                  try:
                      await page.close()
                  except Exception:
                      pass
              self.page_pool = []
              
              # Close browser
              if self.browser:
                  await self.browser.close()
                  self.browser = None
              
              # Close playwright
              if self.playwright:
                  await self.playwright.stop()
                  self.playwright = None
              
              self.is_initialized = False
              logger.info("Browser closed successfully")
          except Exception as e:
              logger.error(f"Error closing browser: {str(e)}")


  
  
  
  async def get_page(self):
      """
      Obtiene una página del navegador, reutilizando una del pool si está disponible.
      
      Returns:
          Página del navegador
      """
      return await self.new_page()  # Use the improved new_page method
  
  
  
  
  def set_proxies(self, proxies):
      """
      Sets the list of proxies to use for browser sessions.
      
      Args:
          proxies: List of proxy URLs
      """
      # Pass proxies to the proxy manager if available
      if hasattr(self, 'proxy_manager') and self.proxy_manager:
          # Clear existing proxies
          self.proxy_manager.proxies = []
          
          # Add new proxies
          for proxy in proxies:
              self.proxy_manager.add_proxy(proxy)
          
          logger.info(f"Set {len(proxies)} proxies in browser manager")

  async def initialize(self, headless: Optional[bool] = None):
      """Initialize the browser instance with enhanced stealth options."""
      async with self._lock:
          if self.is_initialized:
              logger.info("Browser already initialized")
              return
          
          try:
              logger.info("Starting Playwright...")
              self.playwright = await async_playwright().start()
              
              # More stealth arguments to avoid detection
              chromium_args = [
                  '--no-sandbox',
                  '--disable-setuid-sandbox',
                  '--disable-dev-shm-usage',
                  '--disable-accelerated-2d-canvas',
                  '--no-first-run',
                  '--no-zygote',
                  '--disable-gpu',
                  '--disable-blink-features=AutomationControlled' # Disables the "navigator.webdriver" flag
              ]

              logger.info("Launching browser...")
              actual_headless_mode = headless if headless is not None else self.config.get("headless_mode", True)
              logger.info(f"Playwright will launch browser with headless={actual_headless_mode}")
              self.browser = await self.playwright.chromium.launch(
                  headless=actual_headless_mode,
                  args=chromium_args
              )
              
              # Use more diverse and realistic viewport sizes to avoid detection patterns
              common_viewports = [
                  # Full HD and common desktop sizes
                  {"width": 1920, "height": 1080},
                  {"width": 1366, "height": 768},
                  {"width": 1536, "height": 864},
                  {"width": 1440, "height": 900},
                  {"width": 1680, "height": 1050},

                  # Modern laptop sizes
                  {"width": 2560, "height": 1440},
                  {"width": 1920, "height": 1200},
                  {"width": 1280, "height": 1024},

                  # Large displays
                  {"width": 2560, "height": 1600},
                  {"width": 3440, "height": 1440},

                  # Smaller screens and common resolutions
                  {"width": 1280, "height": 800},
                  {"width": 1024, "height": 768},
                  {"width": 1600, "height": 900},
                  {"width": 1360, "height": 768},
              ]

              # Select viewport with weighted probabilities to favor common sizes
              weights = [0.15, 0.12, 0.12, 0.10, 0.08, 0.08, 0.07, 0.06, 0.06, 0.05, 0.05, 0.04, 0.03, 0.03]
              viewport = random.choices(common_viewports, weights=weights, k=1)[0]

              # Add more varied locales and locations to avoid detection patterns
              locales = ['en-US', 'en-GB', 'en-CA', 'en-AU', 'de-DE', 'fr-FR', 'it-IT', 'es-ES']
              timezones = [
                  'America/New_York', 'America/Los_Angeles', 'America/Chicago',
                  'Europe/London', 'Europe/Berlin', 'Europe/Paris', 'Europe/Rome',
                  'America/Vancouver', 'Australia/Sydney', 'Canada/Eastern'
              ]
              locations = [
                  {'latitude': 40.7128, 'longitude': -74.0060}, # New York City
                  {'latitude': 37.7749, 'longitude': -122.4194}, # San Francisco
                  {'latitude': 51.5074, 'longitude': -0.1278}, # London
                  {'latitude': 52.5200, 'longitude': 13.4050}, # Berlin
                  {'latitude': 48.8566, 'longitude': 2.3522}, # Paris
                  {'latitude': 43.6532, 'longitude': -79.3832}, # Toronto
                  {'latitude': -33.8688, 'longitude': 151.2093}, # Sydney
                  {'latitude': 49.2827, 'longitude': -123.1207}, # Vancouver
              ]

              selected_locale = random.choice(locales)
              selected_timezone = random.choice(timezones)
              selected_location = random.choice(locations)

              logger.info("Creating browser context with enhanced fingerprinting protection...")
              logger.info(f"Using locale: {selected_locale}, timezone: {selected_timezone}")

              # Configurar Proxy si está disponible
              proxy_config = None
              if self.proxy_manager and self.proxy_manager.is_enabled():
                  proxy = self.proxy_manager.get_next_proxy()
                  if proxy:
                      proxy_config = self.proxy_manager.get_proxy_for_playwright(proxy)
                      logger.info(f"Usando proxy para el contexto: {proxy['host']}:{proxy['port']}")
              
              self.context = await self.browser.new_context(
                  user_agent=self.user_agent_manager.get_random_user_agent(),
                  ignore_https_errors=True,
                  viewport=viewport,
                  java_script_enabled=True,
                  bypass_csp=True,
                  proxy=proxy_config, # Inyectar configuración de proxy
                  # More varied and human-like environment settings
                  locale=selected_locale,
                  timezone_id=selected_timezone,
                  geolocation=selected_location,
                  permissions=['geolocation'],
                  record_har_path="network_trace.zip",
                  record_har_mode="full"
              )
              
              self.is_initialized = True
              logger.info("Browser initialized successfully with stealth enhancements.")
              
          except Exception as e:
              logger.error(f"Failed to initialize browser: {str(e)}")
              raise

  def set_proxy_manager(self, proxy_manager):
      """
      Establece el gestor de proxies a utilizar.
      
      Args:
          proxy_manager: Instancia de ProxyManager
      """
      self.proxy_manager = proxy_manager
      logger.info("Proxy manager establecido en BrowserManager")