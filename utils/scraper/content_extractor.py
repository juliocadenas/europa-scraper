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
import socket

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
        
        # Explicitly disable browser usage (e.g. for API-only modes)
        self.browser_disabled = False

    def log_error(self, error_type, message, url, exc_info=False):
        """Logs a detailed error message."""
        logger.error(
            f"[{error_type}] Failed to extract content from {url}: {message}",
            exc_info=exc_info
        )
  
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
            delay = random.uniform(1.0, 2.0)
        else:
            # Fewer requests = shorter delay
            delay = random.uniform(0.3, 1.0)
        
        # Add jitter for more natural behavior
        delay += random.uniform(-0.2, 0.2)
        
        # Ensure minimum delay and maximum delay
        delay = max(0.2, min(delay, 2.0))
        
        # Record this request
        self._request_times.append(now)
        if len(self._request_times) > self._max_request_history:
            self._request_times.pop(0)
        
        try:
            await asyncio.wait_for(asyncio.sleep(delay), timeout=delay+1.0)
        except asyncio.TimeoutError:
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
        Extracts content using aiohttp (faster but less reliable) with a retry mechanism.
        
        Args:
            url: URL to extract content from
            
        Returns:
            Extracted text or None if extraction failed
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
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
                # Configurar resolver DNS personalizado para evitar problemas en WSL
                resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "1.1.1.1"])
                connector = aiohttp.TCPConnector(resolver=resolver, family=socket.AF_INET, ssl=False)
                async with aiohttp.ClientSession(headers=headers, timeout=timeout, connector=connector) as session:
                    async with session.get(url, timeout=30, ssl=False, allow_redirects=True) as response:
                        if response.status != 200:
                            self.log_error("AIOHTTP_STATUS_ERROR", f"Returned status {response.status}", url)
                            return None
                        content_type = response.headers.get('Content-Type', '').lower()

                        if 'text/html' in content_type or 'application/xhtml+xml' in content_type:
                            html = await response.text()
                            text = re.sub(r'<script.*?</script>', ' ', html, flags=re.DOTALL)
                            text = re.sub(r'<style.*?</style>', ' ', text, flags=re.DOTALL)
                            text = re.sub(r'<[^>]+>', ' ', text)
                            text = re.sub(r'\s+', ' ', text).strip()
                            return text
                        elif any(mime in content_type for mime in ['pdf', 'msword', 'officedocument', 'text/plain']):
                            return await self.file_extractor.extract_text_from_url(url)
                        else:
                            self.log_error("AIOHTTP_CONTENT_TYPE_ERROR", f"Unsupported content type: {content_type}", url)
                            return None
            except aiohttp.ClientConnectorError as e:
                wait_time = 2 ** (attempt + 1)
                self.log_error("AIOHTTP_EXTRACTION_ERROR", f"Connection error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...", url, exc_info=False)
                if attempt + 1 < max_retries:
                    await asyncio.sleep(wait_time)
                else:
                    self.log_error("AIOHTTP_EXTRACTION_ERROR", f"Connection failed after {max_retries} attempts.", url, exc_info=True)
                    return None
            except Exception as e:
                self.log_error("AIOHTTP_EXTRACTION_ERROR", str(e), url, exc_info=True)
                return None
        return None
  
    @lru_cache(maxsize=100)
    async def _extract_with_browser(self, url: str) -> Optional[str]:
        """
        Extracts content using browser (slower but more reliable).
        """
        if self.browser_disabled:
            # logger.debug(f"Browser extraction disabled, skipping for {url}")
            return None

        page = None
        try:
            async with self._extraction_semaphore:
                context = await self.browser_manager.ensure_browser()
                page = await self.browser_manager.new_page()
                page.set_default_timeout(60000)
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                except Exception as e:
                    self.log_error("BROWSER_NAVIGATION_ERROR", f"Page navigation timeout: {e}", url, exc_info=True)
                    return None
                
                try:
                    await page.wait_for_selector('body', timeout=15000)
                except Exception as e:
                    self.log_error("BROWSER_NO_BODY_ERROR", f"Timeout waiting for body: {e}", url)
                
                try:
                    content = await page.evaluate('''
    () => {
    try {
        if (!document || !document.body) {
            return "No content available - page not fully loaded";
        }
        const clone = document.body.cloneNode(true);
        if (!clone) {
            return document.body ? document.body.innerText || "No content available" : "No content available";
        }
        const elementsToRemove = clone.querySelectorAll('script, style, noscript, iframe, nav, footer, header, aside, .nav, .menu, .sidebar, .advertisement, .ad, .banner, .cookie, .popup, .modal');
        elementsToRemove.forEach(el => {
            try {
                if (el && el.remove) el.remove();
            } catch (removeError) {
            }
        });
        const mainContent = clone.querySelector('main, article, .content, #content, .main-content, .post-content, .entry-content, .article-content, [role="main"], [class*="main"], [class*="content"]');
        if (mainContent && mainContent.innerText) {
            return mainContent.innerText.trim();
        }
        return clone.innerText ? clone.innerText.trim() : "No content available";
    } catch (e) {
        try {
            return document.body && document.body.innerText ? document.body.innerText.trim() : "No content available";
        } catch (fallbackError) {
            return "No content available - JavaScript extraction failed";
        }
    }
    }
    ''')
                except Exception as e:
                    self.log_error("BROWSER_JS_EXTRACTION_ERROR", f"Error extracting content with JavaScript: {e}", url, exc_info=True)
                    try:
                        content = await page.content()
                        if not content:
                            content = "No content available"
                        content = re.sub(r'<script[^>]*>.*?</script>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
                        content = re.sub(r'<style[^>]*>.*?</style>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
                        content = re.sub(r'<noscript[^>]*>.*?</noscript>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
                        content = re.sub(r'<(?:nav|footer|header|aside|iframe|form|button|input|select|textarea)[^>]*>.*?</\\1>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
                        content = re.sub(r'<[^>]+>', ' ', content)
                        content = re.sub(r'\s+', ' ', content).strip()
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
                        self.log_error("BROWSER_FALLBACK_EXTRACTION_ERROR", f"Fallback extraction also failed: {e2}", url, exc_info=True)
                        return None
                
                content = re.sub(r'\s+', ' ', content).strip()
                return content
                
        except Exception as e:
            self.log_error("BROWSER_EXTRACTION_ERROR", f"Browser extraction failed: {e}", url, exc_info=True)
            return None
        finally:
            if page:
                try:
                    await self.browser_manager.release_page(page)
                except Exception as e:
                    self.log_error("BROWSER_PAGE_RELEASE_ERROR", f"Error releasing page: {e}", url)
                    try:
                        await page.close()
                    except:
                        pass

    async def extract_full_content(self, url: str) -> str:
        """
        Extracts the full content from a URL.
        """
        if url in self._content_cache:
            self._cache_hits += 1
            return self._content_cache[url]
        
        self._cache_misses += 1
        
        await self._adaptive_delay()
        
        content = None
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            for special_domain, handler in self.special_domains.items():
                if special_domain in domain:
                    logger.info(f"Using special handler for domain: {special_domain}")
                    content = await handler(url)
                    break
            else:
                if self._is_file_url(url):
                    content = await self._extract_file_content(url)
                elif 'web.archive.org' in domain or 'archive.org' in domain:
                    logger.info(f"Detected archive.org URL, using HTTP-only extraction for: {url}")
                    max_attempts = 3
                    for attempt in range(max_attempts):
                        try:
                            content = await self._extract_with_aiohttp(url)
                            if content:
                                break
                        except Exception as e:
                            self.log_error("ARCHIVE_EXTRACTION_ERROR", f"aiohttp attempt {attempt+1} failed: {e}", url)
                        await asyncio.sleep(2 ** attempt)

                    if not content:
                        self.log_error("ARCHIVE_EXTRACTION_FAILED", "HTTP-only extraction failed for archive.org URL.", url)
                else:
                    content = await self._extract_with_aiohttp(url)
                    if not content:
                        content = await self._extract_with_browser(url)
        
        except Exception as e:
            self.log_error("FULL_EXTRACTION_ERROR", f"An unexpected error occurred: {e}", url, exc_info=True)
            content = None
            
        if content:
            if len(self._content_cache) >= self._cache_limit:
                keys = list(self._content_cache.keys())
                if keys:
                    del self._content_cache[random.choice(keys)]
            self._content_cache[url] = content
        
        return content or ""

    async def _handle_defense_gov(self, url: str) -> str:
        """
        Maneja URLs de media.defense.gov con estrategias especiales.
        """
        logger.info(f"Usando manejo especial para media.defense.gov: {url}")
        page = await self.browser_manager.new_page()
        try:
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
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_load_state('networkidle')
            content = await page.content()
            if url.lower().endswith('.pdf'):
                temp_path, _ = await self.file_extractor.download_file(url)
                if temp_path:
                    pdf_text = self.file_extractor._extract_pdf(temp_path)
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    return pdf_text
            return content
        except Exception as e:
            self.log_error("SPECIAL_HANDLER_ERROR", f"Error en manejo especial para media.defense.gov: {e}", url, exc_info=True)
            return ""
        finally:
            await self.browser_manager.release_page(page)

    async def _handle_dtic_mil(self, url: str) -> str:
        """
        Maneja URLs de apps.dtic.mil con estrategias especiales.
        """
        logger.info(f"Usando manejo especial para apps.dtic.mil: {url}")
        page = await self.browser_manager.new_page()
        try:
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
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_load_state('networkidle')
            content = await page.content()
            if url.lower().endswith('.pdf'):
                logger.info(f"Detectado PDF en apps.dtic.mil: {url}")
                pdf_text = await self._download_pdf_with_fallback(url)
                if pdf_text:
                    return pdf_text
            return content
        except Exception as e:
            self.log_error("SPECIAL_HANDLER_ERROR", f"Error en manejo especial para apps.dtic.mil: {e}", url, exc_info=True)
            return ""
        finally:
            await self.browser_manager.release_page(page)

    async def _handle_marines_mil(self, url: str) -> str:
        """
        Maneja URLs de www.marines.mil con estrategias especiales.
        """
        logger.info(f"Usando manejo especial para www.marines.mil: {url}")
        page = await self.browser_manager.new_page()
        try:
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
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_load_state('networkidle')
            content = await page.content()
            if url.lower().endswith('.pdf'):
                logger.info(f"Detectado PDF en www.marines.mil: {url}")
                pdf_text = await self._download_pdf_with_fallback(url)
                if pdf_text:
                    return pdf_text
            return content
        except Exception as e:
            self.log_error("SPECIAL_HANDLER_ERROR", f"Error en manejo especial para www.marines.mil: {e}", url, exc_info=True)
            return ""
        finally:
            await self.browser_manager.release_page(page)
  
    async def _handle_fldoe_org(self, url: str) -> str:
        """
        Maneja URLs de info.fldoe.org con estrategias especiales.
        """
        logger.info(f"Usando manejo especial para info.fldoe.org: {url}")
        page = await self.browser_manager.new_page()
        try:
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
            await page.goto(url, wait_until='domcontentloaded', timeout=120000)
            await page.wait_for_load_state('networkidle')
            content = await page.content()
            if url.lower().endswith('.pdf'):
                logger.info(f"Detectado PDF en info.fldoe.org: {url}")
                pdf_text = await self._download_pdf_with_fallback(url)
                if pdf_text:
                    return pdf_text
            return content
        except Exception as e:
            self.log_error("SPECIAL_HANDLER_ERROR", f"Error en manejo especial para info.fldoe.org: {e}", url, exc_info=True)
            return ""
        finally:
            await self.browser_manager.release_page(page)
  
    async def _extract_file_content(self, url: str) -> str:
        """
        Extracts content from a file URL with retry mechanism.
        """
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                content = await self.file_extractor.extract_text_from_url(url)
                if content:
                    logger.info(f"Content extracted from file at {url}: {len(content)} characters")
                    return content
                
                if retry_count == 0:
                    logger.info(f"Trying alternative download method for {url}")
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(url, timeout=30, ssl=False) as response:
                                if response.status == 200:
                                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                                    temp_path = temp_file.name
                                    temp_file.close()
                                    buffer = await response.read()
                                    with open(temp_path, 'wb') as f:
                                        f.write(buffer)
                                    pdf_text = self.file_extractor._extract_pdf(temp_path)
                                    if os.path.exists(temp_path):
                                        os.unlink(temp_path)
                                    if pdf_text:
                                        logger.info(f"Content extracted using alternative method: {len(pdf_text)} characters")
                                        return pdf_text
                    except Exception as alt_e:
                        self.log_error("FILE_DOWNLOAD_ERROR", f"Alternative download method failed: {alt_e}", url)
                
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    logger.info(f"Retrying extraction ({retry_count}/{max_retries}) after {wait_time}s for {url}")
                    await asyncio.sleep(wait_time)
                else:
                    self.log_error("FILE_EXTRACTION_ERROR", f"No content extracted after {max_retries} attempts", url)
                    return ""
                    
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    self.log_error("FILE_EXTRACTION_RETRY_ERROR", f"Retrying ({retry_count}/{max_retries}) after {wait_time}s due to error: {e}", url)
                    await asyncio.sleep(wait_time)
                else:
                    self.log_error("FILE_EXTRACTION_FATAL_ERROR", f"Failed after {max_retries} attempts: {e}", url, exc_info=True)
                    return ""
        return ""
  
    async def _extract_web_content(self, url: str) -> str:
        """
        Extracts content from a web page URL.
        """
        try:
            content = await self._extract_with_aiohttp(url)
            if not content:
                content = await self._extract_with_browser(url)
            if content:
                return content
            else:
                self.log_error("WEB_EXTRACTION_ERROR", "No content extracted from web page", url)
                return ""
        except Exception as e:
            self.log_error("WEB_EXTRACTION_FATAL_ERROR", f"Error extracting content from web page: {e}", url, exc_info=True)
            return ""
  
    async def analyze_relevance(self, url: str, search_term: str, text_processor) -> float:
        """
        Analyzes the relevance of a URL's content to a search term.
        """
        try:
            text_content = await self.extract_full_content(url)
            if not text_content:
                self.log_error("RELEVANCE_ANALYSIS_ERROR", "No text content extracted", url)
                return 0.0
            
            text_content = text_content.lower()
            search_term = search_term.lower()
            search_words = re.findall(r'\w+', search_term)
            if not search_words:
                logger.warning(f"No valid search words in '{search_term}'")
                return 0.0
            
            word_counts = {}
            total_words = len(re.findall(r'\w+', text_content))
            for word in search_words:
                if len(word) <= 2:
                    continue
                pattern = r'\b' + re.escape(word) + r'\b'
                count = len(re.findall(pattern, text_content))
                word_counts[word] = count
            
            if not word_counts:
                logger.info(f"No matching words found for '{search_term}' in {url}")
                return 0.0
            
            frequency_score = sum(word_counts.values()) / max(1, total_words) * 10
            coverage_score = len([w for w, c in word_counts.items() if c > 0]) / max(1, len(word_counts))
            phrase_bonus = 0.0
            if len(search_words) > 1:
                phrase_pattern = re.escape(search_term)
                phrase_matches = len(re.findall(phrase_pattern, text_content))
                phrase_bonus = min(0.5, phrase_matches * 0.2)
            relevance_score = (frequency_score * 0.6) + (coverage_score * 0.2) + phrase_bonus
            relevance_score = min(1.0, relevance_score)
            if any(word in text_content.lower() for word in search_words) and relevance_score < 0.1:
                relevance_score = 0.1
            logger.info(f"Relevance score for '{search_term}' in {url}: {relevance_score:.2f}")
            return relevance_score
        except Exception as e:
            self.log_error("RELEVANCE_ANALYSIS_FATAL_ERROR", f"Error analyzing relevance: {e}", url, exc_info=True)
            return 0.0

    async def _download_pdf_with_fallback(self, url: str) -> str:
        """
        Intenta descargar un PDF usando múltiples métodos con fallback.
        """
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
                self.log_error("PDF_DOWNLOAD_ERROR", f"Método {i+1} falló: {e}", url)
        self.log_error("PDF_DOWNLOAD_FATAL_ERROR", "Todos los métodos de descarga fallaron", url)
        return ""

    async def _download_pdf_with_playwright(self, url: str) -> str:
        """
        Descarga un PDF usando Playwright.
        """
        page = await self.browser_manager.new_page()
        try:
            client = await page.context.new_cdp_session(page)
            await client.send('Page.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': tempfile.gettempdir()
            })
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            if not response.ok:
                self.log_error("PDF_DOWNLOAD_PLAYWRIGHT_ERROR", f"Respuesta no válida: {response.status}", url)
                return ""
            buffer = await response.body()
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_path = temp_file.name
            temp_file.close()
            with open(temp_path, 'wb') as f:
                f.write(buffer)
            pdf_text = self.file_extractor._extract_pdf(temp_path)
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return pdf_text
        finally:
            await self.browser_manager.release_page(page)

    async def _download_pdf_with_aiohttp(self, url: str) -> str:
        """
        Descarga un PDF usando aiohttp.
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/pdf,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': urlparse(url).scheme + '://' + urlparse(url).netloc + '/',
        }
        resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "1.1.1.1"])
        connector = aiohttp.TCPConnector(resolver=resolver, family=socket.AF_INET, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, headers=headers, timeout=30, ssl=False) as response:
                if response.status != 200:
                    self.log_error("PDF_DOWNLOAD_AIOHTTP_ERROR", f"Respuesta no válida: {response.status}", url)
                    return ""
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                temp_path = temp_file.name
                temp_file.close()
                with open(temp_path, 'wb') as f:
                    f.write(await response.read())
                pdf_text = self.file_extractor._extract_pdf(temp_path)
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return pdf_text

    async def _download_pdf_with_curl_like(self, url: str) -> str:
        """
        Simula una descarga tipo curl con cabeceras específicas.
        """
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
        timeout = aiohttp.ClientTimeout(total=60)
        resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "1.1.1.1"])
        connector = aiohttp.TCPConnector(resolver=resolver, family=socket.AF_INET, ssl=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            try:
                async with session.get(url, headers=headers, ssl=False, allow_redirects=True) as response:
                    if response.status != 200:
                        self.log_error("PDF_DOWNLOAD_CURL_ERROR", f"Respuesta no válida: {response.status}", url)
                        return ""
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                    temp_path = temp_file.name
                    temp_file.close()
                    chunk_size = 1024
                    with open(temp_path, 'wb') as fd:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            fd.write(chunk)
                    pdf_text = self.file_extractor._extract_pdf(temp_path)
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    return pdf_text
            except Exception as e:
                self.log_error("PDF_DOWNLOAD_CURL_FATAL_ERROR", f"Error en descarga tipo curl: {e}", url, exc_info=True)
                return ""