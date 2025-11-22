import logging
import re
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import quote_plus, urlparse
from playwright.async_api import async_playwright, Page, TimeoutError
from datetime import datetime
import os
import random
from utils.file_extractor import FileExtractor
import aiohttp
import ssl
import certifi

logger = logging.getLogger(__name__)

class URLProcessor:
    """
    Procesa URLs y realiza búsquedas web en cordis.europa.eu.
    """
    
    def __init__(self):
        """Inicializa el procesador de URL."""
        self.browser = None
        self.context = None
        self.file_extractor = FileExtractor()
        self.stop_words = {
            'a', 'ante', 'bajo', 'con', 'contra', 'de', 'desde', 'durante', 'en', 'entre',
            'hacia', 'hasta', 'mediante', 'para', 'por', 'según', 'sin', 'sobre', 'tras',
            'y', 'e', 'ni', 'que', 'o', 'u', 'pero', 'mas', 'aunque', 'sino', 'porque',
            'pues', 'ya', 'si', 'the', 'of', 'and', 'to', 'in', 'for', 'with', 'on', 'at',
            'from', 'by', 'about', 'as', 'into', 'like', 'through', 'after', 'over', 'between',
            'out', 'against', 'during', 'without', 'before', 'under', 'around', 'among',
            'or', 'but', 'yet', 'so', 'nor', 'if', 'while', 'because', 'though', 'although',
            'since', 'unless', 'than', 'whether', 'as if', 'even if', 'in order that'
        }
    
    async def _ensure_browser(self):
        """Asegura que el navegador esté inicializado."""
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
    
    def quote_plus(self, text):
        """Codifica texto para URL."""
        return quote_plus(text)
    
    def filter_stop_words(self, query: str) -> str:
        """
        Filtra preposiciones y conjunciones de la consulta.
        
        Args:
            query: Consulta original
            
        Returns:
            Consulta filtrada
        """
        words = query.split()
        filtered_words = [word for word in words if word.lower() not in self.stop_words]
        
        # Si después de filtrar no queda nada, devolver la consulta original
        if not filtered_words:
            return query
            
        return ' '.join(filtered_words)
    
    def get_significant_words(self, text: str) -> List[str]:
        """
        Obtiene las palabras significativas (excluyendo preposiciones y conjunciones).
        
        Args:
            text: Texto a analizar
            
        Returns:
            Lista de palabras significativas
        """
        words = re.findall(r'\b\w+\b', text.lower())
        significant_words = [word for word in words if word not in self.stop_words]
        return significant_words
    
    def count_all_words(self, text: str) -> int:
        """
        Cuenta todas las palabras en el texto.
        
        Args:
            text: Texto a analizar
        
        Returns:
            Número total de palabras
        """
        words = re.findall(r'\b\w+\b', text.lower())
        return len(words)
    
    def count_significant_words(self, text: str) -> int:
        """
        Cuenta las palabras significativas (excluyendo preposiciones y conjunciones).
        
        Args:
            text: Texto a analizar
            
        Returns:
            Número de palabras significativas
        """
        return len(self.get_significant_words(text))
    
    def estimate_keyword_occurrences(self, content: str, search_term: str) -> Dict[str, int]:
        """
        Cuenta las ocurrencias de cada palabra clave del término de búsqueda en el contenido.
        
        Args:
            content: Contenido completo del documento
            search_term: Término de búsqueda
        
        Returns:
            Diccionario con conteo de cada palabra clave
        """
        # Obtener palabras clave del término de búsqueda (excluyendo stop words)
        search_words = self.get_significant_words(search_term)
        
        # También buscar frases completas (2-3 palabras consecutivas)
        search_phrases = []
        words = search_term.lower().split()
        if len(words) >= 2:
            for i in range(len(words) - 1):
                if words[i] not in self.stop_words and words[i+1] not in self.stop_words:
                    search_phrases.append(f"{words[i]} {words[i+1]}")
        
        if len(words) >= 3:
            for i in range(len(words) - 2):
                if words[i] not in self.stop_words and words[i+2] not in self.stop_words:
                    search_phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
        
        # Convertir contenido a minúsculas
        content_lower = content.lower()
        
        # Contar ocurrencias de cada palabra clave en el contenido
        word_counts = {}
        
        # Procesar palabras individuales
        for word in search_words:
            if len(word) <= 2:  # Ignorar palabras muy cortas
                continue
                
            # Buscar la palabra completa con límites de palabra
            pattern = r'\b' + re.escape(word) + r'\b'
            count = len(re.findall(pattern, content_lower))
            
            # Capitalizar primera letra para mejor presentación
            display_word = word[0].upper() + word[1:] if word else word
            word_counts[display_word] = count
        
        # Procesar frases (tienen mayor peso)
        for phrase in search_phrases:
            if len(phrase) <= 5:  # Ignorar frases muy cortas
                continue
            
            # Buscar la frase exacta
            count = content_lower.count(phrase)
            
            if count > 0:
                # Añadir la frase con un indicador
                word_counts[f"Frase: {phrase}"] = count
        
        return word_counts
    
    def format_word_counts(self, total_count: int, word_counts: Dict[str, int]) -> str:
        """
        Formatea el conteo de palabras según el formato requerido.
        Excluye palabras con conteo cero.
        
        Args:
            total_count: Conteo total de palabras
            word_counts: Diccionario con conteo de cada palabra clave
        
        Returns:
            Cadena formateada
        """
        parts = [f"Total words: {total_count}"]
        
        # Añadir conteo de cada palabra clave, excluyendo las que tienen conteo cero
        for word, count in word_counts.items():
            if count > 0:  # Solo incluir palabras con conteo mayor que cero
                parts.append(f"{word}: {count}")
        
        # Unir con el separador requerido
        return " | ".join(parts)
    
    def is_excluded_domain(self, url: str) -> bool:
        """
        Verifica si un dominio debe ser excluido.
        
        Args:
            url: URL a verificar
        
        Returns:
            True si debe ser excluido, False en caso contrario
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
        
            # Lista de dominios a excluir (vacía por ahora para capturar todos los resultados)
            excluded_domains = []
        
            for excluded in excluded_domains:
                if domain.endswith(excluded):
                    return True
            
            return False
        except:
            return False
    
    async def extract_search_results(self, page: Page) -> Tuple[List[str], List[str], List[str]]:
        """
        Extrae los resultados de búsqueda de la página actual.
        
        Args:
            page: Página de Playwright
            
        Returns:
            Tupla de (títulos, urls, descripciones)
        """
        # Extraer resultados usando JavaScript para mayor flexibilidad y precisión
        results = await page.evaluate('''
() => {
  const results = [];
  
  // Enfoque 1: Buscar todos los elementos que parecen resultados de búsqueda
  let resultElements = Array.from(document.querySelectorAll('.content-block-item, article, div[class*="result"], .result, .item, .search-result'));
  
  // Enfoque 2: Si no encontramos resultados con los selectores anteriores, buscar de forma más genérica
  if (resultElements.length === 0) {
      // Buscar elementos que tengan un título y un enlace
      const allElements = Array.from(document.querySelectorAll('div, section, article, li'));
      resultElements = allElements.filter(elem => {
          const hasTitle = elem.querySelector('h2, h3, h4, a[class*="title"], .title, a[href]:not([href^="#"])');
          const hasText = elem.textContent.trim().length > 50;
          return hasTitle && hasText;
      });
  }
  
  // Enfoque 3: Buscar directamente todos los enlaces con texto sustancial
  if (resultElements.length === 0) {
      const allLinks = Array.from(document.querySelectorAll('a[href]:not([href^="#"])'));
      const contentLinks = allLinks.filter(link => 
          link.textContent.trim().length > 20 && 
          !link.querySelector('img') &&
          !link.href.includes('javascript:')
      );
      
      // Convertir enlaces a elementos de resultado
      resultElements = contentLinks.map(link => {
          const container = document.createElement('div');
          container.appendChild(link.cloneNode(true));
          return container;
      });
  }
  
  // Procesar cada elemento de resultado
  for (const element of resultElements) {
      try {
          // Buscar el título (normalmente un enlace o un encabezado)
          let titleElement = element.querySelector('h2 a, h3 a, h4 a, a.title, a[class*="title"], .title a, a[href]:not([href^="#"])');
          
          if (!titleElement) {
              const links = Array.from(element.querySelectorAll('a[href]:not([href^="#"])'));
              // Filtrar enlaces que parezcan títulos
              const potentialTitleLinks = links.filter(link => 
                  link.textContent.trim().length > 10 && 
                  !link.querySelector('img') &&
                  !link.href.includes('javascript:')
              );
              
              if (potentialTitleLinks.length > 0) {
                  titleElement = potentialTitleLinks[0];
              }
          }
          
          if (!titleElement) continue;
          
          const title = titleElement.textContent.trim();
          const url = titleElement.href;
          
          if (!title || !url) continue;
          
          // Buscar la descripción
          let description = "";

          // Intentar encontrar elementos que puedan contener la descripción
          const descElements = element.querySelectorAll('p, .description, [class*="description"], .snippet, [class*="snippet"], div.summary, div.content, div[class*="content"], div[class*="text"], .abstract, .excerpt');

          // Combinar el texto de todos los elementos de descripción encontrados
          let combinedDesc = "";
          for (const elem of descElements) {
              if (elem !== titleElement && !elem.querySelector('h1, h2, h3, h4, h5, h6')) {
                  combinedDesc += " " + elem.textContent.trim();
              }
          }

          if (combinedDesc.trim()) {
              description = combinedDesc.trim();
          } else {
              // Si no hay elementos específicos, tomar todo el texto del resultado excluyendo el título
              const clone = element.cloneNode(true);
              
              // Eliminar elementos que no queremos en la descripción
              const elementsToRemove = clone.querySelectorAll('h1, h2, h3, h4, h5, h6, script, style, nav, header, footer');
              for (const elem of elementsToRemove) {
                  elem.remove();
              }
              
              // Eliminar URLs visibles del texto
              const urlElements = clone.querySelectorAll('a[href]');
              for (const urlElem of urlElements) {
                  if (urlElem.textContent.includes('http') || urlElem.textContent.includes('www.')) {
                      urlElem.remove();
                  }
              }
              
              description = clone.textContent.trim();
          }

          // Limpiar espacios múltiples
          description = description.replace(/\s+/g, ' ');

          // Aumentar el límite de longitud a 1000 caracteres
          if (description.length > 1000) {
              description = description.substring(0, 997) + '...';
          }
          
          // Buscar la URL visible (a menudo aparece como texto)
          let visibleUrl = "";
          const urlText = element.textContent.match(/(?:https?:\\/\\/|www\\.)\\S+/);
          if (urlText) {
              visibleUrl = urlText[0];
          }
          
          // Si no encontramos una URL visible, usar la URL del enlace
          if (!visibleUrl) {
              visibleUrl = url;
          }

          // Limpiar URLs de la descripción
          description = description.replace(/https?:\\/\\/\\S+/g, '');
          description = description.replace(/www\\.\\S+/g, '');
          description = description.replace(/\\s+/g, ' ').trim();
          
          results.push({
              title: title,
              url: url,
              description: description,
              visibleUrl: visibleUrl
          });
      } catch (e) {
          console.error('Error procesando resultado:', e);
      }
  }
  
  return results;
}
''')
    
        titles = []
        urls = []
        descriptions = []
        
        for result in results:
            if 'title' in result and 'url' in result:
                titles.append(result['title'])
                urls.append(result['url'])
                
                # Usar solo la descripción, sin la URL visible
                desc = result.get('description', '')
                descriptions.append(desc or "Sin descripción")
        
        return titles, urls, descriptions
    
    
    async def extract_full_content(self, url: str) -> str:
        """
        Extrae el contenido completo de una URL.
        
        Args:
            url: URL para extraer contenido
        
        Returns:
            Contenido textual completo de la página
        """
        try:
            # Verificar si la URL parece ser un archivo descargable
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
    
        # Si no es un archivo o no se pudo extraer contenido, proceder como página web
            await self._ensure_browser()
        
        # Crear una nueva página
            page = await self.context.new_page()
        
            try:
            # Configurar timeout más largo para páginas grandes
                page.set_default_timeout(60000)
            
            # Navegar a la URL
                logger.info(f"Extrayendo contenido completo de: {url}")
            
            # Verificar el tipo de contenido antes de navegar
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
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
                                    await page.close()
                                    return content
                    except Exception as e:
                        logger.warning(f"Error verificando headers: {str(e)}, continuando con navegación normal")
            
            # Navegar a la URL
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Esperar a que la página termine de cargar
                try:
                    await page.wait_for_load_state('networkidle', timeout=30000)
                except Exception as e:
                    logger.warning(f"Timeout esperando carga completa: {str(e)}")
            
            # Verificar si la página redirigió a un archivo descargable
                current_url = page.url
                if any(current_url.lower().endswith(ext) for ext in file_extensions):
                    logger.info(f"Redirigido a archivo: {current_url}")
                    content = await self.file_extractor.extract_text_from_url(current_url)
                    if content:
                        logger.info(f"Contenido extraído de archivo redirigido: {len(content)} caracteres")
                        await page.close()
                        return content
            
            # Extraer todo el contenido textual de la página
                content = await page.evaluate('''
() => {
  try {
      // Clonar el body para no modificar la página original
      const clone = document.body.cloneNode(true);
      
      // Remover elementos que no contienen contenido útil
      const elementsToRemove = clone.querySelectorAll('script, style, noscript, iframe, nav, footer, header, aside, .nav, .menu, .sidebar, .advertisement, .ad, .banner, .cookie, .popup, .modal');
      elementsToRemove.forEach(el => el.remove());
      
      // Intentar encontrar el contenido principal primero
      const mainContent = clone.querySelector('main, article, .content, #content, .main-content, .post-content, .entry-content, .article-content, [role="main"]');
      
      if (mainContent) {
          // Si encontramos el contenido principal, usarlo
          return mainContent.innerText;
      }
      
      // Si no encontramos el contenido principal, usar todo el cuerpo
      return clone.innerText;
  } catch (e) {
      // Si hay algún error, intentar con el método simple
      return document.body.innerText;
  }
}
''')
            
            # Limpiar el contenido
                content = re.sub(r'\s+', ' ', content).strip()
            
                logger.info(f"Contenido extraído de {url}: {len(content)} caracteres")
                return content
            
            except Exception as e:
                logger.error(f"Error extrayendo contenido de {url}: {str(e)}")
            
            # Si falla la extracción web, intentar como último recurso con el extractor de archivos
                try:
                    content = await self.file_extractor.extract_text_from_url(url)
                    if content:
                        logger.info(f"Contenido extraído como último recurso de {url}: {len(content)} caracteres")
                        return content
                except Exception as file_e:
                    logger.error(f"Error en extracción de respaldo: {str(file_e)}")
            
                return ""
            
            finally:
                await page.close()
            
        except Exception as e:
            logger.error(f"Error general extrayendo contenido de {url}: {str(e)}")
            return ""
    
    # async def search_cordis_europa(self, query: str, max_pages: int = 50) -> List[Dict[str, Any]]:
    #     """
    #     Busca en cordis.europa.eu la consulta dada.
    #     
    #     Args:
    #         query: Consulta de búsqueda
    #         max_pages: Número máximo de páginas a procesar
    #         
    #     Returns:
    #     Lista de diccionarios con resultados de búsqueda
    #     """
    #     browser = None
    #     page = None
    #     
    #     try:
    #         # Inicializar el navegador de forma segura
    #         playwright = await async_playwright().start()
    #         try:
    #             # Try to launch with default settings
    #             browser = await playwright.chromium.launch(
    #                 headless=True,
    #                 ignore_default_args=["--enable-automation"],
    #                 args=["--disable-web-security", "--ignore-certificate-errors"]
    #             )
    #         except Exception as e:
    #             logger.warning(f"Error launching browser with default settings: {str(e)}")
    #         
    #         # Try with executable path explicitly set
    #         try:
    #             # Get the Playwright browsers path from environment variable
    #             browsers_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '')
    #             
    #             # Try different possible paths
    #             possible_paths = [
    #                 os.path.join(browsers_path, "chromium-1161", "chrome-win", "chrome.exe"),
    #                 os.path.join(browsers_path, "chromium_headless_shell-1161", "chrome-win", "chrome.exe"),
    #                 os.path.join(browsers_path, "chromium_headless_shell-1161", "chrome-win", "headless_shell.exe")
    #             ]
    #             
    #             # Find the first path that exists
    #             executable_path = None
    #             for path in possible_paths:
    #                 if os.path.exists(path):
    #                     executable_path = path
    #                     break
    #             
    #             if executable_path:
    #                 logger.info(f"Using browser executable at: {executable_path}")
    #                 browser = await playwright.chromium.launch(
    #                     headless=True,
    #                     executable_path=executable_path,
    #                     ignore_default_args=["--enable-automation"],
    #                     args=["--disable-web-security", "--ignore-certificate-errors"]
    #                 )
    #             else:
    #                 # If no path exists, try with channel
    #                 browser = await playwright.chromium.launch(
    #                     headless=True,
    #                     channel="chrome",
    #                     ignore_default_args=["--enable-automation"],
    #                     args=["--disable-web-security", "--ignore-certificate-errors"]
    #                 )
    #         except Exception as e2:
    #             logger.error(f"Error launching browser with explicit path: {str(e2)}")
    #             return []

    #         context = await browser.new_context(
    #             user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    #             ignore_https_errors=True
    #         )
    #         
    #         # Filtrar preposiciones y conjunciones de la consulta
    #         filtered_query = self.filter_stop_words(query)
    #         logger.info(f"Consulta original: '{query}', Consulta filtrada: '{filtered_query}'")
    #         
    #         # Codificar la consulta para URL
    #         encoded_query = quote_plus(filtered_query)
    #         
    #         # Construir la URL de búsqueda base
    #         base_url = "https://cordis.europa.eu/search"
    #         
    #         all_results = []
    #         page_num = 1
    #         
    #         # Crear una nueva página
    #         page = await context.new_page()
    #         
    #         try:
    #             # Configurar el viewport para simular una pantalla más grande
    #             await page.set_viewport_size({"width": 1280, "height": 800})
    #             
    #             # Establecer un timeout global para la página
    #             page.set_default_timeout(60000)  # 60 segundos
    #             
    #             # Extract the total number of pages from the pagination
    #             total_pages = await self.extract_total_pages(page, f"{base_url}?q={encoded_query}&p=1&num=10&srt=Relevance:decreasing")
    #             if total_pages is None:
    #                 logger.warning("Could not determine total number of pages. Stopping at max_pages.")
    #                 total_pages = max_pages  # Limit to max_pages if extraction fails
    #             
    #             while page_num <= max_pages and page_num <= total_pages:
    #                 # Construir URL con número de página
    #                 search_url = f"{base_url}?q={encoded_query}&p={page_num}&num=10&srt=Relevance:decreasing"
    #                 
    #                 logger.info(f"Buscando en cordis.europa.eu: {filtered_query} - Página {page_num}")
    #                 logger.info(f"URL de búsqueda: {search_url}")
    #                 
    #                 try:
    #                     # Navegar a la URL de búsqueda con timeout
    #                     await asyncio.wait_for(
    #                         page.goto(search_url, wait_until='domcontentloaded'),
    #                         timeout=60.0  # 60 segundos de timeout
    #                     )
    #                     
    #                     # Esperar a que la página termine de cargar con timeout
    #                     try:
    #                         await asyncio.wait_for(
    #                             page.wait_for_load_state('networkidle'),
    #                             timeout=30.0  # 30 segundos de timeout
    #                         )
    #                     except asyncio.TimeoutError:
    #                         logger.warning(f"Timeout esperando carga completa en página {page_num}, continuando de todos modos")
    #                     
    #                     # Extraer resultados de la página actual
    #                     try:
    #                         titles, urls, descriptions = await asyncio.wait_for(
    #                             self.extract_search_results(page),
    #                             timeout=30.0  # 30 segundos de timeout
    #                         )
    #                     except asyncio.TimeoutError:
    #                         logger.error(f"Timeout extrayendo resultados en página {page_num}, saltando a la siguiente página")
    #                         page_num += 1
    #                         continue
    #                     
    #                     # Procesar resultados
    #                     for title, url, description in zip(titles, urls, descriptions):
    #                         # Asegurar que la URL sea absoluta
    #                         if url and not url.startswith(('http://', 'https://')):
    #                             if url.startswith('/'):
    #                                 url = f"https://cordis.europa.eu{url}"
    #                             else:
    #                                 url = f"https://cordis.europa.eu/{url}"
    #                         
    #                         # Verificar si el dominio debe ser excluido
    #                         if url and self.is_excluded_domain(url):
    #                             logger.info(f"Excluyendo URL de dominio no deseado: {url}")
    #                             continue
    #                         
    #                         # Añadir a resultados preliminares
    #                         all_results.append({
    #                             'title': title,
    #                             'url': url,
    #                             'description': description
    #                         })
    #                     
    #                     logger.info(f"Encontrados {len(titles)} resultados en la página {page_num}")
    #                     
    #                     page_num += 1
    #                     
    #                     # Pequeña pausa para evitar sobrecarga
    #                     await asyncio.sleep(random.uniform(1, 2))
    #                 
    #                 except asyncio.TimeoutError as e:
    #                     logger.error(f"Timeout en página {page_num}: {str(e)}")
    #                     # Intentar continuar con la siguiente página en caso de timeout
    #                     page_num += 1
    #                     continue
    #                 except Exception as e:
    #                     logger.error(f"Error procesando página {page_num}: {str(e)}")
    #                     # Intentar continuar con la siguiente página en caso de error
    #                     page_num += 1
    #                     continue
    #           
    #       finally:
    #           # Asegurarse de cerrar la página
    #           if page:
    #               await page.close()
    #       
    #       logger.info(f"Se encontraron {len(all_results)} resultados preliminares para la consulta: {query}")
    #       return all_results
    #     
    #     except Exception as e:
    #         logger.error(f"Error buscando en cordis.europa.eu: {str(e)}")
    #         return []
    #     
    #     finally:
    #         # Asegurarse de cerrar el navegador
    #         if browser:
    #             await browser.close()

    async def extract_total_pages(self, page: Page, search_url: str) -> Optional[int]:
        """
        Extrae el número total de páginas de la paginación.
        
        Args:
            page: Página de Playwright
            
        Returns:
            Número total de páginas o None si no se puede determinar
        """
        try:
            # Navegar a la primera página para extraer el número total de páginas
            await page.goto(search_url, wait_until='domcontentloaded')
            
            # Extraer el número total de páginas usando JavaScript
            total_pages = await page.evaluate('''
() => {
    try {
        // Buscar el último enlace de paginación que contenga un número
        const paginationLinks = Array.from(document.querySelectorAll('.pagination a, .usa-pagination a, nav[role="navigation"] a'));
        
        // Filtrar los enlaces que tienen contenido numérico
        const numericLinks = paginationLinks.filter(link => {
            const text = link.textContent.trim();
            return !isNaN(Number(text));
        });
        
        // Si no hay enlaces numéricos, buscar un elemento que indique el número total de páginas
        if (numericLinks.length === 0) {
            const totalPagesElement = document.querySelector('.usa-pagination__total-pages, .results-count');
            if (totalPagesElement) {
                const text = totalPagesElement.textContent.trim();
                const match = text.match(/\d+/);
                if (match) {
                    return parseInt(match[0]);
                }
            }
            return null;
        }
        
        // Obtener el número de página más alto
        const lastLink = numericLinks[numericLinks.length - 1];
        return parseInt(lastLink.textContent.trim());
    } catch (e) {
        console.error('Error extrayendo número total de páginas:', e);
        return null;
    }
}
''');
            
            if (total_pages):
                logger.info(f"Número total de páginas encontradas: {total_pages}")
                return int(total_pages)
            else:
                logger.warning("No se pudo determinar el número total de páginas")
                return None
            
        except Exception as e:
            logger.error(f"Error al extraer el número total de páginas: {str(e)}")
            return None
    
    async def close(self):
        """Cierra el navegador y limpia recursos."""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
                self.context = None
                logger.info("Navegador cerrado correctamente")
        except Exception as e:
            logger.error(f"Error cerrando navegador: {str(e)}")