import logging
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CordisApiClient:
    """
    Client for interacting with the Cordis Europa SPARQL API.
    """

    SPARQL_ENDPOINT = "https://cordis.europa.eu/datalab/sparql"
    
    def __init__(self):
        self.headers = {
            'Accept': 'application/sparql-results+json, application/json, text/javascript',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    async def search_projects_and_publications(self, query_term: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Searches for projects and publications related to the query term using SPARQL.
        
        Args:
            query_term: The term to search for (e.g., "Education").
            max_results: Maximum number of results to return.
            
        Returns:
            A list of dictionaries containing formatted results (url, title, description).
        """
        sparql_query = f"""
        PREFIX eurio: <http://data.europa.eu/s66#>
        
        SELECT ?pubTitle ?pubUrl ?projectTitle ?projectDesc WHERE {{
          ?pub a eurio:ProjectPublication .
          ?pub eurio:title ?pubTitle .
          
          OPTIONAL {{ ?pub eurio:hasDownloadURL ?pubUrl }}
          
          OPTIONAL {{ 
              ?pub eurio:hasProject ?proj .
              ?proj eurio:title ?projectTitle .
              OPTIONAL {{ ?proj eurio:description ?projectDesc }}
          }}
          
          FILTER(CONTAINS(LCASE(STR(?pubTitle)), "{query_term.lower()}"))
        }}
        LIMIT {max_results}
        """
        
        logger.info(f"Executing SPARQL query for term: '{query_term}' on {self.SPARQL_ENDPOINT}")
        logger.debug(f"Query payload: {sparql_query}")
        
        # Use requests via executor to avoid blocking and ensure compatibility
        # (aiohttp was having issues with this specific endpoint)
        loop = asyncio.get_running_loop()
        
        def _execute_request():
            import requests
            return requests.post(
                self.SPARQL_ENDPOINT, 
                data={'query': sparql_query}, 
                headers=self.headers, 
                timeout=30
            )

        try:
            response = await loop.run_in_executor(None, _execute_request)
            
            if response.status_code != 200:
                logger.error(f"Cordis API returned status {response.status_code}")
                return []
            
            data = response.json()
            bindings = data.get('results', {}).get('bindings', [])
            
            formatted_results = []
            for item in bindings:
                pub_url = item.get('pubUrl', {}).get('value')
                pub_title = item.get('pubTitle', {}).get('value', 'No Title')
                project_title = item.get('projectTitle', {}).get('value', '')
                project_desc = item.get('projectDesc', {}).get('value', '')
                
                # Only include results that have a download URL or some substantial info
                if pub_url or pub_title:
                        formatted_results.append({
                        'url': pub_url if pub_url else f"cordis://{pub_title}", # Fallback URL
                        'title': pub_title,
                        'description': f"Project: {project_title}. {project_desc[:200]}...",
                        'source': 'Cordis Europa API',
                        'mediatype': 'publication'
                    })
            
            logger.info(f"Cordis API returned {len(formatted_results)} valid results for '{query_term}'")
            return formatted_results

        except Exception as e:
            logger.error(f"Error querying Cordis API: {e}")
            return []
