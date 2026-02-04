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
        
        # Separate metals from other terms
        metals = []
        other_terms = []
        
        for word in words:
            if word in self.translations:
                translated = self.translations[word]
                # Metals should come first
                if translated in ['iron', 'copper', 'aluminum', 'gold', 'silver', 'zinc', 'lead']:
                    metals.append(translated)
                # Then mining/ore/processing terms
                elif translated in ['mining', 'ore', 'metal', 'metals']:
                    other_terms.append(translated)
        
        # Combine: metals first, then other terms (e.g., "iron ore" not "ore iron")
        key_terms = metals + other_terms
        
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
            query_term: The term to search for (in any language).
            max_results: Maximum number of results to return.
            
        Returns:
            A list of dictionaries containing formatted results (url, title, description).
        """
        # First, try searching in the original language (e.g., Spanish)
        logger.info(f"Searching Cordis API with original term: '{query_term}'")
        results = await self._execute_sparql_search(query_term, max_results)
        
        # If no results and term looks like Spanish, try English translation
        if not results and any(word in query_term.lower() for word in ['minería', 'mineral', 'preparación', 'de']):
            english_term = self._translate_to_english(query_term)
            logger.info(f"No results with original term, trying English: '{english_term}'")
            results = await self._execute_sparql_search(english_term, max_results)
        
        logger.info(f"Cordis API returned {len(results)} valid results for '{query_term}'")
        return results
    
    async def _execute_sparql_search(self, search_term: str, max_results: int) -> List[Dict[str, Any]]:
        # Split search term into individual keywords for broader matching
        # "Beryllium ore mining" -> ["beryllium", "mining"] (skip common words like "ore")
        stop_words = {'ore', 'ores', 'mining', 'farms', 'of', 'and', 'the', 'for', 'in', 'to', 'a', 'an'}
        keywords = [word.lower().strip() for word in search_term.split() if len(word) > 2]
        
        # Use the most specific keyword (longest non-stop word) for primary search
        significant_keywords = [k for k in keywords if k not in stop_words]
        
        if not significant_keywords:
            # Fallback: use all keywords if no significant ones
            significant_keywords = keywords[:2]  # Take first 2
        
        # Build FILTER clause with OR for each keyword
        if significant_keywords:
            # Use the primary keyword (most specific/longest)
            primary_keyword = max(significant_keywords, key=len) if significant_keywords else search_term.lower()
        else:
            primary_keyword = search_term.lower()
        
        logger.info(f"SPARQL search: original='{search_term}', primary_keyword='{primary_keyword}'")
        
        sparql_query = f"""
        PREFIX eurio: <http://data.europa.eu/s66#>
        
        SELECT DISTINCT ?title ?url ?description WHERE {{
          {{
            # Search in Projects
            ?project a eurio:Project .
            ?project eurio:title ?title .
            OPTIONAL {{ ?project eurio:description ?description }}
            OPTIONAL {{ ?project eurio:hasWebpage ?url }}
            
            FILTER(CONTAINS(LCASE(STR(?title)), "{primary_keyword}") || 
                   CONTAINS(LCASE(STR(?description)), "{primary_keyword}"))
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
            
            FILTER(CONTAINS(LCASE(STR(?title)), "{primary_keyword}"))
          }}
        }}
        LIMIT {max_results}
        """
        
        logger.info(f"Executing SPARQL query for term: '{primary_keyword}' on {self.SPARQL_ENDPOINT}")
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
                        'url': url if url else f"https://cordis.europa.eu/search?q={search_term}",
                        'title': title,
                        'description': description[:500] if description else f"Cordis project/publication: {title}",
                        'source': 'Cordis Europa API',
                        'mediatype': 'project'
                    })
            
            return formatted_results


        except Exception as e:
            logger.error(f"Error querying Cordis API: {e}")
            return []
