import logging
import re
from typing import List, Dict, Tuple, Optional, Any
import asyncio
from playwright.async_api import async_playwright, Page, TimeoutError
from datetime import datetime
import os
import random
from utils.file_extractor import FileExtractor
import aiohttp
import ssl
import certifi

logger = logging.getLogger(__name__)

class ContentAnalyzer:
    """
    Analyzes web content for relevance to search terms.
    """
    
    def __init__(self):
        """Initialize the content analyzer."""
        self.browser = None
        self.context = None
        self.file_extractor = FileExtractor()
    
    async def _ensure_browser(self):
        """Ensure the browser is initialized."""
        if not self.browser:
            playwright = await async_playwright().start()
            try:
                # Try to launch with default settings
                self.browser = await playwright.chromium.launch(
                    headless=True,
                    ignore_default_args=["--enable-automation"],
                    args=["--disable-web-security", "--ignore-certificate-errors"]
                )
            except Exception as e:
                logger.warning(f"Error launching browser with default settings: {str(e)}")
                
                # Try with executable path explicitly set
                try:
                    # Get the Playwright browsers path from environment variable
                    browsers_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '')
                    
                    # Try different possible paths
                    possible_paths = [
                        os.path.join(browsers_path, "chromium-1161", "chrome-win", "chrome.exe"),
                        os.path.join(browsers_path, "chromium_headless_shell-1161", "chrome-win", "chrome.exe"),
                        os.path.join(browsers_path, "chromium_headless_shell-1161", "chrome-win", "headless_shell.exe")
                    ]
                    
                    # Find the first path that exists
                    executable_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            executable_path = path
                            break
                    
                    if executable_path:
                        logger.info(f"Using browser executable at: {executable_path}")
                        self.browser = await playwright.chromium.launch(
                            headless=True,
                            executable_path=executable_path,
                            ignore_default_args=["--enable-automation"],
                            args=["--disable-web-security", "--ignore-certificate-errors"]
                        )
                    else:
                        # If no path exists, try with channel
                        self.browser = await playwright.chromium.launch(
                            headless=True,
                            channel="chrome",
                            ignore_default_args=["--enable-automation"],
                            args=["--disable-web-security", "--ignore-certificate-errors"]
                        )
                except Exception as e2:
                    logger.error(f"Error launching browser with explicit path: {str(e2)}")
                    raise
            
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                ignore_https_errors=True
            )
    
    async def extract_text_from_url(self, url: str) -> str:
        """
        Extract text content from a URL.
        
        Args:
            url: URL to extract text from
        
        Returns:
            Extracted text content
        """
        browser = None
        page = None
        
        try:
            # Verificar si la URL parece ser un archivo descargable
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            path = parsed_url.path.lower()
            
            # Lista de extensiones de archivo comunes
            file_extensions = ['.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.csv', '.json', '.xml']
            
            # Verificar si la URL termina con una extensión de archivo conocida
            is_file = any(path.endswith(ext) for ext in file_extensions)
            
            # Si parece ser un archivo, usar el extractor de archivos
            if is_file:
                logger.info(f"Detectado archivo en URL: {url}")
                content = await self.file_extractor.extract_text_from_url(url)
                if content:
                    logger.info(f"Contenido extraído de archivo en {url}: {len(content)} caracteres")
                    return content
                else:
                    logger.warning(f"No se pudo extraer contenido del archivo en {url}, intentando como página web")
            
            # Verificar el tipo de contenido antes de navegar
            try:
                # Configurar un contexto SSL personalizado que ignore errores de verificación
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # Usar el contexto SSL personalizado con aiohttp
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                
                async with aiohttp.ClientSession(connector=connector) as session:
                    try:
                        # Hacer una solicitud HEAD para obtener los headers
                        async with session.head(url, allow_redirects=True, timeout=30) as response:
                            content_type = response.headers.get('Content-Type', '').lower()
                            
                            # Si es un tipo de archivo conocido, usar el extractor de archivos
                            if any(mime in content_type for mime in ['pdf', 'msword', 'officedocument', 'text/plain']):
                                logger.info(f"Detectado archivo por Content-Type: {content_type} en {url}")
                                content = await self.file_extractor.extract_text_from_url(url)
                                if content:
                                    logger.info(f"Contenido extraído de archivo en {url}: {len(content)} caracteres")
                                    return content
                    except Exception as e:
                        logger.warning(f"Error verificando headers: {str(e)}, continuando con navegación normal")
            except Exception as outer_e:
                logger.warning(f"Error en verificación de contenido: {str(outer_e)}")
            
            # Inicializar el navegador de forma segura
            playwright = await async_playwright().start()
            try:
                # Try to launch with default settings
                browser = await playwright.chromium.launch(
                    headless=True,
                    ignore_default_args=["--enable-automation"],
                    args=["--disable-web-security", "--ignore-certificate-errors"]
                )
            except Exception as e:
                logger.warning(f"Error launching browser with default settings: {str(e)}")
                
                # Try with executable path explicitly set
                try:
                    # Get the Playwright browsers path from environment variable
                    browsers_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '')
                    
                    # Try different possible paths
                    possible_paths = [
                        os.path.join(browsers_path, "chromium-1161", "chrome-win", "chrome.exe"),
                        os.path.join(browsers_path, "chromium_headless_shell-1161", "chrome-win", "chrome.exe"),
                        os.path.join(browsers_path, "chromium_headless_shell-1161", "chrome-win", "headless_shell.exe")
                    ]
                    
                    # Find the first path that exists
                    executable_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            executable_path = path
                            break
                    
                    if executable_path:
                        logger.info(f"Using browser executable at: {executable_path}")
                        browser = await playwright.chromium.launch(
                            headless=True,
                            executable_path=executable_path,
                            ignore_default_args=["--enable-automation"],
                            args=["--disable-web-security", "--ignore-certificate-errors"]
                        )
                    else:
                        # If no path exists, try with channel
                        browser = await playwright.chromium.launch(
                            headless=True,
                            channel="chrome",
                            ignore_default_args=["--enable-automation"],
                            args=["--disable-web-security", "--ignore-certificate-errors"]
                        )
                except Exception as e2:
                    logger.error(f"Error launching browser with explicit path: {str(e2)}")
                    
                    # Si falla el navegador, intentar con el extractor de archivos como último recurso
                    content = await self.file_extractor.extract_text_from_url(url)
                    if content:
                        logger.info(f"Contenido extraído de archivo como último recurso: {len(content)} caracteres")
                        return content
                    return ""
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                ignore_https_errors=True
            )
            
            page = await context.new_page()
            
            # Set timeout for navigation
            page.set_default_timeout(30000)
            
            # Navigate to the URL con mejor manejo de errores
            try:
                # Usar asyncio.wait_for para establecer un timeout estricto
                await asyncio.wait_for(
                    page.goto(url, wait_until='domcontentloaded'),
                    timeout=60.0  # 60 segundos de timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout en navegación inicial a {url}")
                
                # Intentar con el extractor de archivos como alternativa
                content = await self.file_extractor.extract_text_from_url(url)
                if content:
                    logger.info(f"Contenido extraído de archivo después de timeout: {len(content)} caracteres")
                    return content
                return ""
            except Exception as e:
                logger.warning(f"Error en navegación inicial: {str(e)}")
                try:
                    # Intentar de nuevo con un tiempo de espera más simple
                    await asyncio.wait_for(
                        page.goto(url),
                        timeout=60.0  # 60 segundos de timeout
                    )
                except Exception as e2:
                    logger.error(f"Error en navegación de respaldo: {str(e2)}")
                    
                    # Intentar con el extractor de archivos como alternativa
                    content = await self.file_extractor.extract_text_from_url(url)
                    if content:
                        logger.info(f"Contenido extraído de archivo después de error de navegación: {len(content)} caracteres")
                        return content
                    return ""
            
            # Wait for content to load
            await asyncio.sleep(2)
            
            # Verificar si la página redirigió a un archivo descargable
            current_url = page.url
            file_extensions = ['.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.csv', '.json', '.xml']
            if any(current_url.lower().endswith(ext) for ext in file_extensions):
                logger.info(f"Redirigido a archivo: {current_url}")
                content = await self.file_extractor.extract_text_from_url(current_url)
                if content:
                    logger.info(f"Contenido extraído de archivo redirigido: {len(content)} caracteres")
                    return content
            
            # Extract text content con mejor manejo
            try:
                # Esperar a que la página termine de cargar con timeout
                try:
                    await asyncio.wait_for(
                        page.wait_for_load_state('networkidle'),
                        timeout=30.0  # 30 segundos de timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout esperando carga completa para {url}, continuando de todos modos")
                
                # Extraer el texto con un enfoque más robusto y timeout
                try:
                    text_content = await asyncio.wait_for(
                        page.evaluate('''
                        () => {
                            try {
                                // Clonar el body para no modificar la página original
                                const clone = document.body.cloneNode(true);
                                
                                // Remover elementos que no contienen contenido útil
                                const elementsToRemove = clone.querySelectorAll('script, style, noscript, iframe, nav, footer, header, aside');
                                elementsToRemove.forEach(el => el.remove());
                                
                                // Extraer texto de los elementos principales
                                const mainContent = clone.querySelector('main, article, .content, #content, .main-content');
                                if (mainContent) {
                                    return mainContent.innerText;
                                }
                                
                                // Si no hay elementos principales, usar todo el body
                                return clone.innerText;
                            } catch (e) {
                                // Si hay algún error, intentar con el método simple
                                return document.body.innerText;
                            }
                        }
                        '''),
                        timeout=30.0  # 30 segundos de timeout
                    )
                    
                    if not text_content or text_content.strip() == "":
                        # Si no obtuvimos texto, intentar con un enfoque más simple
                        text_content = await asyncio.wait_for(
                            page.evaluate('document.body.innerText'),
                            timeout=10.0  # 10 segundos de timeout
                        )
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout en extracción de texto avanzada para {url}")
                    # Intentar con un método más simple
                    try:
                        text_content = await asyncio.wait_for(
                            page.evaluate('document.body.innerText'),
                            timeout=10.0  # 10 segundos de timeout
                        )
                    except Exception as e2:
                        logger.error(f"Error en extracción de texto de respaldo: {str(e2)}")
                        
                        # Intentar con el extractor de archivos como último recurso
                        content = await self.file_extractor.extract_text_from_url(url)
                        if content:
                            logger.info(f"Contenido extraído de archivo después de error de extracción: {len(content)} caracteres")
                            return content
                        text_content = ""
                except Exception as e:
                    logger.warning(f"Error en extracción de texto avanzada: {str(e)}")
                    # Intentar con un método más simple
                    try:
                        text_content = await asyncio.wait_for(
                            page.evaluate('document.body.innerText'),
                            timeout=10.0  # 10 segundos de timeout
                        )
                    except Exception as e2:
                        logger.error(f"Error en extracción de texto de respaldo: {str(e2)}")
                        
                        # Intentar con el extractor de archivos como último recurso
                        content = await self.file_extractor.extract_text_from_url(url)
                        if content:
                            logger.info(f"Contenido extraído de archivo después de error de extracción: {len(content)} caracteres")
                            return content
                        text_content = ""
            except Exception as e:
                logger.error(f"Error general en extracción de texto: {str(e)}")
                
                # Intentar con el extractor de archivos como último recurso
                content = await self.file_extractor.extract_text_from_url(url)
                if content:
                    logger.info(f"Contenido extraído de archivo después de error general: {len(content)} caracteres")
                    return content
                text_content = ""
            
            # Clean up the text
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            return text_content
            
        except Exception as e:
            logger.error(f"Error extracting text from URL {url}: {str(e)}")
            
            # Intentar con el extractor de archivos como último recurso
            try:
                content = await self.file_extractor.extract_text_from_url(url)
                if content:
                    logger.info(f"Contenido extraído de archivo después de error general: {len(content)} caracteres")
                    return content
            except Exception as file_e:
                logger.error(f"Error en extracción de archivo de respaldo: {str(file_e)}")
            
            return ""
        
        finally:
            # Asegurarse de cerrar la página y el navegador
            try:
                if page:
                    await page.close()
                if browser:
                    await browser.close()
            except Exception as e:
                logger.error(f"Error cerrando recursos: {str(e)}")
    
    async def analyze_relevance(self, url: str, search_term: str) -> float:
        """
        Analyze the relevance of a URL's content to a search term.
        
        Args:
            url: URL to analyze
            search_term: Search term to check relevance for
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        try:
            # Extract text content
            text_content = await self.extract_text_from_url(url)
            
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
            
            # Calcular puntuación de relevancia
            # 1. Frecuencia de palabras de búsqueda (más peso)
            frequency_score = sum(word_counts.values()) / max(1, total_words) * 10  # Multiplicado por 10 para aumentar sensibilidad

            # 2. Cobertura de palabras de búsqueda
            coverage_score = len([w for w, c in word_counts.items() if c > 0]) / max(1, len(word_counts))

            # 3. Bonus por coincidencia exacta de frase
            phrase_bonus = 0.0
            if len(search_words) > 1:
                phrase_pattern = re.escape(search_term)
                phrase_matches = len(re.findall(phrase_pattern, text_content))
                phrase_bonus = min(0.5, phrase_matches * 0.2)  # Cap at 0.5, increased from 0.3

            # Combinar puntuaciones con más peso en la frecuencia
            relevance_score = (frequency_score * 0.6) + (coverage_score * 0.2) + phrase_bonus

            # Normalizar al rango 0.0-1.0
            relevance_score = min(1.0, relevance_score)

            # Aplicar un umbral mínimo para contenido general
            if any(word in text_content.lower() for word in search_words) and relevance_score < 0.1:
                relevance_score = 0.1  # Establecer un mínimo si hay alguna coincidencia

            logger.info(f"Puntuación de relevancia para '{search_term}' en {url}: {relevance_score:.2f}")
            
            return relevance_score
            
        except Exception as e:
            logger.error(f"Error analyzing relevance for {url}: {str(e)}")
            return 0.0
    
    async def close(self):
        """Close the browser and clean up resources."""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
                self.context = None
                logger.info("Navegador del analizador de contenido cerrado correctamente")
        except Exception as e:
            logger.error(f"Error cerrando navegador del analizador de contenido: {str(e)}")
