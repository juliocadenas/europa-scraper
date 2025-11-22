import logging
import re
import asyncio
from typing import Optional, Dict
from urllib.parse import urlparse
import aiohttp
from functools import lru_cache
import time
import random
import os
import tempfile

from utils.scraper.browser_manager import BrowserManager
from utils.file_extractor import FileExtractor
from utils.url_cache import URLCache

logger = logging.getLogger(__name__)

class ContentExtractor:
  """
  Extrae contenido de páginas web y archivos.
  """
  
  def __init__(self, browser_manager):
      """
      Inicializa el extractor de contenido.
      
      Args:
          browser_manager: Instancia de BrowserManager para navegar por páginas web
      """
      self.browser_manager = browser_manager
      self.file_extractor = FileExtractor()
      self.url_cache = URLCache()  # Añadir sistema de caché
      
      # Cache for extracted content
      self._content_cache = {}
      self._cache_hits = 0
      self._cache_misses = 0
      self._cache_limit = 500  # Limit cache size to avoid memory issues
      
      # Track request times for adaptive delays
      self._request_times = []
      self._max_request_history = 50
      
      # File extensions for common downloadable files
      self.file_extensions = ['.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.csv', '.json', '.xml']
      
      # Dominios que requieren manejo especial
      self.special_domains = {
          'media.defense.gov': self._handle_defense_gov,
          'apps.dtic.mil': self._handle_dtic_mil,
          'www.marines.mil': self._handle_marines_mil,
          'info.fldoe.org': self._handle_fldoe_org,
      }
      
      # Semaphore to limit concurrent extractions
      self._extraction_semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent extractions
  
  async def _adaptive_delay(self):
      """
      Implements an adaptive delay based on recent request history.
      Helps avoid detection and rate limiting.
      """
      now = time.time()
      
      # Clean old request times
      self._request_times = [t for t in self._request_times if now - t < 60]
      
      # Calculate delay based on request frequency
      if len(self._request_times) > 10:
          # More requests = longer delay
          delay = random.uniform(1.0, 2.0)  # Reduced from 1.5-3.0 to 1.0-2.0
      else:
          # Fewer requests = shorter delay
          delay = random.uniform(0.3, 1.0)  # Reduced from 0.5-1.5 to 0.3-1.0
      
      # Add jitter for more natural behavior
      delay += random.uniform(-0.2, 0.2)
      
      # Ensure minimum delay and maximum delay
      delay = max(0.2, min(delay, 2.0))  # Cap at 2.0 seconds
      
      # Record this request
      self._request_times.append(now)
      if len(self._request_times) > self._max_request_history:
          self._request_times.pop(0)
      
      # Use asyncio.wait_for to ensure the delay doesn't block indefinitely
      try:
          await asyncio.wait_for(asyncio.sleep(delay), timeout=delay+1.0)
      except asyncio.TimeoutError:
          # This should never happen, but just in case
          logger.warning("Adaptive delay timeout, continuing")
  
  def _is_file_url(self, url: str) -> bool:
      """
      Checks if a URL appears to point to a downloadable file.
      
      Args:
          url: URL to check
          
      Returns:
          True if it appears to be a file URL, False otherwise
      """
      parsed_url = urlparse(url)
      path = parsed_url.path.lower()
      return any(path.endswith(ext) for ext in self.file_extensions)
  
  async def _extract_with_aiohttp(self, url: str) -> Optional[str]:
      """
      Extracts content using aiohttp (faster but less reliable).
      
      Args:
          url: URL to extract content from
          
      Returns:
          Extracted text or None if extraction failed
      """
      try:
          # Normalize archive URLs to HTTPS to avoid redirections and blocking
          parsed = urlparse(url)
          netloc = parsed.netloc.lower()
          if 'archive.org' in netloc or 'web.archive.org' in netloc:
              if parsed.scheme != 'https':
                  try:
                      url = parsed._replace(scheme='https').geturl()
                  except Exception:
                      url = url.replace('http://', 'https://', 1)

          headers = {
              'User-Agent': getattr(self, 'user_agent_manager', None).get_random_user_agent() if getattr(self, 'user_agent_manager', None) else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
              'Accept-Language': 'en-US,en;q=0.9',
              'Referer': 'https://www.google.com/'
          }

          timeout = aiohttp.ClientTimeout(total=30)
          async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
              async with session.get(url, timeout=30, ssl=False, allow_redirects=True) as response:
                  if response.status != 200:
                      logger.debug(f"aiohttp returned status {response.status} for {url}")
                      return None
                  content_type = response.headers.get('Content-Type', '').lower()

                  # Handle different content types
                  if 'text/html' in content_type or 'application/xhtml+xml' in content_type:
                      html = await response.text()

                      # Simple HTML to text conversion
                      text = re.sub(r'<script.*?</script>', ' ', html, flags=re.DOTALL)
                      text = re.sub(r'<style.*?</style>', ' ', text, flags=re.DOTALL)
                      text = re.sub(r'<[^>]+>', ' ', text)
                      text = re.sub(r'\s+', ' ', text).strip()
                      return text
                  elif any(mime in content_type for mime in ['pdf', 'msword', 'officedocument', 'text/plain']):
                      return await self.file_extractor.extract_text_from_url(url)
                  else:
                      return None
      except Exception as e:
          logger.debug(f"aiohttp extraction failed for {url}: {str(e)}")
          return None
  
  @lru_cache(maxsize=100)
  async def _extract_with_browser(self, url: str) -> Optional[str]:
    """
    Extracts content using browser (slower but more reliable).
    Cached to improve performance for repeated URLs.
    
    Args:
        url: URL to extract content from
        
    Returns:
        Extracted text or None if extraction failed
    """
    page = None
    try:
        # Use semaphore to limit concurrent extractions
        async with self._extraction_semaphore:
            # Get browser context
            context = await self.browser_manager.ensure_browser()
            
            # Create a new page
            page = await self.browser_manager.new_page()
            
            # Set longer timeout
            page.set_default_timeout(60000)  # 60 seconds
            
            # Navigate to the URL with a longer timeout
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            except Exception as e:
                logger.warning(f"Page navigation timeout for {url}: {str(e)}")
                return None
            
            # Wait for the body to be present
            try:
                await page.wait_for_selector('body', timeout=15000)
            except Exception as e:
                logger.debug(f"Timeout waiting for body on {url}, continuing with partial content: {str(e)}")
            
            # Extract text content using JavaScript with enhanced error handling
            try:
                content = await page.evaluate('''
() => {
try {
    // Check if document and body exist
    if (!document || !document.body) {
        return "No content available - page not fully loaded";
    }

    // Clone the body to avoid modifying the original page
    const clone = document.body.cloneNode(true);

    if (!clone) {
        return document.body ? document.body.innerText || "No content available" : "No content available";
    }

    // Remove elements that don't contain useful content
    const elementsToRemove = clone.querySelectorAll('script, style, noscript, iframe, nav, footer, header, aside, .nav, .menu, .sidebar, .advertisement, .ad, .banner, .cookie, .popup, .modal');
    elementsToRemove.forEach(el => {
        try {
            if (el && el.remove) el.remove();
        } catch (removeError) {
            // Silently continue if remove fails
        }
    });

    // Try to find the main content first
    const mainContent = clone.querySelector('main, article, .content, #content, .main-content, .post-content, .entry-content, .article-content, [role="main"], [class*="main"], [class*="content"]');

    if (mainContent && mainContent.innerText) {
        // If we find the main content, use it
        return mainContent.innerText.trim();
    }

    // If we don't find the main content, use the entire body
    return clone.innerText ? clone.innerText.trim() : "No content available";
} catch (e) {
    // If there's an error, try with the simple method
    try {
        return document.body && document.body.innerText ? document.body.innerText.trim() : "No content available";
    } catch (fallbackError) {
        return "No content available - JavaScript extraction failed";
    }
}
}
''')
            except Exception as e:
                logger.warning(f"Error extracting content with JavaScript: {str(e)}")
                # Try a simpler extraction method as fallback
                try:
                    content = await page.content()
                    if not content:
                        content = "No content available"

                    # Clean up HTML content more thoroughly
                    # Remove scripts and styles first
                    content = re.sub(r'<script[^>]*>.*?</script>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
                    content = re.sub(r'<style[^>]*>.*?</style>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
                    content = re.sub(r'<noscript[^>]*>.*?</noscript>', ' ', content, flags=re.DOTALL | re.IGNORECASE)

                    # Remove other unwanted tags but keep text between them
                    content = re.sub(r'<(?:nav|footer|header|aside|iframe|form|button|input|select|textarea)[^>]*>.*?</\1>', ' ', content, flags=re.DOTALL | re.IGNORECASE)

                    # Convert remaining HTML to text
                    content = re.sub(r'<[^>]+>', ' ', content)
                    content = re.sub(r'\s+', ' ', content).strip()

                    # If content is too short (probably just title or meta), check innerText
                    if len(content) < 100:
                        logger.debug("Content too short, trying innerText extraction")
                        inner_text = await page.evaluate('''() => {
                            try {
                                return document.body ? document.body.innerText.trim() : "";
                            } catch (e) {
                                return "";
                            }
                        }''')
                        if inner_text and len(inner_text.strip()) > len(content):
                            content = inner_text.strip()
                except Exception as e2:
                    logger.error(f"Fallback extraction also failed: {str(e2)}")
                    return None
            
            # Clean the content
            content = re.sub(r'\s+', ' ', content).strip()
            
            return content
            
    except Exception as e:
        logger.debug(f"Browser extraction failed for {url}: {str(e)}")
        return None
    finally:
        if page:
            try:
                await self.browser_manager.release_page(page)
            except Exception as e:
                logger.warning(f"Error releasing page: {str(e)}")
                # Try to close the page directly if release fails
                try:
                    await page.close()
                except:
                    pass
  
  async def extract_full_content(self, url: str) -> str:
    """
    Extracts the full content from a URL.
    
    Args:
        url: URL to extract content from
        
    Returns:
        Full content as text
    """
    # Check cache first
    if url in self._content_cache:
        self._cache_hits += 1
        return self._content_cache[url]
    
    self._cache_misses += 1
    
    # Apply adaptive delay
    await self._adaptive_delay()
    
    # Check if this is a special domain that needs custom handling
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    
    for special_domain, handler in self.special_domains.items():
        if special_domain in domain:
            logger.info(f"Using special handler for domain: {special_domain}")
            return await handler(url)
    
    # Check if this is a file URL
    if self._is_file_url(url):
        content = await self._extract_file_content(url)
    else:
        # If the target is Internet Archive / Wayback Machine, force API/HTTP-only extraction
        if 'web.archive.org' in domain or 'archive.org' in domain:
            logger.info(f"Detected archive.org URL, using HTTP-only extraction for: {url}")
            # Try aiohttp with retries and backoff, do NOT use browser for archive.org
            content = None
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    content = await self._extract_with_aiohttp(url)
                    if content:
                        break
                except Exception as e:
                    logger.debug(f"aiohttp attempt {attempt+1} failed for {url}: {e}")
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

            if not content:
                logger.warning(f"HTTP-only extraction failed for archive.org URL: {url}. Not falling back to browser to avoid scraping.")
        else:
            # Try aiohttp first (faster)
            content = await self._extract_with_aiohttp(url)
            # If aiohttp fails, try browser extraction
            if not content:
                content = await self._extract_with_browser(url)
    
    # Cache the result if it's not empty
    if content:
        # Manage cache size
        if len(self._content_cache) >= self._cache_limit:
            # Remove a random item to avoid cache growing too large
            keys = list(self._content_cache.keys())
            if keys:
                del self._content_cache[random.choice(keys)]
        
        self._content_cache[url] = content
    
    return content or ""  # Always return at least an empty string
  
  # Métodos para manejar dominios especiales
  
  async def _handle_defense_gov(self, url: str) -> str:
    """
    Maneja URLs de media.defense.gov con estrategias especiales.
    
    Args:
        url: URL de defense.gov
        
    Returns:
        Contenido extraído
    """
    logger.info(f"Usando manejo especial para media.defense.gov: {url}")
    
    # Intentar con User-Agent de navegador móvil
    page = await self.browser_manager.new_page()
    
    try:
        # Configurar encabezados adicionales
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.defense.gov/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Navegar a la URL
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        
        # Esperar a que se cargue el contenido
        await page.wait_for_load_state('networkidle')
        
        # Extraer el contenido
        content = await page.content()
        
        # Si es un PDF, intentar extraer el texto
        if url.lower().endswith('.pdf'):
            # Descargar el PDF
            temp_path, _ = await self.file_extractor.download_file(url)
            if temp_path:
                # Extraer texto del PDF
                pdf_text = self.file_extractor._extract_pdf(temp_path)
                # Limpiar el archivo temporal
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return pdf_text
        
        return content
    except Exception as e:
        logger.error(f"Error en manejo especial para media.defense.gov: {str(e)}")
        return ""
    finally:
        await self.browser_manager.release_page(page)
  
  async def _handle_dtic_mil(self, url: str) -> str:
    """
    Maneja URLs de apps.dtic.mil con estrategias especiales.
    
    Args:
        url: URL de dtic.mil
        
    Returns:
        Contenido extraído
    """
    logger.info(f"Usando manejo especial para apps.dtic.mil: {url}")
    
    # Similar al manejo de defense.gov pero con encabezados específicos para dtic.mil
    page = await self.browser_manager.new_page()
    
    try:
        # Configurar encabezados adicionales
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.dtic.mil/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Navegar a la URL
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        
        # Esperar a que se cargue el contenido
        await page.wait_for_load_state('networkidle')
        
        # Extraer el contenido
        content = await page.content()
        
        # Si es un PDF, intentar extraer el texto con métodos mejorados
        if url.lower().endswith('.pdf'):
            logger.info(f"Detectado PDF en apps.dtic.mil: {url}")
            pdf_text = await self._download_pdf_with_fallback(url)
            if pdf_text:
                return pdf_text
        
        return content
    except Exception as e:
        logger.error(f"Error en manejo especial para apps.dtic.mil: {str(e)}")
        return ""
    finally:
        await self.browser_manager.release_page(page)
  
  async def _handle_marines_mil(self, url: str) -> str:
    """
    Maneja URLs de www.marines.mil con estrategias especiales.
    
    Args:
        url: URL de marines.mil
        
    Returns:
        Contenido extraído
    """
    logger.info(f"Usando manejo especial para www.marines.mil: {url}")
    
    # Similar al manejo de defense.gov pero con encabezados específicos para marines.mil
    page = await self.browser_manager.new_page()
    
    try:
        # Configurar encabezados adicionales
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.marines.mil/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Navegar a la URL
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        
        # Esperar a que se cargue el contenido
        await page.wait_for_load_state('networkidle')
        
        # Extraer el contenido
        content = await page.content()
        
        # Si es un PDF, intentar extraer el texto con métodos mejorados
        if url.lower().endswith('.pdf'):
            logger.info(f"Detectado PDF en www.marines.mil: {url}")
            pdf_text = await self._download_pdf_with_fallback(url)
            if pdf_text:
                return pdf_text
        
        return content
    except Exception as e:
        logger.error(f"Error en manejo especial para www.marines.mil: {str(e)}")
        return ""
    finally:
        await self.browser_manager.release_page(page)
  
  async def _handle_fldoe_org(self, url: str) -> str:
    """
    Maneja URLs de info.fldoe.org con estrategias especiales.
    
    Args:
        url: URL de fldoe.org
        
    Returns:
        Contenido extraído
    """
    logger.info(f"Usando manejo especial para info.fldoe.org: {url}")
    
    # Intentar con User-Agent de navegador móvil y encabezados específicos
    page = await self.browser_manager.new_page()
    
    try:
        # Configurar encabezados adicionales
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.fldoe.org/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        })
        
        # Navegar a la URL con un timeout más largo
        await page.goto(url, wait_until='domcontentloaded', timeout=120000)
        
        # Esperar a que se cargue el contenido
        await page.wait_for_load_state('networkidle')
        
        # Extraer el contenido
        content = await page.content()
        
        # Si es un PDF, intentar extraer el texto con métodos mejorados
        if url.lower().endswith('.pdf'):
            logger.info(f"Detectado PDF en info.fldoe.org: {url}")
            pdf_text = await self._download_pdf_with_fallback(url)
            if pdf_text:
                return pdf_text
        
        return content
    except Exception as e:
        logger.error(f"Error en manejo especial para info.fldoe.org: {str(e)}")
        return ""
    finally:
        await self.browser_manager.release_page(page)
  
  async def _extract_file_content(self, url: str) -> str:
    """
    Extracts content from a file URL with retry mechanism.
    
    Args:
        url: URL of the file
        
    Returns:
        Extracted text content
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Intento normal de extracción
            content = await self.file_extractor.extract_text_from_url(url)
            if content:
                logger.info(f"Content extracted from file at {url}: {len(content)} characters")
                return content
            
            # Si no hay contenido pero no hubo error, intentar método alternativo
            if retry_count == 0:
                logger.info(f"Trying alternative download method for {url}")
                try:
                    # Método alternativo usando aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=30, ssl=False) as response:
                            if response.status == 200:
                                # Guardar el PDF en un archivo temporal
                                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                                temp_path = temp_file.name
                                temp_file.close()
                                
                                # Guardar el contenido del PDF
                                buffer = await response.read()
                                with open(temp_path, 'wb') as f:
                                    f.write(buffer)
                                
                                # Extraer texto del PDF
                                pdf_text = self.file_extractor._extract_pdf(temp_path)
                                
                                # Limpiar el archivo temporal
                                if os.path.exists(temp_path):
                                    os.unlink(temp_path)
                                
                                if pdf_text:
                                    logger.info(f"Content extracted using alternative method: {len(pdf_text)} characters")
                                    return pdf_text
                except Exception as alt_e:
                    logger.warning(f"Alternative download method failed: {str(alt_e)}")
            
            # Si llegamos aquí, incrementar contador de reintentos
            retry_count += 1
            if retry_count < max_retries:
                wait_time = 2 ** retry_count  # Espera exponencial: 2, 4, 8 segundos
                logger.info(f"Retrying extraction ({retry_count}/{max_retries}) after {wait_time}s for {url}")
                await asyncio.sleep(wait_time)
            else:
                logger.warning(f"No content extracted from file at {url} after {max_retries} attempts")
                return ""
                
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                wait_time = 2 ** retry_count
                logger.warning(f"Error extracting content, retrying ({retry_count}/{max_retries}) after {wait_time}s: {str(e)}")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Error extracting content from file at {url} after {max_retries} attempts: {str(e)}")
                return ""
    
    return ""  # Si llegamos aquí, todos los intentos fallaron
  
  async def _extract_web_content(self, url: str) -> str:
      """
      Extracts content from a web page URL.
      
      Args:
          url: URL of the web page
          
      Returns:
          Extracted text content
      """
      try:
          content = await self._extract_with_aiohttp(url)
          if not content:
              content = await self._extract_with_browser(url)
          
          if content:
              return content
          else:
              logger.warning(f"No content extracted from web page at {url}")
              return ""
      except Exception as e:
          logger.error(f"Error extracting content from web page at {url}: {str(e)}")
          return ""
  
  async def analyze_relevance(self, url: str, search_term: str, text_processor) -> float:
      """
      Analyzes the relevance of a URL's content to a search term.
      
      Args:
          url: URL to analyze
          search_term: Search term to check relevance for
          text_processor: Text processor instance
          
      Returns:
          Relevance score (0.0 to 1.0)
      """
      try:
          # Extract text content
          text_content = await self.extract_full_content(url)
          
          if not text_content:
              logger.warning(f"No text content extracted from {url}")
              return 0.0
          
          # Normalize text and search term
          text_content = text_content.lower()
          search_term = search_term.lower()
          
          # Split search term into words
          search_words = re.findall(r'\w+', search_term)
          
          if not search_words:
              logger.warning(f"No valid search words in '{search_term}'")
              return 0.0
          
          # Count occurrences of each search word
          word_counts = {}
          total_words = len(re.findall(r'\w+', text_content))
          
          for word in search_words:
              if len(word) <= 2:  # Skip very short words
                  continue
                  
              pattern = r'\b' + re.escape(word) + r'\b'
              count = len(re.findall(pattern, text_content))
              word_counts[word] = count
          
          if not word_counts:
              logger.info(f"No matching words found for '{search_term}' in {url}")
              return 0.0
          
          # Calculate relevance score
          # 1. Word frequency (more weight)
          frequency_score = sum(word_counts.values()) / max(1, total_words) * 10  # Multiplied by 10 to increase sensitivity

          # 2. Word coverage
          coverage_score = len([w for w, c in word_counts.items() if c > 0]) / max(1, len(word_counts))

          # 3. Bonus for exact phrase match
          phrase_bonus = 0.0
          if len(search_words) > 1:
              phrase_pattern = re.escape(search_term)
              phrase_matches = len(re.findall(phrase_pattern, text_content))
              phrase_bonus = min(0.5, phrase_matches * 0.2)  # Cap at 0.5, increased from 0.3

          # Combine scores with more weight on frequency
          relevance_score = (frequency_score * 0.6) + (coverage_score * 0.2) + phrase_bonus

          # Normalize to 0.0-1.0 range
          relevance_score = min(1.0, relevance_score)

          # Apply a minimum threshold for general content
          if any(word in text_content.lower() for word in search_words) and relevance_score < 0.1:
              relevance_score = 0.1  # Set a minimum if there's any match

          logger.info(f"Relevance score for '{search_term}' in {url}: {relevance_score:.2f}")
          
          return relevance_score
          
      except Exception as e:
          logger.error(f"Error analyzing relevance for {url}: {str(e)}")
          return 0.0

  async def _download_pdf_with_fallback(self, url: str) -> str:
    """
    Intenta descargar un PDF usando múltiples métodos con fallback.
    
    Args:
        url: URL del archivo PDF
        
    Returns:
        Texto extraído del PDF o cadena vacía si falla
    """
    # Lista de métodos a intentar en orden
    methods = [
        self._download_pdf_with_playwright,
        self._download_pdf_with_aiohttp,
        self._download_pdf_with_curl_like
    ]
    
    for i, method in enumerate(methods):
        try:
            logger.info(f"Intentando método {i+1}/{len(methods)} para descargar PDF: {url}")
            content = await method(url)
            if content:
                logger.info(f"PDF descargado exitosamente con método {i+1}")
                return content
        except Exception as e:
            logger.warning(f"Método {i+1} falló: {str(e)}")
    
    logger.error(f"Todos los métodos de descarga fallaron para: {url}")
    return ""

  async def _download_pdf_with_playwright(self, url: str) -> str:
    """
    Descarga un PDF usando Playwright.
    
    Args:
        url: URL del archivo PDF
        
    Returns:
        Texto extraído del PDF
    """
    page = await self.browser_manager.new_page()
    try:
        # Configurar para descargar el PDF
        client = await page.context.new_cdp_session(page)
        await client.send('Page.setDownloadBehavior', {
            'behavior': 'allow',
            'downloadPath': tempfile.gettempdir()
        })
        
        # Navegar a la URL
        response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        
        if not response.ok:
            return ""
            
        # Obtener el contenido del PDF
        buffer = await response.body()
        
        # Guardar en archivo temporal
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_path = temp_file.name
        temp_file.close()
        
        with open(temp_path, 'wb') as f:
            f.write(buffer)
        
        # Extraer texto
        pdf_text = self.file_extractor._extract_pdf(temp_path)
        
        # Limpiar
        if os.path.exists(temp_path):
            os.unlink(temp_path)
            
        return pdf_text
    finally:
        await self.browser_manager.release_page(page)

  async def _download_pdf_with_aiohttp(self, url: str) -> str:
    """
    Descarga un PDF usando aiohttp.
    
    Args:
        url: URL del archivo PDF
        
    Returns:
        Texto extraído del PDF
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/pdf,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': urlparse(url).scheme + '://' + urlparse(url).netloc + '/',
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=30, ssl=False) as response:
            if response.status != 200:
                return ""
                
            # Guardar en archivo temporal
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_path = temp_file.name
            temp_file.close()
            
            with open(temp_path, 'wb') as f:
                f.write(await response.read())
            
            # Extraer texto
            pdf_text = self.file_extractor._extract_pdf(temp_path)
            
            # Limpiar
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
            return pdf_text

  async def _download_pdf_with_curl_like(self, url: str) -> str:
    """
    Simula una descarga tipo curl con cabeceras específicas.
    
    Args:
        url: URL del archivo PDF
        
    Returns:
        Texto extraído del PDF
    """
    # Crear un proceso para simular curl
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/pdf,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': f"{parsed_url.scheme}://{domain}/",
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }
    
    # Usar aiohttp con configuración específica
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, headers=headers, ssl=False, allow_redirects=True) as response:
                if response.status != 200:
                    return ""
                    
                # Guardar en archivo temporal
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                temp_path = temp_file.name
                temp_file.close()
                
                chunk_size = 1024
                with open(temp_path, 'wb') as fd:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        fd.write(chunk)
                
                # Extraer texto
                pdf_text = self.file_extractor._extract_pdf(temp_path)
                
                # Limpiar
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
                return pdf_text
        except Exception as e:
            logger.error(f"Error en descarga tipo curl: {str(e)}")
            return ""
