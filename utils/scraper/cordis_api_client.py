import logging
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class CordisApiClient:
    """
    V27 - FINAL VERSION
    
    Uses the OFFICIAL Cordis JSON endpoint that works:
    https://cordis.europa.eu/search?q=QUERY&format=json&p=PAGE&num=100
    
    This returns:
    - totalHits: Total number of results available
    - hits.hit[]: Array of result objects with rcn, id, title, teaser
    """

    SEARCH_URL = "https://cordis.europa.eu/search"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    
    async def search_projects_and_publications(self, query_term: str, search_mode: str = 'broad', max_results: int = 50000) -> List[Dict[str, Any]]:
        """
        V27 - Uses the official Cordis JSON endpoint.
        
        1. First request gets totalHits
        2. Paginates through ALL pages to collect every result
        3. Returns complete list for tabulation
        """
        logger.info(f"*** V27 ACTIVADA ***: Iniciando búsqueda JSON en Cordis para '{query_term}'")
        
        all_results = []
        page = 1
        results_per_page = 100  # Max allowed
        total_hits = None
        
        encoded_query = quote_plus(query_term)
        
        while True:
            # Build URL: https://cordis.europa.eu/search?q=QUERY&format=json&p=PAGE&num=100
            search_url = f"{self.SEARCH_URL}?q={encoded_query}&format=json&p={page}&num={results_per_page}"
            
            logger.info(f"V27 - Fetching page {page}: {search_url}")
            
            loop = asyncio.get_running_loop()
            def _fetch():
                import requests
                return requests.get(search_url, headers=self.headers, timeout=90)
            
            try:
                response = await loop.run_in_executor(None, _fetch)
                
                if response.status_code != 200:
                    logger.error(f"V27 - Error fetching page {page}: Status {response.status_code}")
                    break
                
                try:
                    data = response.json()
                except Exception as e:
                    logger.error(f"V27 - JSON parse error on page {page}: {e}")
                    break
                
                # Extract header info
                header = data.get('result', {}).get('header', {})
                
                # Get total hits from first page
                if total_hits is None:
                    total_hits_str = header.get('totalHits', '0')
                    total_hits = int(total_hits_str) if total_hits_str else 0
                    logger.info(f"*** V27 - TOTAL EN CORDIS: {total_hits} resultados ***")
                    
                    if total_hits == 0:
                        logger.warning("V27 - No results found for this query")
                        break
                
                # Extract hits - Cordis returns them in data['hits'] as a list
                hits = []
                
                # Structure 1 (ACTUAL CORDIS STRUCTURE): data['hits'] direct list
                if 'hits' in data and isinstance(data['hits'], list):
                    hits = data['hits']
                # Structure 2: data['hits'] as dict with 'hit' key
                elif 'hits' in data and isinstance(data['hits'], dict):
                    hits = data['hits'].get('hit', [])
                # Structure 3: result.hits (legacy fallback)
                elif 'result' in data and 'hits' in data['result']:
                    result_hits = data['result']['hits']
                    if isinstance(result_hits, dict) and 'hit' in result_hits:
                        hits = result_hits['hit']
                    elif isinstance(result_hits, list):
                        hits = result_hits
                
                # Ensure hits is a list
                if isinstance(hits, dict):
                    hits = [hits]
                elif not isinstance(hits, list):
                    hits = []
                
                if not hits:
                    logger.warning(f"V27 - Page {page}: Found totalHits={total_hits} but extracted 0 hits.")
                    logger.warning(f"V27 - Root data keys: {list(data.keys())}")
                    if 'hits' in data:
                        logger.warning(f"V27 - data['hits'] type: {type(data['hits'])}")
                    break
                
                page_count = 0
                for hit in hits:
                    # Each hit contains various content types: article, project, result, etc.
                    # We need to extract from whichever is present
                    content = None
                    content_type = 'unknown'
                    
                    # Check for different content types
                    for ctype in ['article', 'project', 'result', 'publication', 'event']:
                        if ctype in hit:
                            content = hit[ctype]
                            content_type = ctype
                            break
                    
                    if not content:
                        continue
                    
                    # Extract fields
                    rcn = content.get('rcn', '')
                    item_id = content.get('id', rcn)
                    title = content.get('title', content.get('acronym', 'No Title'))
                    teaser = content.get('teaser', content.get('objective', ''))
                    
                    # Build URL based on content type
                    if content_type == 'project':
                        url = f"https://cordis.europa.eu/project/id/{item_id}"
                    elif content_type == 'article':
                        url = f"https://cordis.europa.eu/article/id/{item_id}"
                    elif content_type == 'result':
                        url = f"https://cordis.europa.eu/result/id/{item_id}"
                    elif content_type == 'publication':
                        url = f"https://cordis.europa.eu/publication/id/{item_id}"
                    else:
                        url = f"https://cordis.europa.eu/search?q={encoded_query}"
                    
                    # Add to results
                    all_results.append({
                        'url': url,
                        'title': title,
                        'description': teaser[:1000] if teaser else f"Cordis {content_type}: {title}",
                        'source': 'Cordis Europa JSON V27',
                        'mediatype': content_type,
                        'rcn': rcn,
                        'lang': content.get('language', 'en')
                    })
                    page_count += 1
                
                logger.info(f"V27 - Page {page}: Found {page_count} results. Total acumulado: {len(all_results)} de {total_hits}")
                
                # Check if we have collected all expected results
                if len(all_results) >= total_hits:
                    logger.info(f"V27 - Collected all {total_hits} results. Done!")
                    break
                
                # Safety limit
                if len(all_results) >= max_results:
                    logger.info(f"V27 - Reached safety limit ({max_results}). Stopping.")
                    break
                
                # Check if this was the last page (NO results on this page)
                if page_count == 0:
                    logger.info(f"V27 - No more results on page {page}. Stopping.")
                    break
                
                page += 1
                
                # Be nice to server - 0.3 seconds between requests
                await asyncio.sleep(0.3)
                
            except Exception as e:
                logger.error(f"V27 - Error on page {page}: {e}")
                # Try to continue with next page
                page += 1
                if page > 1000:  # Safety: max 1000 pages
                    break
                await asyncio.sleep(2.0)
                continue
        
        logger.info(f"*** V27 COMPLETADO ***: Recopilados {len(all_results)} resultados de Cordis")
        return all_results

    # Legacy compatibility
    async def _execute_sparql_search(self, search_term: str, max_results: int, search_mode: str = 'broad') -> List[Dict[str, Any]]:
        """Deprecated - redirects to JSON search"""
        return await self.search_projects_and_publications(search_term, search_mode, max_results)

    # =============================================
    # DET API METHODS (for API key users)
    # =============================================
    
    async def request_extraction(self, search_term: str) -> Optional[int]:
        """Requests extraction from CORDIS DET API."""
        if not self.api_key:
            return None
        try:
            create_url = f"https://cordis.europa.eu/api/dataextractions/getExtraction"
            params = {
                'query': f"'{search_term}'",
                'key': self.api_key,
                'outputFormat': 'json',
                'archived': 'true'
            }
            
            loop = asyncio.get_running_loop()
            def _create():
                import requests
                return requests.get(create_url, params=params, timeout=30)
            
            response = await loop.run_in_executor(None, _create)
            if response.status_code != 200:
                return None
                
            data = response.json()
            return data.get('payload', {}).get('taskID')
            
        except Exception as e:
            logger.error(f"DET error: {e}")
            return None

    async def get_extraction_status(self, task_id: int) -> Dict[str, Any]:
        """Checks DET extraction status."""
        if not self.api_key:
            return {'status': 'Failed', 'progress': '0'}
        try:
            status_url = "https://cordis.europa.eu/api/dataextractions/getExtractionStatus"
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
            logger.error(f"DET status error: {e}")
            return {'status': 'Error', 'progress': '0'}

    async def download_results(self, file_uri: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Downloads DET results."""
        try:
            loop = asyncio.get_running_loop()
            def _download():
                import requests
                return requests.get(file_uri, timeout=60)
                
            response = await loop.run_in_executor(None, _download)
            if response.status_code != 200:
                return []
                
            data = response.json()
            items = data if isinstance(data, list) else data.get('results', [])
            
            return [{
                'url': f"https://cordis.europa.eu/project/id/{item.get('id', item.get('rcn', ''))}",
                'title': item.get('title', 'No Title'),
                'description': item.get('objective', '')[:1000],
                'source': 'Cordis DET API',
                'mediatype': 'project'
            } for item in items]
        except Exception as e:
            logger.error(f"DET download error: {e}")
            return []
