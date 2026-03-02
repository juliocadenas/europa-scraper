import logging
import asyncio
import sys
import os
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

# DEBUG FILE for workers
DEBUG_FILE = "/tmp/cordis_debug.log"


def debug_to_file(msg):
    """Write debug message to file (for multiprocess debugging)"""
    with open(DEBUG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{msg}\n")
        f.flush()


# Force DEBUG logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Idiomas oficiales de la UE que CORDIS soporta
EU_LANGUAGES = ["en", "es", "de", "fr", "it", "pl"]

# Log al importar el módulo
logger.critical("V29 - MODULE cordis_api_client.py LOADED")
print("V29 - MODULE cordis_api_client.py LOADED", flush=True, file=sys.stderr)

# Log al importar el módulo
logger.critical("V29 - MODULE cordis_api_client.py LOADED")
print("V29 - MODULE cordis_api_client.py LOADED", flush=True, file=sys.stderr)


class CordisApiClient:
    """
    V29 - SMART MULTI-LANGUAGE VERSION

    Uses the OFFICIAL Cordis JSON endpoint that works:
    https://cordis.europa.eu/search?q=QUERY&format=json&p=PAGE&num=100

    NEW: Detects availableLanguages from API response:
    - If multiple languages available → creates records with /en, /es, etc.
    - If only one language → creates single record without language suffix
    """

    SEARCH_URL = "https://cordis.europa.eu/search"
    DET_API_URL = "https://cordis.europa.eu/dataextractions/api"
    DET_API_KEY = "f1bd9899469be604b0b85dc2eea3438abfd580c7"  # API key para DET
    DET_API_URL = "https://cordis.europa.eu/dataextractions/api"
    DET_API_KEY = "f1bd9899469be604b0b85dc2eea3438abfd580c7"  # API key para DET

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _parse_available_languages(self, available_langs_str: str) -> List[str]:
        """
        Parsea el campo 'availableLanguages' de la API de CORDIS.

        Args:
            available_langs_str: String como "de,en,es,fr,it,pl" o "en"

        Returns:
            Lista de códigos de idioma disponibles
        """
        if not available_langs_str:
            return ["en"]  # Default to English

        # Split by comma and strip whitespace
        langs = [
            lang.strip() for lang in available_langs_str.split(",") if lang.strip()
        ]

        # Filter to only valid EU languages
        valid_langs = [lang for lang in langs if lang in EU_LANGUAGES]

        return valid_langs if valid_langs else ["en"]

    async def check_query_total_hits(self, query_term: str) -> int:
        """
        Obtiene el total de resultados para un término de búsqueda SIN procesarlos.

        Args:
            query_term: Término de búsqueda

        Returns:
            Total de resultados disponibles en CORDIS para este término
        """
        encoded_query = quote_plus(query_term)
        search_url = f"{self.SEARCH_URL}?q={encoded_query}&format=json&p=1&num=1"

        try:
            import requests

            response = requests.get(search_url, headers=self.headers, timeout=30)

            if response.status_code != 200:
                return 0

            data = response.json()
            result_data = data.get("result", {})
            if not isinstance(result_data, dict):
                result_data = {}
            header = (
                result_data.get("header", {}) if isinstance(result_data, dict) else {}
            )

            total_hits_str = header.get("totalHits", "0")
            total_hits = int(total_hits_str) if total_hits_str else 0

            return total_hits

        except Exception as e:
            logger.error(f"DET download error: {e}")
            return []

    async def search_projects_and_publications(
        self,
        query_term: str,
        search_mode: str = "broad",
        max_results: int = 1000000,
        progress_callback=None,
        languages: List[str] = None,
        total_hits_callback=None,
    ) -> List[Dict[str, Any]]:
        """
        V29 - Smart Multi-language version con soporte para grandes volúmenes.

        Si detecta más de 3,000 resultados, divide la búsqueda por años
        para obtener más resultados totales.
        """
        # DEBUG: Verify function is called
        debug_to_file(
            f"FUNCTION CALLED: search_projects_and_publications('{query_term}')"
        )
        logger.critical(
            f"V29 - FUNCTION CALLED: search_projects_and_publications('{query_term}')"
        )

        # Primera búsqueda para obtener total_hits
        encoded_query = quote_plus(query_term)
        search_url = (
            f"{self.SEARCH_URL}?q={encoded_query}&format=json&p=1&num=1&archived=true"
        )

        try:
            import requests

            response = requests.get(search_url, headers=self.headers, timeout=30)
            data = response.json()
            total_hits_str = (
                data.get("result", {}).get("header", {}).get("totalHits", "0")
            )
            total_hits = int(total_hits_str) if total_hits_str else 0

            debug_to_file(f"Total hits for '{query_term}': {total_hits}")

            # Si hay más de 3,000 resultados, usar estrategia de años
            if total_hits > 3000:
                logger.warning(
                    f"V29 - Detectados {total_hits} resultados. Usando estrategia de años."
                )
                return await self._search_by_years(
                    query_term, search_mode, max_results, progress_callback, languages
                )
            else:
                # Usar búsqueda normal
                return await self._search_single(
                    query_term,
                    search_mode,
                    max_results,
                    progress_callback,
                    languages,
                    total_hits_callback,
                )
        except Exception as e:
            debug_to_file(f"Error en búsqueda inicial: {e}")
            # Fallback a búsqueda normal
            return await self._search_single(
                query_term,
                search_mode,
                max_results,
                progress_callback,
                languages,
                total_hits_callback,
            )

    async def _search_single(
        self,
        query_term: str,
        search_mode: str = "broad",
        max_results: int = 1000000,
        progress_callback=None,
        languages: List[str] = None,
        total_hits_callback=None,
    ) -> List[Dict[str, Any]]:
        """Búsqueda simple sin división por años."""
        # Usar el código de búsqueda actual (que está después de este método)
        # Copiar el código de búsqueda existente aquí
        debug_to_file(f"_search_single called for '{query_term}'")

        # Código de búsqueda normal (la parte del while loop)
        encoded_query = quote_plus(query_term)

        if languages is None or (isinstance(languages, list) and len(languages) == 0):
            languages = EU_LANGUAGES

        logger.info(
            f"*** V29 SMART MULTI-LANG ACTIVADA ***: Iniciando búsqueda JSON en Cordis para '{query_term}'"
        )
        logger.info(
            f"*** URL Base: {self.SEARCH_URL}?q={encoded_query}&format=json&archived=true"
        )
        logger.info(f"*** Idiomas seleccionados: {languages} ***")
        logger.info(f"*** Modo: {search_mode} | Max results: {max_results:,} ***")

        all_results = []
        page = 1
        results_per_page = 100
        total_hits = None

        logger.warning(
            f"V29 - 🚀 INICIANDO PAGINACIÓN para '{query_term}' - Esperando {results_per_page} resultados por página"
        )

        debug_to_file(f"=" * 60)
        debug_to_file(f"START: query={query_term}, max_results={max_results}")
        debug_to_file(f"=" * 60)

        while True:
            debug_to_file(
                f"WHILE: page={page}, total_hits={total_hits}, results={len(all_results)}"
            )
            logger.critical(
                f"V29 - 🔄 WHILE LOOP: page={page}, total_hits={total_hits}, results={len(all_results)}"
            )

            search_url = f"{self.SEARCH_URL}?q={encoded_query}&format=json&p={page}&num={results_per_page}&archived=true"
            logger.info(f"V29 - 🔄 Obteniendo página {page}...")

            loop = asyncio.get_running_loop()

            def _fetch():
                import requests

                return requests.get(search_url, headers=self.headers, timeout=90)

            try:
                response = await loop.run_in_executor(None, _fetch)

                if response.status_code != 200:
                    logger.error(
                        f"V29 - Error fetching page {page}: Status {response.status_code}"
                    )
                    break

                try:
                    data = response.json()
                except Exception as e:
                    logger.error(f"V29 - JSON parse error on page {page}: {e}")
                    break

                result_data = data.get("result", {})
                if not isinstance(result_data, dict):
                    result_data = {}
                header = (
                    result_data.get("header", {})
                    if isinstance(result_data, dict)
                    else {}
                )

                if total_hits is None:
                    total_hits_str = header.get("totalHits", "0")
                    total_hits = int(total_hits_str) if total_hits_str else 0
                    logger.info(
                        f"*** V29 - TOTAL EN CORDIS: {total_hits} resultados ***"
                    )

                    if total_hits_callback:
                        total_hits_callback(total_hits)

                    logger.warning(
                        f"V29 - ✅ Callback completado, continuando procesamiento..."
                    )

                    if total_hits == 0:
                        logger.warning("V29 - No results found for this query")
                        break

                hits = []

                logger.warning(
                    f"V29 - DEBUG: Page {page}, data keys: {list(data.keys())}"
                )

                if "hits" in data and isinstance(data["hits"], list):
                    hits = data["hits"]
                    logger.warning(
                        f"V29 - DEBUG: Using Structure 1, hits count: {len(hits)}"
                    )
                elif "hits" in data and isinstance(data["hits"], dict):
                    hits = data["hits"].get("hit", [])
                    debug_to_file(
                        f"DEBUG: data['hits'] keys: {list(data['hits'].keys())}"
                    )
                    debug_to_file(f"DEBUG: data['hits'] content: {data['hits']}")
                    logger.warning(
                        f"V29 - DEBUG: Using Structure 2, hits count: {len(hits) if hits else 0}, data['hits'] keys: {list(data['hits'].keys())}"
                    )
                elif "result" in data and "hits" in data["result"]:
                    result_hits = data["result"]["hits"]
                    if isinstance(result_hits, dict) and "hit" in result_hits:
                        hits = result_hits["hit"]
                    elif isinstance(result_hits, list):
                        hits = result_hits
                    logger.warning(
                        f"V29 - DEBUG: Using Structure 3, hits count: {len(hits) if hits else 0}"
                    )

                if isinstance(hits, dict):
                    hits = [hits]
                elif not isinstance(hits, list):
                    hits = []

                if not hits:
                    logger.warning(
                        f"V29 - Page {page}: Found totalHits={total_hits} but extracted 0 hits."
                    )
                    logger.warning(f"V29 - Root data keys: {list(data.keys())}")
                    if "hits" in data:
                        logger.warning(f"V29 - data['hits'] type: {type(data['hits'])}")
                    break

                page_count = 0
                multi_lang_count = 0
                single_lang_count = 0

                for hit in hits:
                    content = None
                    content_type = "unknown"

                    for ctype in [
                        "article",
                        "project",
                        "result",
                        "publication",
                        "event",
                    ]:
                        if ctype in hit:
                            content = hit[ctype]
                            content_type = ctype
                            break

                    if not content:
                        continue

                    rcn = content.get("rcn", "")
                    title = content.get("title", "No Title")
                    teaser = content.get("teaser", "")
                    available_langs = content.get("availableLanguages", [])
                    primary_lang = content.get("language", "en")

                    if not available_langs:
                        available_langs = [primary_lang]

                    filtered_langs = [
                        lang for lang in available_langs if lang in languages
                    ]

                    if not filtered_langs:
                        filtered_langs = [primary_lang]

                    base_url = f"https://cordis.europa.eu/{content_type}/id/{rcn}"

                    if len(filtered_langs) > 1:
                        multi_lang_count += 1
                        for lang in filtered_langs:
                            all_results.append(
                                {
                                    "url": f"{base_url}/{lang}",
                                    "title": title,
                                    "description": teaser[:1000]
                                    if teaser
                                    else f"Cordis {content_type}: {title}",
                                    "source": "Cordis Europa API V29",
                                    "mediatype": content_type,
                                    "rcn": rcn,
                                    "lang": lang,
                                }
                            )
                            page_count += 1
                    else:
                        single_lang_count += 1
                        all_results.append(
                            {
                                "url": base_url,
                                "title": title,
                                "description": teaser[:1000]
                                if teaser
                                else f"Cordis {content_type}: {title}",
                                "source": "Cordis Europa API V29",
                                "mediatype": content_type,
                                "rcn": rcn,
                                "lang": filtered_langs[0]
                                if filtered_langs
                                else primary_lang,
                            }
                        )
                        page_count += 1

                logger.info(
                    f"═══════════════════════════════════════════════════════════"
                )
                logger.info(
                    f"📄 V29 - Página {page}/{max(1, (total_hits // 100) + 1)} procesada | Hits: {page_count} | Acumulado: {len(all_results)}/{total_hits:,}"
                )
                logger.info(
                    f"    📊 Multi-idioma: {multi_lang_count} | Single-idioma: {single_lang_count}"
                )
                logger.info(
                    f"═══════════════════════════════════════════════════════════"
                )

                try:
                    if progress_callback:
                        progress_callback(
                            0,
                            f"🔄 CORDIS: Página {page} | {len(all_results):,} resultados/{total_hits:,} total",
                            {
                                "page": page,
                                "total_hits": total_hits,
                                "collected": len(all_results),
                            },
                        )
                except Exception as cb_err:
                    logger.warning(
                        f"V29 - Progress callback error (continuando): {cb_err}"
                    )

                if len(all_results) >= max_results:
                    debug_to_file(f"BREAK: Reached max_results={max_results}")
                    logger.warning(
                        f"V29 - 💥 BREAK: Reached safety limit ({max_results}). Stopping."
                    )
                    break

                if page_count == 0:
                    debug_to_file(f"BREAK: page_count=0 on page {page}")
                    debug_to_file(
                        f"DEBUG: hits count was {len(hits)}, data keys: {list(data.keys())}"
                    )
                    if "hits" in data:
                        debug_to_file(f"DEBUG: data['hits'] type: {type(data['hits'])}")
                        if isinstance(data["hits"], list):
                            debug_to_file(
                                f"DEBUG: data['hits'] length: {len(data['hits'])}"
                            )
                    logger.warning(
                        f"V29 - 💥 BREAK: page_count=0, no more results on page {page}. Stopping."
                    )
                    break

                debug_to_file(f"CONTINUE: page={page}, going to page {page + 1}")
                logger.warning(f"V29 - ✅ Continuando a página {page + 1}...")
                logger.info(f"V29 - Avanzando a página {page + 1}...")
                page += 1

                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"V29 - Error on page {page}: {e}")
                page += 1
                if page > 1000:
                    break
                await asyncio.sleep(2.0)
                continue

        logger.info(
            f"*** V29 COMPLETADO ***: Recopilados {len(all_results)} resultados de Cordis"
        )
        return all_results

    async def _search_by_years(
        self,
        query_term: str,
        search_mode: str = "broad",
        max_results: int = 1000000,
        progress_callback=None,
        languages: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """Divide la búsqueda por años para obtener más resultados."""
        debug_to_file(f"_search_by_years called for '{query_term}'")
        logger.warning(f"V29 - Usando estrategia de años para '{query_term}'")

        all_results = []
        years = list(range(2014, 2026))  # 2014-2025

        for year in years:
            year_query = f"{query_term} {year}"
            debug_to_file(f"Searching year {year}: '{year_query}'")
            logger.info(f"V29 - Buscando año {year}: '{year_query}'")

            year_results = await self._search_single(
                year_query,
                search_mode=search_mode,
                max_results=max_results,
                progress_callback=progress_callback,
                languages=languages,
                total_hits_callback=None,
            )

            debug_to_file(f"Year {year}: {len(year_results)} results")
            logger.info(f"V29 - Año {year}: {len(year_results)} resultados")
            all_results.extend(year_results)

            if len(all_results) >= max_results:
                debug_to_file(f"Reached max_results in year loop")
                break

        debug_to_file(f"_search_by_years total: {len(all_results)} results")
        logger.warning(
            f"V29 - Total con estrategia de años: {len(all_results)} resultados"
        )
        return all_results

    # Legacy compatibility
    async def _execute_sparql_search(
        self, search_term: str, max_results: int, search_mode: str = "broad"
    ) -> List[Dict[str, Any]]:
        """Deprecated - redirects to JSON search"""
        return await self.search_projects_and_publications(
            search_term, search_mode, max_results
        )

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
                "query": f"'{search_term}'",
                "key": self.api_key,
                "outputFormat": "json",
                "archived": "true",
            }

            loop = asyncio.get_running_loop()

            def _create():
                import requests

                return requests.get(create_url, params=params, timeout=30)

            response = await loop.run_in_executor(None, _create)
            if response.status_code != 200:
                return None

            data = response.json()
            return data.get("payload", {}).get("taskID")

        except Exception as e:
            logger.error(f"DET error: {e}")
            return None

    async def get_extraction_status(self, task_id: int) -> Dict[str, Any]:
        """Checks DET extraction status."""
        if not self.api_key:
            return {"status": "Failed", "progress": "0"}
        try:
            status_url = (
                "https://cordis.europa.eu/api/dataextractions/getExtractionStatus"
            )
            loop = asyncio.get_running_loop()

            def _check():
                import requests

                return requests.get(
                    status_url,
                    params={"key": self.api_key, "taskId": task_id},
                    timeout=30,
                )

            response = await loop.run_in_executor(None, _check)
            if response.status_code != 200:
                return {"status": "Failed", "progress": "0"}

            data = response.json()
            payload = data.get("payload", {})
            progress = payload.get("progress", "0")

            return {
                "status": "Finished" if progress == "100" else "Ongoing",
                "progress": progress,
                "file_uri": payload.get("destinationFileUri"),
                "count": payload.get("numberOfRecords", "0"),
            }
        except Exception as e:
            logger.error(f"DET status error: {e}")
            return {"status": "Error", "progress": "0"}

    async def download_results(
        self, file_uri: str, max_results: int = 100
    ) -> List[Dict[str, Any]]:
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
            items = data if isinstance(data, list) else data.get("results", [])

            return [
                {
                    "url": f"https://cordis.europa.eu/project/id/{item.get('id', item.get('rcn', ''))}",
                    "title": item.get("title", "No Title"),
                    "description": item.get("objective", "")[:1000],
                    "source": "Cordis DET API",
                    "mediatype": "project",
                }
                for item in items
            ]
        except Exception as e:
            logger.error(f"DET download error: {e}")
            return []
