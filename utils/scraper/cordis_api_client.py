import logging
import asyncio
import re
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class CordisApiClient:
    """
    V26 - COMPLETE REWRITE
    
    Client for scraping the Cordis Europa WEBSITE search results.
    The SPARQL endpoint has limited data (~2000 results).
    The WEBSITE search has the full dataset (~18,000+ results).
    
    This version scrapes the website search pages to get ALL results.
    """

    SEARCH_URL = "https://cordis.europa.eu/search/en"
    DET_BASE_URL = "https://cordis.europa.eu"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    
    async def search_projects_and_publications(self, query_term: str, search_mode: str = 'broad', max_results: int = 50000) -> List[Dict[str, Any]]:
        """
        V26 - Scrapes the Cordis WEBSITE search to get ALL results.
        
        1. First, gets the total count from page 1
        2. Then, paginates through ALL pages to collect results
        3. Returns the complete list for tabulation
        """
        logger.info(f"*** V26 ACTIVADA ***: Iniciando scraping de búsqueda WEB de Cordis para '{query_term}'")
        
        all_results = []
        page = 1
        results_per_page = 100  # Maximum allowed by Cordis
        total_results = None
        
        # URL encode the query
        encoded_query = quote_plus(query_term)
        
        while True:
            # Build the search URL
            # Format: https://cordis.europa.eu/search/en?q=QUERY&p=PAGE&num=100&srt=/project/contentUpdateDate:decreasing
            search_url = f"{self.SEARCH_URL}?q={encoded_query}&p={page}&num={results_per_page}&srt=/project/contentUpdateDate:decreasing"
            
            logger.info(f"V26 - Fetching page {page}: {search_url}")
            
            loop = asyncio.get_running_loop()
            def _fetch_page():
                import requests
                return requests.get(search_url, headers=self.headers, timeout=60)
            
            try:
                response = await loop.run_in_executor(None, _fetch_page)
                
                if response.status_code != 200:
                    logger.error(f"Error fetching Cordis page {page}: Status {response.status_code}")
                    break
                
                html = response.text
                
                # Extract total results count from HTML (first page only)
                if total_results is None:
                    # Look for pattern like "1 - 100 of 18,595 results"
                    count_match = re.search(r'of\s+([\d,]+)\s+results?', html)
                    if count_match:
                        total_results = int(count_match.group(1).replace(',', ''))
                        logger.info(f"*** V26 - TOTAL DISPONIBLE EN CORDIS WEB: {total_results} resultados ***")
                    else:
                        # Try alternate pattern: "Results: 18595"
                        count_match2 = re.search(r'Results:\s*([\d,]+)', html)
                        if count_match2:
                            total_results = int(count_match2.group(1).replace(',', ''))
                            logger.info(f"*** V26 - TOTAL DISPONIBLE EN CORDIS WEB: {total_results} resultados ***")
                        else:
                            logger.warning("V26 - Could not extract total count from page, will continue until no more results")
                            total_results = max_results  # Fallback
                
                # Extract result items from HTML
                # Cordis results are in <article> tags with class "result"
                # Each contains a link and title
                
                # Pattern 1: Look for result links
                # <a href="/project/id/12345" class="...">Title Here</a>
                result_pattern = re.compile(
                    r'<a[^>]*href="(/(?:project|result|article|publication)/(?:id|rcn)/(\d+))"[^>]*>([^<]+)</a>',
                    re.IGNORECASE
                )
                
                matches = result_pattern.findall(html)
                
                # Also try to extract from JSON-LD if present
                jsonld_pattern = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>([^<]+)</script>', re.IGNORECASE)
                jsonld_matches = jsonld_pattern.findall(html)
                
                page_results = []
                seen_urls = set()
                
                for match in matches:
                    path, item_id, title = match
                    url = f"https://cordis.europa.eu{path}"
                    
                    # Avoid duplicates within same page
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    # Clean up title
                    title = title.strip()
                    if not title or title in ['...', 'Read more', 'More']:
                        continue
                    
                    page_results.append({
                        'url': url,
                        'title': title,
                        'description': f"Cordis item ID: {item_id}",
                        'source': 'Cordis Europa Web V26',
                        'mediatype': 'project' if 'project' in path else 'result',
                        'lang': 'en'
                    })
                
                # If no results with primary pattern, try alternate patterns
                if not page_results:
                    # Try: <h3 class="card-title">...<a href="...">Title</a></h3>
                    alt_pattern = re.compile(
                        r'class="card-title"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
                        re.IGNORECASE
                    )
                    alt_matches = alt_pattern.findall(html)
                    
                    for url_path, title in alt_matches:
                        if url_path.startswith('/'):
                            url = f"https://cordis.europa.eu{url_path}"
                        else:
                            url = url_path
                        
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)
                        
                        title = title.strip()
                        if title:
                            page_results.append({
                                'url': url,
                                'title': title,
                                'description': "Cordis item",
                                'source': 'Cordis Europa Web V26',
                                'mediatype': 'mixed',
                                'lang': 'en'
                            })
                
                # If still no results, try the most generic pattern
                if not page_results:
                    # Look for any link to project/result pages
                    generic_pattern = re.compile(
                        r'href="(https?://cordis\.europa\.eu/(?:project|result|article)/[^"]+)"[^>]*>([^<]{5,100})</a>',
                        re.IGNORECASE
                    )
                    generic_matches = generic_pattern.findall(html)
                    
                    for url, title in generic_matches:
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)
                        
                        title = title.strip()
                        if title and len(title) > 3:
                            page_results.append({
                                'url': url,
                                'title': title,
                                'description': "Cordis item",
                                'source': 'Cordis Europa Web V26',
                                'mediatype': 'mixed',
                                'lang': 'en'
                            })
                
                if not page_results:
                    logger.info(f"V26 - No more results found on page {page}. Stopping pagination.")
                    break
                
                all_results.extend(page_results)
                logger.info(f"V26 - Page {page}: Found {len(page_results)} results. Total acumulado: {len(all_results)}")
                
                # Check if we've collected all expected results
                if total_results and len(all_results) >= total_results:
                    logger.info(f"V26 - Reached expected total ({total_results}). Stopping.")
                    break
                
                # Check safety limit
                if len(all_results) >= max_results:
                    logger.info(f"V26 - Reached safety limit ({max_results}). Stopping.")
                    break
                
                # Check if this page had fewer results than expected (last page)
                if len(page_results) < results_per_page:
                    logger.info(f"V26 - Last page reached (got {len(page_results)} < {results_per_page}). Stopping.")
                    break
                
                page += 1
                
                # Be nice to the server
                await asyncio.sleep(1.5)
                
            except Exception as e:
                logger.error(f"V26 - Error fetching page {page}: {e}")
                # On error, wait and retry once
                await asyncio.sleep(3)
                try:
                    response = await loop.run_in_executor(None, _fetch_page)
                    if response.status_code != 200:
                        logger.error(f"V26 - Retry failed for page {page}. Stopping.")
                        break
                except:
                    logger.error(f"V26 - Retry also failed. Stopping pagination.")
                    break
        
        logger.info(f"*** V26 COMPLETADO ***: Recopilados {len(all_results)} resultados de Cordis Web")
        return all_results
    
    # Legacy method for compatibility
    async def _execute_sparql_search(self, search_term: str, max_results: int, search_mode: str = 'broad') -> List[Dict[str, Any]]:
        """Deprecated - redirects to web search"""
        return await self.search_projects_and_publications(search_term, search_mode, max_results)

    # =============================================
    # DET API METHODS (kept for API key users)
    # =============================================
    
    async def request_extraction(self, search_term: str) -> Optional[int]:
        """Requests a new extraction from CORDIS DET API."""
        if not self.api_key:
            return None
        try:
            query = f"'{search_term}'"
            create_url = f"{self.DET_BASE_URL}/api/dataextractions/getExtraction"
            params = {
                'query': query,
                'key': self.api_key,
                'outputFormat': 'json',
                'archived': 'true'
            }
            
            loop = asyncio.get_running_loop()
            def _create():
                import requests
                return requests.get(create_url, params=params, headers={'Accept': 'application/json', 'User-Agent': self.headers['User-Agent']}, timeout=30)
            
            response = await loop.run_in_executor(None, _create)
            if response.status_code != 200:
                logger.error(f"DET creation failed ({response.status_code})")
                return None
                
            data = response.json()
            if not data.get('status'):
                return None
                
            task_id = data.get('payload', {}).get('taskID')
            logger.info(f"DET extraction requested: TaskID={task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Error requesting DET extraction: {e}")
            return None

    async def get_extraction_status(self, task_id: int) -> Dict[str, Any]:
        """Checks DET extraction status."""
        if not self.api_key:
            return {'status': 'Failed', 'progress': '0'}
        try:
            status_url = f"{self.DET_BASE_URL}/api/dataextractions/getExtractionStatus"
            loop = asyncio.get_running_loop()
            def _check():
                import requests
                return requests.get(status_url, params={'key': self.api_key, 'taskId': task_id}, timeout=30)
                
            response = await loop.run_in_executor(None, _check)
            if response.status_code != 200:
                return {'status': 'Failed', 'progress': '0'}
                
            data = response.json()
            payload = data.get('payload', {})
            progress = payload.get('progress', '0')
            
            return {
                'status': 'Finished' if progress == '100' else 'Ongoing',
                'progress': progress,
                'file_uri': payload.get('destinationFileUri'),
                'count': payload.get('numberOfRecords', '0')
            }
        except Exception as e:
            logger.error(f"Error checking DET status: {e}")
            return {'status': 'Error', 'progress': '0'}

    async def download_results(self, file_uri: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Downloads DET results."""
        try:
            loop = asyncio.get_running_loop()
            def _download():
                import requests
                return requests.get(file_uri, headers=self.headers, timeout=60)
                
            response = await loop.run_in_executor(None, _download)
            if response.status_code != 200:
                return []
                
            data = response.json()
            items = data if isinstance(data, list) else data.get('results', [])
            
            formatted = []
            for item in items:
                title = item.get('title', 'No Title')
                desc = item.get('objective', item.get('description', ''))
                proj_id = str(item.get('id', item.get('rcn', '')))
                
                formatted.append({
                    'url': f"https://cordis.europa.eu/project/id/{proj_id}" if proj_id else "",
                    'title': title,
                    'description': desc[:1000] if desc else f"Cordis: {title}",
                    'source': 'Cordis Europa DET API',
                    'mediatype': 'project'
                })
                
            return formatted
        except Exception as e:
            logger.error(f"Error downloading results: {e}")
            return []
