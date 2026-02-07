
import os

def create_manual_server_update_script():
    # --- CONTENIDO DE CORDIS API CLIENT CON OR LOGIC ---
    cordis_code = r'''import logging
import asyncio
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CordisApiClient:
    SPARQL_ENDPOINT = "https://cordis.europa.eu/datalab/sparql"
    
    def __init__(self, api_key: str = None):
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }

    async def search_projects_and_publications(self, query_term: str, max_results: int = 1000) -> List[Dict[str, Any]]:
        return await self._execute_sparql_search(query_term, max_results)

    async def _execute_sparql_search(self, search_term: str, max_results: int) -> List[Dict[str, Any]]:
        # 1. SOLUCIÓN: Limpiar STOP WORDS agresivo. Dejamos que busque TODO menos conectores.
        stop_words = {'and', 'the', 'of', 'in', 'for', 'to', 'a', 'an', 'or', 'by', 'with'}
        keywords = [word.lower().strip() for word in search_term.split() if len(word) > 2]
        significant_keywords = [k for k in keywords if k not in stop_words]
        
        if significant_keywords:
            query_parts = significant_keywords
        else:
            query_parts = [keywords[0]] if keywords else [search_term.lower()]

        # 2. SOLUCIÓN: CAMBIO LOGICA A "OR" (||). 
        # Si dice "AGRICULTURAL PRODUCTION", traerá todo lo de "AGRICULTURAL" más todo lo de "PRODUCTION".
        filter_clauses = []
        for part in query_parts:
            # Buscamos coincidencias flexibles
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
                timeout=60
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
                title = item.get('title', {}).get('value', 'No Title')
                lang = item.get('lang', {}).get('value', 'en')
                description = item.get('description', {}).get('value', '')
                
                if title and title != 'No Title':
                    formatted_results.append({
                        'url': url if url else f"https://cordis.europa.eu/search?q={search_term}",
                        'title': title,
                        'description': description[:500] if description else "Cordis project",
                        'source': 'Cordis Europa SPARQL',
                        'mediatype': 'project',
                        'lang': lang
                    })
            logger.info(f"SPARQL returned {len(formatted_results)} results (BROAD SEARCH)")
            return formatted_results
        except Exception as e:
            logger.error(f"SPARQL error: {e}")
            return []
'''

    # --- SCRIPT DE PARCHEO ---
    script_content = "#!/bin/bash\n\n"
    script_content += "echo '🔥 Starting HOTFIX update (Vacuum Mode)...'\n\n"
    
    # Escribir CordisApiClient
    script_content += "echo '📝 Updating cordis_api_client.py (OR Logic)...'\n"
    script_content += f"sudo tee /opt/docuscraper/utils/scraper/cordis_api_client.py > /dev/null << 'EOF_CORDIS'\n{cordis_code}\nEOF_CORDIS\n\n"

    # Parchear ScraperController usando sed para ser menos destructivos pero efectivos
    # Buscamos la lógica de exclusión y la anulamos o reemplazamos.
    # Dado que es complejo parchear python con sed, vamos a inyectar un "monkey patch" simple si no podemos reemplazar todo.
    # Pero mejor aún: vamos a usar sed para comentar las líneas problematicas.
    
    script_content += "echo '📝 Updating scraper_controller.py (Removing Strict Filters)...'\n"
    # Comentar la llamada a should_exclude_result y el if successivo
    # Usamos sed para reemplazar el bloque especifico.
    # Buscamos: should_exclude, exclude_reason = self.text_processor.should_exclude_result
    # Reemplamos por: should_exclude, exclude_reason = (False, "") # VACUUM MODE FORCE
    
    script_content += "sudo sed -i 's/should_exclude, exclude_reason = self.text_processor.should_exclude_result.*/should_exclude, exclude_reason = (False, \"\") # VACUUM MODE FORCE/g' /opt/docuscraper/controllers/scraper_controller.py\n"
    
    # También forzamos el chequeo de min_words manual si queremos, pero al poner False arriba, pasará todo.
    # El usuario dijo: "ese numero de palabras me va a definir si ese documento va a estar en results"
    # Así que debemos asegurarnos de que el conteo de palabras AÚN funcione.
    # Mierda, si pongo False, ignora min_words. Tengo que ser mas inteligente.
    
    # Reemplazo inteligente:
    # should_exclude... -> should_exclude = total_words < min_words; exclude_reason = f"Low words: {total_words}" if should_exclude else ""
    script_content += "sudo sed -i 's/should_exclude, exclude_reason = self.text_processor.should_exclude_result.*/should_exclude = total_words < min_words; exclude_reason = f\"Low words: {total_words}\" if should_exclude else \"\"/g' /opt/docuscraper/controllers/scraper_controller.py\n"

    # Eliminar el bloque de "skipped_zero_keywords" posterior
    # formatted_word_counts.startswith... -> if False:
    script_content += "sudo sed -i 's/if formatted_word_counts.startswith.*:/if False: # VACUUM MODE/g' /opt/docuscraper/controllers/scraper_controller.py\n"
    
    script_content += "\n"
    script_content += "echo '🐳 Rebuilding Docker...'\n"
    script_content += "sudo docker compose down\n"
    script_content += "sudo docker compose up --build -d\n"
    script_content += "echo '✅ Update Complete! TRY NOW.'\n"

    with open("manual_server_update.sh", "w", encoding="utf-8") as f:
        f.write(script_content)
    
    print("✅ Created manual_server_update.sh with embedded code fixes.")

if __name__ == "__main__":
    create_manual_server_update_script()
