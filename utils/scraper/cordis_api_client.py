import logging
import aiohttp
import asyncio
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CordisApiClient:
    """
    Client for interacting with the Cordis Europa Data Extraction Tool (DET) API.
    
    This API provides access to ALL Cordis data including archived content,
    unlike the SPARQL endpoint which has limited data.
    
    API Documentation: https://cordis.europa.eu/dataextractions/api-docs-ui
    """

    # DET API endpoints
    DET_BASE_URL = "https://cordis.europa.eu"
    DET_CREATE_EXTRACTION = "/api/dataextractions/getExtraction"
    DET_GET_STATUS = "/api/dataextractions/getExtractionStatus"
    
    # Fallback SPARQL endpoint (limited data, but no API key required)
    SPARQL_ENDPOINT = "https://cordis.europa.eu/datalab/sparql"
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Cordis API client.
        
        Args:
            api_key: Optional API key for DET API. If not provided, falls back to SPARQL.
        """
        self.api_key = api_key
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
    async def search_projects_and_publications(self, query_term: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Searches for projects and publications related to the query term.
        
        Uses DET API if API key is available, otherwise falls back to SPARQL.
        
        Args:
            query_term: The term to search for.
            max_results: Maximum number of results to return.
            
        Returns:
            A list of dictionaries containing formatted results (url, title, description).
        """
        # Try DET API first if we have an API key
        if self.api_key:
            logger.info(f"Using DET API with archived=true for '{query_term}'")
            results = await self._search_with_det_api(query_term, max_results)
            if results:
                return results
            logger.warning("DET API returned no results, falling back to SPARQL")
        
        # Fallback to SPARQL (limited data but no API key required)
        logger.info(f"Using SPARQL endpoint for '{query_term}'")
        return await self._execute_sparql_search(query_term, max_results)
    
    async def _search_with_det_api(self, search_term: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search using the DET API which includes ALL archived content.
        
        The DET API works asynchronously:
        1. Create extraction task with getExtraction
        2. Poll getExtractionStatus until complete
        3. Download results from destinationFileUri
        """
        try:
            # Format query for Cordis search syntax
            query = f"'{search_term}'"
            
            # Step 1: Create extraction task
            create_url = f"{self.DET_BASE_URL}{self.DET_CREATE_EXTRACTION}"
            params = {
                'query': query,
                'key': self.api_key,
                'outputFormat': 'json',
                'archived': 'true'  # CRITICAL: Include archived content!
            }
            
            loop = asyncio.get_running_loop()
            
            def _create_extraction():
                import requests
                return requests.get(create_url, params=params, headers=self.headers, timeout=30)
            
            response = await loop.run_in_executor(None, _create_extraction)
            
            if response.status_code != 200:
                logger.error(f"DET API create extraction failed: {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")
                return []
            
            data = response.json()
            if not data.get('status'):
                logger.error(f"DET API returned error: {data}")
                return []
            
            task_id = data.get('payload', {}).get('taskID')
            if not task_id:
                logger.error(f"DET API did not return taskID: {data}")
                return []
            
            logger.info(f"DET extraction task created: {task_id}")
            
            # Step 2: Poll for completion
            status_url = f"{self.DET_BASE_URL}{self.DET_GET_STATUS}"
            max_wait_time = 60  # seconds
            poll_interval = 2  # seconds
            elapsed = 0
            
            while elapsed < max_wait_time:
                def _get_status():
                    import requests
                    return requests.get(status_url, params={'key': self.api_key, 'taskId': task_id}, headers=self.headers, timeout=30)
                
                status_response = await loop.run_in_executor(None, _get_status)
                
                if status_response.status_code != 200:
                    logger.error(f"DET API status check failed: {status_response.status_code}")
                    break
                
                status_data = status_response.json()
                payload = status_data.get('payload', {})
                progress = payload.get('progress', '')
                
                logger.info(f"DET extraction progress: {progress}")
                
                if progress == '100':
                    # Extraction complete - download results
                    file_uri = payload.get('destinationFileUri')
                    if file_uri:
                        return await self._download_det_results(file_uri, max_results)
                    break
                
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
            
            logger.warning(f"DET extraction timed out or failed")
            return []
            
        except Exception as e:
            logger.error(f"DET API error: {e}")
            return []
    
    async def _download_det_results(self, file_uri: str, max_results: int) -> List[Dict[str, Any]]:
        """Download and parse results from DET extraction."""
        try:
            loop = asyncio.get_running_loop()
            
            def _download():
                import requests
                return requests.get(file_uri, headers=self.headers, timeout=60)
            
            response = await loop.run_in_executor(None, _download)
            
            if response.status_code != 200:
                logger.error(f"Failed to download DET results: {response.status_code}")
                return []
            
            data = response.json()
            
            # Parse JSON results into our format
            formatted_results = []
            items = data if isinstance(data, list) else data.get('results', data.get('items', []))
            
            for item in items[:max_results]:
                title = item.get('title', item.get('acronym', 'No Title'))
                description = item.get('objective', item.get('description', ''))
                url = item.get('url', item.get('id', ''))
                
                # Build Cordis URL if only ID provided
                if url and not url.startswith('http'):
                    url = f"https://cordis.europa.eu/project/id/{url}"
                
                if title and title != 'No Title':
                    formatted_results.append({
                        'url': url,
                        'title': title,
                        'description': description[:500] if description else f"Cordis project: {title}",
                        'source': 'Cordis Europa DET API',
                        'mediatype': 'project'
                    })
            
            logger.info(f"DET API returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error downloading DET results: {e}")
            return []
    
    async def _execute_sparql_search(self, search_term: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Fallback SPARQL search (limited data but no API key required).
        """
        # Extract primary keyword for broader matching
        stop_words = {'ore', 'ores', 'mining', 'farms', 'of', 'and', 'the', 'for', 'in', 'to', 'a', 'an', 'production', 'crops'}
        keywords = [word.lower().strip() for word in search_term.split() if len(word) > 2]
        significant_keywords = [k for k in keywords if k not in stop_words]
        
        if significant_keywords:
            primary_keyword = max(significant_keywords, key=len)
        else:
            primary_keyword = keywords[0] if keywords else search_term.lower()
        
        logger.info(f"SPARQL search: original='{search_term}', primary_keyword='{primary_keyword}'")
        
        sparql_query = f"""
        PREFIX eurio: <http://data.europa.eu/s66#>
        
        SELECT DISTINCT ?title ?url ?description WHERE {{
          {{
            ?project a eurio:Project .
            ?project eurio:title ?title .
            OPTIONAL {{ ?project eurio:description ?description }}
            OPTIONAL {{ ?project eurio:hasWebpage ?url }}
            
            FILTER(CONTAINS(LCASE(STR(?title)), "{primary_keyword}") || 
                   CONTAINS(LCASE(STR(?description)), "{primary_keyword}"))
          }}
          UNION
          {{
            ?pub a eurio:ProjectPublication .
            ?pub eurio:title ?title .
            OPTIONAL {{ ?pub eurio:hasDownloadURL ?url }}
            OPTIONAL {{ 
                ?pub eurio:hasProject ?proj .
                ?proj eurio:description ?description
            }}
            
            FILTER(CONTAINS(LCASE(STR(?title)), "{primary_keyword}"))
          }}
        }}
        LIMIT {max_results}
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
                logger.error(f"SPARQL returned status {response.status_code}")
                return []
            
            data = response.json()
            bindings = data.get('results', {}).get('bindings', [])
            
            formatted_results = []
            for item in bindings:
                url = item.get('url', {}).get('value')
                title = item.get('title', {}).get('value', 'No Title')
                description = item.get('description', {}).get('value', '')
                
                if title and title != 'No Title':
                    formatted_results.append({
                        'url': url if url else f"https://cordis.europa.eu/search?q={search_term}",
                        'title': title,
                        'description': description[:500] if description else f"Cordis project: {title}",
                        'source': 'Cordis Europa SPARQL',
                        'mediatype': 'project'
                    })
            
            logger.info(f"SPARQL returned {len(formatted_results)} results (limited dataset)")
            return formatted_results

        except Exception as e:
            logger.error(f"SPARQL error: {e}")
            return []
