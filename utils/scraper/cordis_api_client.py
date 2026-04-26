import logging
import asyncio
import random
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)
logger.critical("🔔🔔🔔 NUEVO CORDIS CARGADO - callbacks deben funcionar 🔔🔔🔔")

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
    DET_API_URL = "https://cordis.europa.eu/dataextractions/api"
    DET_API_KEY = "f1bd9899469be604b0b85dc2eea3438abfd580c7"  # API key para DET
    DET_API_URL = "https://cordis.europa.eu/dataextractions/api"
    DET_API_KEY = "f1bd9899469be604b0b85dc2eea3438abfd580c7"  # API key para DET

    # Pool de User-Agents para rotación (anti-fingerprinting)
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    ]

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.headers = {
            "Accept": "application/json",
            "User-Agent": random.choice(self.USER_AGENTS),
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
                logger.error(
                    f"[CORDIS] ❌ HTTP {response.status_code} al consultar total hits "
                    f"para '{query_term}'. URL: {search_url}. "
                    f"Respuesta: {response.text[:300]}"
                )
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
        languages: Optional[List[str]] = None,
        total_hits_callback=None,
    ) -> List[Dict[str, Any]]:
        """
        V29 - Smart Multi-language version con soporte para grandes volúmenes.
        """
        # Primera búsqueda para obtener total_hits
        encoded_query = quote_plus(query_term)
        search_url = (
            f"{self.SEARCH_URL}?q={encoded_query}&format=json&p=1&num=1&archived=true"
        )

        try:
            import requests

            response = requests.get(search_url, headers=self.headers, timeout=30)
            data = response.json()
            
            if "payload" in data:
                data = data["payload"]
                
            total_hits_str = (
                data.get("result", {}).get("header", {}).get("totalHits", "0")
            )
            total_hits = int(total_hits_str) if total_hits_str else 0

            # CORDIS permite paginación profunda, por lo que la estrategia de años era redundante
            # y además arruinaba los resultados añadiendo literalmente un string ' 2014' a la query
            logger.info(
                f"[CORDIS] >>> {total_hits} resultados detectados. Usando búsqueda continua paginada. <<<"
            )
            return await self._search_single(
                query_term,
                search_mode,
                max_results,
                progress_callback,
                languages,
                total_hits_callback,
            )
        except Exception as e:
            logger.error(f"Error en búsqueda inicial: {e}")
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
        languages: Optional[List[str]] = None,
        total_hits_callback=None,
    ) -> List[Dict[str, Any]]:
        """Búsqueda simple sin división por años."""
        logger.warning(
            f"[CORDIS _search_single] INICIANDO con term='{query_term}', callback={'YES' if progress_callback else 'NO'}"
        )
        # Usar el código de búsqueda actual (que está después de este método)
        # Copiar el código de búsqueda existente aquí
        # Código de búsqueda normal (la parte del while loop)
        encoded_query = quote_plus(query_term)

        if languages is None or (isinstance(languages, list) and len(languages) == 0):
            languages = EU_LANGUAGES

        logger.info(f"CORDIS: Iniciando búsqueda para '{query_term}'")

        all_results = []
        page = 1
        results_per_page = 100
        total_hits = None

        async def _heartbeat_sleep(duration: float, reason: str):
            """Duerme en incrementos pequeños para poder enviar heartbeats a la GUI."""
            slept = 0.0
            while slept < duration:
                await asyncio.sleep(min(2.0, duration - slept))
                slept += 2.0
                if progress_callback:
                    # Reportar que seguimos vivos y por qué estamos esperando
                    # Forzamos un log temporal usando el parámetro de página como 0
                    progress_callback(0, f"⏳ {reason} ({int(duration - slept)}s restantes)", len(all_results))

        # Stagger inicial aleatorio para no golpear CORDIS los 48 a la vez
        await _heartbeat_sleep(random.uniform(1.0, 15.0), "Stagger inicial")

        while True:
            logger.info(
                f"V29 - Página {page}, total_hits={total_hits}, results={len(all_results)}"
            )

            search_url = f"{self.SEARCH_URL}?q={encoded_query}&format=json&p={page}&num={results_per_page}&archived=true"
            logger.info(f"V29 - 🔄 Obteniendo página {page}...")

            loop = asyncio.get_running_loop()

            def _fetch():
                import requests
                # Rotar User-Agent en cada petición
                req_headers = self.headers.copy()
                req_headers["User-Agent"] = random.choice(self.USER_AGENTS)
                
                # Configurar proxy si está disponible
                proxies = None
                if hasattr(self, 'proxy_manager') and self.proxy_manager:
                    proxy_url = self.proxy_manager.get_proxy()
                    if proxy_url:
                        proxies = {"http": proxy_url, "https": proxy_url}
                        logger.info(f"CORDIS API: Usando proxy {proxy_url} para página {page}")

                logger.info(f"CORDIS API: Petición HTTP GET página {page}")
                
                try:
                    res = requests.get(search_url, headers=req_headers, timeout=20, proxies=proxies)
                    logger.info(f"CORDIS API: HTTP {res.status_code} página {page}")
                    return res
                except requests.exceptions.RequestException as req_err:
                    logger.error(f"CORDIS API: Error de conexión página {page}: {req_err}")
                    raise

            try:
                # Reintentos con backoff exponencial
                max_retries = 5
                retry_delay = 5
                response = None
                has_sem = hasattr(self, 'api_semaphore') and self.api_semaphore is not None

                for attempt in range(max_retries):
                    try:
                        try:
                            response = await asyncio.wait_for(
                                loop.run_in_executor(None, _fetch),
                                timeout=30.0
                            )
                        break  # Éxito, salir del loop de reintentos
                    except (asyncio.TimeoutError, Exception) as fetch_err:
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"CORDIS: ⚠️ Intento {attempt+1}/{max_retries} falló en página {page}: {fetch_err}. "
                                f"Esperando {retry_delay}s antes de reintentar..."
                            )
                            await _heartbeat_sleep(retry_delay, f"Reintentando pág {page}")
                            retry_delay = min(retry_delay * 2, 60)  # Backoff exponencial, máx 60s
                        else:
                            logger.error(
                                f"CORDIS: ❌ Página {page} falló tras {max_retries} intentos. Saltando."
                            )
                            response = None

                if response is None:
                    page += 1
                    if page > (total_hits // results_per_page) + 2 if total_hits else 1000:
                        break
                    continue

                if response.status_code == 429:
                    logger.warning(
                        f"CORDIS: 🔴 RATE LIMITED (429) en página {page}. Esperando 120s..."
                    )
                    await _heartbeat_sleep(120.0, "RATE LIMIT 429")
                    continue

                if response.status_code == 403:
                    logger.error(
                        f"CORDIS: 🚫 BLOQUEADO (403) en página {page}. IP probablemente baneada. Esperando 300s..."
                    )
                    await _heartbeat_sleep(300.0, "BAN 403")
                    continue

                if response.status_code != 200:
                    logger.error(
                        f"CORDIS: Error HTTP {response.status_code} en página {page}. Respuesta: {response.text[:200]}"
                    )
                    break

                try:
                    data = response.json()
                except Exception as e:
                    logger.error(f"V29 - JSON parse error on page {page}: {e}")
                    break

                # Log top-level keys to diagnose structure issues
                top_keys = list(data.keys())
                logger.info(f"[CORDIS PAGE {page}] Top-level keys: {top_keys}")

                # The API sometimes envelops the root keys inside 'payload'
                # IMPORTANT: do NOT unwrap payload if it would lose top-level 'hits'
                if "payload" in data and "hits" not in data:
                    data = data["payload"]
                    logger.info(f"[CORDIS PAGE {page}] Unwrapped payload. New keys: {list(data.keys())}")

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
                    logger.info(f"CORDIS: Total disponible: {total_hits} resultados")

                    if total_hits_callback:
                        total_hits_callback(total_hits)

                    if total_hits == 0:
                        logger.warning(
                            f"CORDIS: totalHits=0 para esta búsqueda. "
                            f"Header completo: {header}. "
                            f"Top-level keys: {list(data.keys())}"
                        )
                        break

                # --- EXTRAER HITS ---
                # Estructura real confirmada: data['hits']['hit'] = [lista de resultados]
                hits = []

                raw_hits = data.get("hits")
                if raw_hits is not None:
                    if isinstance(raw_hits, list):
                        hits = raw_hits
                        logger.info(f"[CORDIS PAGE {page}] hits es lista directa: {len(hits)} items")
                    elif isinstance(raw_hits, dict):
                        hits = raw_hits.get("hit", [])
                        if not isinstance(hits, list):
                            hits = [hits] if hits else []
                        logger.info(f"[CORDIS PAGE {page}] hits['hit']: {len(hits)} items")
                    else:
                        logger.warning(f"[CORDIS PAGE {page}] data['hits'] tipo inesperado: {type(raw_hits)}")
                else:
                    # Fallback: buscar dentro de result
                    if "hits" in result_data:
                        result_hits = result_data["hits"]
                        if isinstance(result_hits, dict) and "hit" in result_hits:
                            hits = result_hits["hit"]
                        elif isinstance(result_hits, list):
                            hits = result_hits
                    logger.warning(f"[CORDIS PAGE {page}] data['hits'] es None. Fallback result_data hits: {len(hits)}")

                if isinstance(hits, dict):
                    hits = [hits]
                elif not isinstance(hits, list):
                    hits = []

                if not hits:
                    logger.error(
                        f"[CORDIS PAGE {page}] ❌ HITS VACÍO a pesar de totalHits={total_hits}. "
                        f"data keys={list(data.keys())}. raw_hits type={type(raw_hits)}"
                    )

                # LOG cada 10 páginas, pero callback de progreso cada 5 páginas
                current_results = len(all_results)
                progress_pct = (
                    min(100, int((current_results / total_hits) * 100))
                    if total_hits > 0
                    else 0
                )

                # Callback de progreso cada 5 páginas (más dinámico para UI)
                logger.info(
                    f"[CORDIS CALL] page={page}, callback={'YES' if progress_callback else 'NO'}, mod5={page % 5}"
                )
                if progress_callback and (page % 5 == 0):
                    logger.info(f"[CORDIS CALL] 🔥 CALLING CALLBACK page={page}")
                    progress_callback(page, total_hits, current_results)

                # Log cada 10 páginas (conservador)
                if page % 10 == 0:
                    logger.info(
                        f"[CORDIS PROGRESS] Página {page} | {len(hits)} hits esta página | Total recolectado: {current_results}/{total_hits} ({progress_pct}%)"
                    )

                if not hits:
                    logger.warning(f"CORDIS: Página {page} sin resultados, deteniendo.")
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
                    f"CORDIS: Página {page} procesada | {page_count} hits | Total: {len(all_results)}/{total_hits:,}"
                )

                try:
                    if progress_callback:
                        logger.info(f"[CORDIS] 🔥 LLAMANDO callback en página {page}")
                        progress_callback(
                            page,
                            total_hits,
                            len(all_results),
                        )
                except Exception as cb_err:
                    logger.warning(f"Progress callback error: {cb_err}")

                if len(all_results) >= max_results:
                    logger.warning(
                        f"CORDIS: Límite alcanzado ({max_results}), deteniendo."
                    )
                    break

                if page_count == 0:
                    logger.info(f"CORDIS: Fin de resultados en página {page}")
                    break

                page += 1

                # DELAY HUMANO ALEATORIO entre páginas (5s - 8s)
                # Aumentado para soportar múltiples workers sin proxies
                delay = random.uniform(5.0, 8.0)
                await _heartbeat_sleep(delay, "Pausa humana")

            except Exception as e:
                logger.error(f"CORDIS: Error en página {page}: {e}")
                page += 1
                if page > 1000:
                    break
                await _heartbeat_sleep(10.0, "Recuperación de error")
                continue

        logger.info(
            f"CORDIS: Búsqueda completada. Total: {len(all_results)} resultados"
        )
        return all_results

    async def _search_by_years(
        self,
        query_term: str,
        search_mode: str = "broad",
        max_results: int = 1000000,
        progress_callback=None,
        languages: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Divide la búsqueda por años para obtener más resultados."""
        logger.info(f"CORDIS: Usando estrategia de años para '{query_term}'")

        all_results = []
        years = list(range(2014, 2026))

        cumulative_results = 0

        def year_progress_wrapper(page, total_hits, collected):
            """Wrapper que suma el progreso de todos los años"""
            nonlocal cumulative_results
            cumulative_results = max(cumulative_results, collected)
            if progress_callback:
                progress_callback(page, total_hits, cumulative_results)

        for year in years:
            year_query = f"{query_term} {year}"
            logger.info(f"[CORDIS AÑO {year}] Iniciando búsqueda: '{year_query}'")

            year_results = await self._search_single(
                year_query,
                search_mode=search_mode,
                max_results=max_results,
                progress_callback=year_progress_wrapper,
                languages=languages,
                total_hits_callback=None,
            )

            logger.info(
                f"[CORDIS AÑO {year}] COMPLETADO: {len(year_results)} resultados | Acumulado total: {cumulative_results}"
            )
            all_results.extend(year_results)

            if cumulative_results >= max_results:
                logger.info(f"[CORDIS] Límite de {max_results} alcanzado. Deteniendo.")
                break

        logger.info(
            f"[CORDIS] ESTRATEGIA DE AÑOS COMPLETADA: {len(all_results)} resultados totales"
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
