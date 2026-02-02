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
        # Simple translation dictionary for common mining/metal terms
        self.translations = {
            'minería': 'mining',
            'mineral': 'ore',
            'hierro': 'iron',
            'cobre': 'copper',
            'metales': 'metals',
            'metal': 'metal',
            'preparación': 'preparation',
            'procesamiento': 'processing',
            'extracción': 'extraction',
            'aluminio': 'aluminum',
            'oro': 'gold',
            'plata': 'silver',
            'zinc': 'zinc',
            'plomo': 'lead'
        }
    
    def _translate_to_english(self, spanish_term: str) -> str:
        """Extract key technical terms and translate them."""
        words = spanish_term.lower().split()
        # Extract only the important technical terms (metals, minerals, processes)
        key_terms = []
        for word in words:
            if word in self.translations:
                translated = self.translations[word]
                # Only add metals and key nouns, skip generic words
                if translated in ['iron', 'copper', 'metals', 'metal', 'mining', 'ore', 
                                 'aluminum', 'gold', 'silver', 'zinc', 'lead']:
                    key_terms.append(translated)
        
        # If we found key terms, use them; otherwise use first translated word
        if key_terms:
            return ' '.join(key_terms[:2])  # Use max 2 key terms
        else:
            # Fallback: translate all words
            translated_words = [self.translations.get(word, word) for word in words]
            return ' '.join(translated_words[:2])

    async def search_projects_and_publications(self, query_term: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Searches for projects and publications related to the query term using SPARQL.
        
        Args:
            query_term: The term to search for (e.g., "Education").
            max_results: Maximum number of results to return.
            
        Returns:
            A list of dictionaries containing formatted results (url, title, description).
        """
        # Translate Spanish terms to English for better Cordis API results
        english_term = self._translate_to_english(query_term)
        logger.info(f"Translated '{query_term}' to '{english_term}' for Cordis API search")
        
        sparql_query = f"""
        PREFIX eurio: <http://data.europa.eu/s66#>
        
        SELECT DISTINCT ?title ?url ?description WHERE {{
          {{
            # Search in Projects
            ?project a eurio:Project .
            ?project eurio:title ?title .
            OPTIONAL {{ ?project eurio:description ?description }}
            OPTIONAL {{ ?project eurio:hasWebpage ?url }}
            
            FILTER(CONTAINS(LCASE(STR(?title)), "{english_term.lower()}") || 
                   CONTAINS(LCASE(STR(?description)), "{english_term.lower()}"))
          }}
          UNION
          {{
            # Search in Publications
            ?pub a eurio:ProjectPublication .
            ?pub eurio:title ?title .
            OPTIONAL {{ ?pub eurio:hasDownloadURL ?url }}
            OPTIONAL {{ 
                ?pub eurio:hasProject ?proj .
                ?proj eurio:description ?description
            }}
            
            FILTER(CONTAINS(LCASE(STR(?title)), "{english_term.lower()}"))
          }}
        }}
        LIMIT {max_results}
        """
        
        logger.info(f"Executing SPARQL query for term: '{english_term}' on {self.SPARQL_ENDPOINT}")
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
                url = item.get('url', {}).get('value')
                title = item.get('title', {}).get('value', 'No Title')
                description = item.get('description', {}).get('value', '')
                
                # Only include results that have a title
                if title and title != 'No Title':
                    formatted_results.append({
                        'url': url if url else f"https://cordis.europa.eu/search?q={query_term}",
                        'title': title,
                        'description': description[:500] if description else f"Cordis project/publication: {title}",
                        'source': 'Cordis Europa API',
                        'mediatype': 'project'
                    })
            
            logger.info(f"Cordis API returned {len(formatted_results)} valid results for '{query_term}'")
            return formatted_results

        except Exception as e:
            logger.error(f"Error querying Cordis API: {e}")
            return []
