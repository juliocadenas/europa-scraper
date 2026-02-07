import logging
import asyncio
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CordisApiClient:
    """
    Client for interacting with the Cordis Europa Data Extraction Tool (DET) API.
    
    This API provides access to ALL Cordis data including archived content.
    Documentation: https://cordis.europa.eu/dataextractions/api-docs-ui
    """

    DET_BASE_URL = "https://cordis.europa.eu"
    DET_CREATE_EXTRACTION = "/api/dataextractions/getExtraction"
    DET_GET_STATUS = "/api/dataextractions/getExtractionStatus"
    SPARQL_ENDPOINT = "https://cordis.europa.eu/datalab/sparql"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
    async def request_extraction(self, search_term: str) -> Optional[int]:
        """
        Requests a new extraction from CORDIS. 
        Note: Only ONE extraction can be active at a time per API key.
        """
        if not self.api_key:
            return None
            
        try:
            # Format query for Cordis search syntax
            query = f"'{search_term}'"
            create_url = f"{self.DET_BASE_URL}{self.DET_CREATE_EXTRACTION}"
            params = {
                'query': query,
                'key': self.api_key,
                'outputFormat': 'json',
                'archived': 'true'
            }
            
            loop = asyncio.get_running_loop()
            def _create():
                import requests
                return requests.get(create_url, params=params, headers=self.headers, timeout=30)
            
            response = await loop.run_in_executor(None, _create)
            if response.status_code != 200:
                logger.error(f"DET creation failed ({response.status_code}): {response.text[:200]}")
                return None
                
            data = response.json()
            if not data.get('status'):
                logger.error(f"DET API error response: {data}")
                return None
                
            task_id = data.get('payload', {}).get('taskID')
            logger.info(f"DET extraction requested: TaskID={task_id} for '{search_term}'")
            return task_id
            
        except Exception as e:
            logger.error(f"Error requesting DET extraction: {e}")
            return None

    async def get_extraction_status(self, task_id: int) -> Dict[str, Any]:
        """
        Checks the status of an extraction task.
        Returns a dict with 'progress', 'status' (Finished/Ongoing/Failed), and 'file_uri'.
        """
        if not self.api_key:
            return {'status': 'Failed', 'progress': '0'}
            
        try:
            status_url = f"{self.DET_BASE_URL}{self.DET_GET_STATUS}"
            loop = asyncio.get_running_loop()
            def _check():
                import requests
                return requests.get(status_url, params={'key': self.api_key, 'taskId': task_id}, headers=self.headers, timeout=30)
                
            response = await loop.run_in_executor(None, _check)
            if response.status_code != 200:
                return {'status': 'Failed', 'progress': '0'}
                
            data = response.json()
            payload = data.get('payload', {})
            progress = payload.get('progress', '0')
            
            status = 'Ongoing'
            if progress == '100':
                status = 'Finished'
            elif progress == '-1': # Hypothetical failed status based on common patterns
                status = 'Failed'
                
            return {
                'status': status,
                'progress': progress,
                'file_uri': payload.get('destinationFileUri'),
                'count': payload.get('numberOfRecords', '0')
            }
            
        except Exception as e:
            logger.error(f"Error checking DET status: {e}")
            return {'status': 'Error', 'progress': '0'}

    async def download_results(self, file_uri: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Downloads and parses the JSON result file."""
        try:
            loop = asyncio.get_running_loop()
            def _download():
                import requests
                return requests.get(file_uri, headers=self.headers, timeout=60)
                
            response = await loop.run_in_executor(None, _download)
            if response.status_code != 200:
                logger.error(f"Error downloading file {file_uri}: Status {response.status_code}")
                return []
                
            data = response.json()
            # Handle different payload structures
            # Sometimes it's a list, sometimes {'results': [...]}, sometimes {'payload': {'results': [...]}}
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get('results', data.get('items', data.get('payload', {}).get('results', [])))
            
            logger.info(f"Downloaded JSON contains {len(items)} items")
            
            formatted = []
            # REMOVED slicing [:max_results] to get ALL results
            for item in items:
                title = item.get('title', item.get('acronym', item.get('projectAcronym', 'No Title')))
                desc = item.get('objective', item.get('description', item.get('teaser', '')))
                
                # Robust ID extraction
                proj_id = str(item.get('id', item.get('rcn', item.get('projectID', item.get('projectRcn', '')))))
                
                # If still no ID, use hash of title to ensure uniqueness and avoid 'skipped_duplicates'
                if not proj_id:
                     import hashlib
                     proj_id = hashlib.md5(title.encode()).hexdigest()[:10]
                
                url = f"https://cordis.europa.eu/project/id/{proj_id}"
                
                formatted.append({
                    'url': url,
                    'title': title,
                    'description': desc[:1000] if desc else f"Cordis project: {title}",
                    'source': 'Cordis Europa DET API',
                    'mediatype': 'project'
                })
                
            logger.info(f"Parsed {len(formatted)} formatted results")
            return formatted
            
        except Exception as e:
            logger.error(f"Error downloading results: {e}")
            return []

    # Keeping this for legacy/fallback support
    async def search_projects_and_publications(self, query_term: str, search_mode: str = 'broad', max_results: int = 1000) -> List[Dict[str, Any]]:
        """Fallback to SPARQL if no API key or manual quick search wanted."""
        return await self._execute_sparql_search(query_term, max_results, search_mode)

    async def _execute_sparql_search(self, search_term: str, max_results: int, search_mode: str = 'broad') -> List[Dict[str, Any]]:
        # 1. Preparación de Keywords
        # En modo 'broad' (Vacuum), somos permisivos con stop words para captar más.
        # En modo 'exact', somos más estrictos para reducir ruido.
        if search_mode == 'exact':
            stop_words = {'and', 'the', 'of', 'in', 'for', 'to', 'a', 'an', 'or', 'by', 'with', 'on', 'at', 'from', 'is', 'are'}
        else:
            stop_words = {'and', 'the', 'of', 'in', 'for', 'to', 'a', 'an', 'or', 'by', 'with'}

        keywords = [word.lower().strip() for word in search_term.split() if len(word) > 2]
        significant_keywords = [k for k in keywords if k not in stop_words]
        
        if significant_keywords:
            query_parts = significant_keywords
        else:
            query_parts = [keywords[0]] if keywords else [search_term.lower()]

        # 2. Construcción de Filtros (AND vs OR)
        filter_clauses = []
        
        if search_mode == 'exact':
            # Lógica EXACTA (AND): Todas las partes deben estar presentes
            # Se aplica el filtro iterativamente para que Cummulatively restrinja resultados
            # (FILTER (contains A) && FILTER (contains B))
            pass # Se maneja abajo construyendo un solo string grande con &&
            
            # Para SPARQL, es mejor: (clause1) && (clause2) ...
            temp_clauses = []
            for part in query_parts:
                # Buscamos en título O descripción, pero CADA parte debe estar en uno u otro
                clause = f'(CONTAINS(LCASE(STR(?t)), "{part}") || CONTAINS(LCASE(STR(?d)), "{part}"))'
                temp_clauses.append(clause)
            full_filter = " && ".join(temp_clauses)
            logger.info(f"SPARQL search (EXACT): '{search_term}', AND filter with parts: {query_parts}")

        else:
            # Lógica AMPLIA (OR) - Default / Vacuum Mode
            # Basta con que CUALQUIERA de las partes aparezca
            for part in query_parts:
                clause = f'(CONTAINS(LCASE(STR(?t)), "{part}") || CONTAINS(LCASE(STR(?d)), "{part}"))'
                filter_clauses.append(clause)
            full_filter = " || ".join(filter_clauses)
            logger.info(f"SPARQL search (BROAD): '{search_term}', OR filter with parts: {query_parts}")
        
        
        # 3. SOLUCIÓN: LÍMITE MASIVO.
        sparql_limit = max(2000, max_results * 50) 

        sparql_query = f"""
        PREFIX eurio: <http://data.europa.eu/s66#>
        
        SELECT DISTINCT ?title ?url ?description (LANG(?title) as ?lang) WHERE {{
          {{
            SELECT DISTINCT ?project WHERE {{
               ?project a eurio:Project .
               ?project eurio:title ?t .
               OPTIONAL {{ ?project eurio:description ?d }}
               
               FILTER({full_filter})
            }}
            LIMIT {sparql_limit}
          }}
          
          ?project eurio:title ?title .
          OPTIONAL {{ ?project eurio:description ?description . FILTER(LANG(?description) = LANG(?title)) }}
          OPTIONAL {{ ?project eurio:hasWebpage ?url }}
        }}
        """
        
        loop = asyncio.get_running_loop()
        def _execute_request():
            import requests
            return requests.post(
                self.SPARQL_ENDPOINT, 
                data={'query': sparql_query}, 
                headers={'Accept': 'application/sparql-results+json', **self.headers}, 
                timeout=30
            )

        try:
            response = await loop.run_in_executor(None, _execute_request)
            if response.status_code != 200:
                return []
            
            data = response.json()
            bindings = data.get('results', {}).get('bindings', [])
            
            formatted_results = []
            for item in bindings:
                url = item.get('url', {}).get('value')
                # Extract title and its language
                title_item = item.get('title', {})
                title = title_item.get('value', 'No Title')
                lang = item.get('lang', {}).get('value', 'en') # Default to 'en' if missing
                
                desc = item.get('description', {}).get('value', '')
                
                if title and title != 'No Title':
                    formatted_results.append({
                        'url': url if url else f"https://cordis.europa.eu/search?q={search_term}",
                        'title': title,
                        'description': desc[:500] if desc else "Cordis project",
                        'source': 'Cordis Europa SPARQL',
                        'mediatype': 'project',
                        'lang': lang
                    })
            return formatted_results
        except Exception as e:
            logger.error(f"SPARQL error: {e}")
            return []
