import logging
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

# Force DEBUG logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Idiomas oficiales de la UE que CORDIS soporta
EU_LANGUAGES = ["en", "es", "de", "fr", "it", "pl"]


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
            logger.error(f"Error checking total hits for '{query_term}': {e}")
            return 0

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
        V29 - Smart Multi-language version.

        1. First request gets totalHits
        2. Paginates through ALL pages to collect every result
        3. For each result, checks 'availableLanguages' field:
           - If multiple languages → creates records with /en, /es, etc.
           - If only one language → creates single record without suffix
        4. Returns complete list for tabulation

        Args:
            query_term: Término de búsqueda
            search_mode: Modo de búsqueda ('broad' o 'exact')
            max_results: Número máximo de resultados
            progress_callback: Callback para reportar progreso
            languages: Lista de idiomas a incluir (ej: ['en', 'es', 'de']).
                      Si es None, incluye todos los idiomas disponibles.
        """
        # Si no se especifican idiomas o está vacía, usar todos los disponibles
        if languages is None or (isinstance(languages, list) and len(languages) == 0):
            languages = EU_LANGUAGES

        # Preparar query antes del log
        encoded_query = quote_plus(query_term)

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
        results_per_page = 100  # Max allowed
        total_hits = None

        logger.warning(
            f"V29 - 🚀 INICIANDO PAGINACIÓN para '{query_term}' - Esperando {results_per_page} resultados por página"
        )

        while True:
            # Build URL: https://cordis.europa.eu/search?q=QUERY&format=json&p=PAGE&num=100
            # Incluir archived=true para buscar también contenido archivado
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

                # Extract header info - handle case where 'result' might not be a dict
                result_data = data.get("result", {})
                if not isinstance(result_data, dict):
                    result_data = {}
                header = (
                    result_data.get("header", {})
                    if isinstance(result_data, dict)
                    else {}
                )

                # Get total hits from first page
                if total_hits is None:
                    total_hits_str = header.get("totalHits", "0")
                    total_hits = int(total_hits_str) if total_hits_str else 0
                    logger.info(
                        f"*** V29 - TOTAL EN CORDIS: {total_hits} resultados ***"
                    )

                    # Notificar al callback si existe
                    if total_hits_callback:
                        total_hits_callback(total_hits)

                    logger.warning(
                        f"V29 - ✅ Callback completado, continuando procesamiento..."
                    )

                    if total_hits == 0:
                        logger.warning("V29 - No results found for this query")
                        break

                # Extract hits - Cordis returns them in data['hits'] as a list
                hits = []

                # DEBUG: Log data structure
                logger.warning(
                    f"V29 - DEBUG: Page {page}, data keys: {list(data.keys())}"
                )

                # Structure 1 (ACTUAL CORDIS STRUCTURE): data['hits'] direct list
                if "hits" in data and isinstance(data["hits"], list):
                    hits = data["hits"]
                    logger.warning(
                        f"V29 - DEBUG: Using Structure 1, hits count: {len(hits)}"
                    )
                # Structure 2: data['hits'] as dict with 'hit' key
                elif "hits" in data and isinstance(data["hits"], dict):
                    hits = data["hits"].get("hit", [])
                    logger.warning(
                        f"V29 - DEBUG: Using Structure 2, hits count: {len(hits) if hits else 0}"
                    )
                # Structure 3: result.hits (legacy fallback)
                elif "result" in data and "hits" in data["result"]:
                    result_hits = data["result"]["hits"]
                    if isinstance(result_hits, dict) and "hit" in result_hits:
                        hits = result_hits["hit"]
                    elif isinstance(result_hits, list):
                        hits = result_hits
                    logger.warning(
                        f"V29 - DEBUG: Using Structure 3, hits count: {len(hits) if hits else 0}"
                    )

                # Ensure hits is a list
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
                    # Each hit contains various content types: article, project, result, etc.
                    # We need to extract from whichever is present
                    content = None
                    content_type = "unknown"

                    # Check for different content types
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

                    # Extract fields
                    rcn = content.get("rcn", "")
                    item_id = content.get("id", rcn)
                    title = content.get("title", content.get("acronym", "No Title"))
                    teaser = content.get("teaser", content.get("objective", ""))

                    # V29: Detectar idiomas disponibles desde la API
                    available_langs_str = content.get("availableLanguages", "")
                    primary_lang = content.get("language", "en")

                    # Parsear idiomas disponibles
                    available_langs = self._parse_available_languages(
                        available_langs_str
                    )

                    # Build base URL based on content type (without language suffix)
                    if content_type == "project":
                        base_url = f"https://cordis.europa.eu/project/id/{item_id}"
                    elif content_type == "article":
                        base_url = f"https://cordis.europa.eu/article/id/{item_id}"
                    elif content_type == "result":
                        base_url = f"https://cordis.europa.eu/result/id/{item_id}"
                    elif content_type == "publication":
                        base_url = f"https://cordis.europa.eu/publication/id/{item_id}"
                    else:
                        base_url = f"https://cordis.europa.eu/search?q={encoded_query}"

                    # V29: Lógica inteligente de idiomas con FILTRADO por languages seleccionados
                    # Filtrar idiomas disponibles para incluir solo los seleccionados por el usuario
                    filtered_langs = [
                        lang for lang in available_langs if lang in languages
                    ]

                    # Si ningún idioma está en la selección del usuario, saltar este resultado
                    if not filtered_langs:
                        continue

                    if len(filtered_langs) > 1:
                        # Múltiples idiomas disponibles → crear registro por cada idioma seleccionado
                        multi_lang_count += 1
                        for lang in filtered_langs:
                            # URL with language suffix
                            url_with_lang = f"{base_url}/{lang}"

                            all_results.append(
                                {
                                    "url": url_with_lang,
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
                        # Solo un idioma → crear un solo registro SIN sufijo de idioma
                        single_lang_count += 1
                        all_results.append(
                            {
                                "url": base_url,  # Sin sufijo de idioma
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

                # Emitir evento para GUI SI el callback no causa errores
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

                # Safety limit
                if len(all_results) >= max_results:
                    logger.info(
                        f"V29 - Reached safety limit ({max_results}). Stopping."
                    )
                    break

                # Check if this was the last page (NO results on this page)
                if page_count == 0:
                    logger.info(f"V29 - No more results on page {page}. Stopping.")
                    break

                logger.info(f"V29 - Avanzando a página {page + 1}...")
                page += 1

                # Be nice to server - 0.1 seconds between requests (reducido para mayor velocidad)
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"V29 - Error on page {page}: {e}")
                # Try to continue with next page
                page += 1
                if page > 1000:  # Safety: max 1000 pages
                    break
                await asyncio.sleep(2.0)
                continue

        logger.info(
            f"*** V29 COMPLETADO ***: Recopilados {len(all_results)} resultados de Cordis"
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
