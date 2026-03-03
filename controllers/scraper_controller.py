"""
Scraper Controller
-----------------
Controlador principal para la aplicación de scraping.
"""

import asyncio
import logging
import os
import time
import random
from typing import List, Dict, Tuple, Optional, Any, Callable
from datetime import datetime
import re
import traceback
import gc
import requests  # Added for Wayback Machine API calls

from controllers.scraper_controller_base import ScraperControllerBase
from utils.sqlite_handler import SQLiteHandler
from utils.scraper.browser_manager import BrowserManager
from utils.scraper.search_engine import SearchEngine
from utils.scraper.content_extractor import ContentExtractor
from utils.scraper.text_processor import TextProcessor
from utils.scraper.result_manager import ResultManager
from utils.scraper.progress_reporter import ProgressReporter
from utils.scraper.url_utils import URLUtils
from utils.scraper.search_engine import ManualCaptchaPendingError
from utils.scraper.cordis_api_client import CordisApiClient

logger = logging.getLogger(__name__)

from utils.config import Config


class ScraperController(ScraperControllerBase):
    """
    Controlador principal para la aplicación de scraping de USA.gov.
    Gestiona el flujo de trabajo de scraping y procesa resultados.
    """

    def __init__(
        self,
        config_manager: Config,
        browser_manager: BrowserManager,
        proxy_manager=None,
    ):
        """Inicializa el controlador de scraping."""
        super().__init__()

        # Inicializar el logger específico para esta instancia
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        self.config = config_manager
        # Use the provided browser_manager instance
        self.browser_manager = browser_manager
        self.text_processor = TextProcessor()
        self.search_engine = SearchEngine(
            self.browser_manager, self.text_processor, self.config
        )
        self.content_extractor = ContentExtractor(self.browser_manager)
        self.result_manager = ResultManager()
        self.progress_reporter = ProgressReporter()
        self.url_utils = URLUtils()
        self.cordis_api_client = CordisApiClient()
        # Usar la base de datos SQLite en lugar del CSV
        from utils.sqlite_handler import SQLiteHandler

        db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "courses.db"
        )
        self.csv_handler = SQLiteHandler(db_path=db_path)

        # NO establecer el proxy manager por defecto - debe ser explícito
        self.proxy_manager = None

        # Inicializar estado
        self.processed_records = set()  # Usar un conjunto para rastrear registros completos (sic_code, course_name, url)
        self.stats = {
            "total_urls_found": 0,
            "files_saved": 0,
            "files_not_saved": 0,
            "skipped_duplicates": 0,
            "skipped_low_words": 0,
            "skipped_zero_keywords": 0,
            "failed_content_extraction": 0,
            "total_errors": 0,
        }
        self.stop_requested = False
        self._is_paused = asyncio.Event()
        self._is_paused.set()

        # Callback para eventos de auditoría (inyectado por el worker)
        self.event_callback = None

        # Variables para resultados omitidos
        self.omitted_results = []
        self.omitted_file = ""

        # Variables para el progreso basado en resultados
        self.total_results_to_process = 0
        self.processed_results_count = 0

        # Variables para rastrear la fase actual
        self.current_phase = 1  # 1 = Búsqueda, 2 = Tabulación
        self.current_tabulation_course = 0  # Contador para la fase de tabulación

        # Callback para logs
        self.log_callback = None

        # Pause/Resume mechanism for CAPTCHA handling
        # self._is_paused = asyncio.Event() # Moved to __init__
        # self._is_paused.set()  # Initially not paused # Moved to __init__

        # Caché para resultados procesados
        self._processed_results_cache = {}
        self._batch_size = 1  # Further reduced for better stealth - process 1 at a time

        # Semaphore to limit concurrent processing - reduced for better stealth
        self._processing_semaphore = asyncio.Semaphore(
            2
        )  # Limit to 2 concurrent processes

    def set_event_callback(self, callback):
        """Establece el callback para reportar eventos al log del servidor."""
        self.event_callback = callback

    def _emit_event(self, type_str, msg, details=None):
        """Emite un evento si el callback está configurado."""
        logger.info(f"[EMIT_EVENT] type={type_str}, msg={msg[:50]}...")
        if self.event_callback:
            try:
                self.event_callback(type_str, msg, details)
            except Exception as e:
                logger.error(f"Error emitiendo evento: {e}")

    async def _process_single_result(
        self,
        result: Dict[str, Any],
        min_words: int,
        search_engine: str,
        require_keywords: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Procesa un único resultado de búsqueda (API-only)."""
        try:
            async with self._processing_semaphore:
                if self.stop_requested:
                    return None

                sic_code = result.get("sic_code", "")
                course_name = result.get("course_name", "")
                search_term = result.get("search_term", "")
                title = result.get("title", "Sin Título")
                url = result.get("url", "")
                description = result.get("description", "Sin Descripción")

                record_identifier = (sic_code, course_name, url)
                if record_identifier in self.processed_records:
                    self.stats["skipped_duplicates"] += 1
                    self.stats["files_not_saved"] += 1
                    self.omitted_results.append(
                        {
                            "sic_code": sic_code,
                            "course_name": course_name,
                            "title": title,
                            "url": url,
                            "description": description,
                            "omission_reason": "Registro duplicado (mismo código, curso y URL)",
                        }
                    )
                    self._emit_event(
                        "WARNING",
                        f"Registro duplicado omitido: {url}",
                        {"sic": sic_code, "course": course_name},
                    )
                    return None

                self.processed_records.add(record_identifier)

                if not url:
                    return None

                content_extraction_url = (
                    result.get("wayback_url", url)
                    if search_engine == "Wayback Machine"
                    else url
                )

                # SOLUCIÓN CRÍTICA PARA CORDIS:
                # Los resultados de Cordis SPARQL ya incluyen título + descripción detallada
                # Las URLs son páginas de resumen con poco texto extraíble
                # Usar el contenido de la API directamente evita 1,700+ omisiones
                source = result.get("source", "")
                is_cordis = "cordis" in source.lower() or "sparql" in source.lower()

                # Debug: mostrar valor de min_words
                if is_cordis:
                    logger.info(f"🔍 CORDIS - min_words config: {min_words}")

                if is_cordis and description and len(description) > 50:
                    # Usar contenidodel API directamente para Cordis
                    logger.info(
                        f"Using Cordis API metadata for {title[:50]}... (skipping URL extraction)"
                    )
                    full_content = f"{title}\n\n{description}"
                else:
                    # Para otras fuentes, extraer contenido de la URL normalmente
                    try:
                        full_content = await asyncio.wait_for(
                            self.content_extractor.extract_full_content(
                                content_extraction_url
                            ),
                            timeout=60.0,
                        )
                    except asyncio.TimeoutError:
                        self.stats["failed_content_extraction"] += 1
                        self.stats["files_not_saved"] += 1
                        self.omitted_results.append(
                            {
                                "sic_code": sic_code,
                                "course_name": course_name,
                                "title": title,
                                "url": url,
                                "description": description,
                                "omission_reason": "Timeout en extracción de contenido",
                            }
                        )
                        self._emit_event(
                            "WARNING",
                            f"Omitido por timeout en extracción de contenido: {url}",
                            {"sic": sic_code, "course": course_name},
                        )
                        return None

                if not full_content:
                    logger.warning(
                        f"Content extraction failed for {content_extraction_url}. See content_extractor.log for details."
                    )
                    self.stats["failed_content_extraction"] += 1
                    self.stats["files_not_saved"] += 1
                    self.omitted_results.append(
                        {
                            "sic_code": sic_code,
                            "course_name": course_name,
                            "title": title,
                            "url": url,
                            "description": description,
                            "omission_reason": "Error en extracción de contenido",
                        }
                    )
                    self._emit_event(
                        "WARNING",
                        f"Omitido por error en extracción de contenido: {url}",
                        {"sic": sic_code, "course": course_name},
                    )
                    return None

                total_words = self.text_processor.count_all_words(full_content)
                word_counts = self.text_processor.estimate_keyword_occurrences(
                    full_content, search_term
                )
                should_exclude, exclude_reason = (
                    self.text_processor.should_exclude_result(
                        total_words, word_counts, min_words
                    )
                )

                if should_exclude:
                    # Log total keywords found for debugging
                    total_keywords = sum(word_counts.values()) if word_counts else 0
                    logger.info(
                        f"   Result EXCLUDED: {exclude_reason} (Keywords sum: {total_keywords}, min_words: {min_words})"
                    )

                    if "total keywords" in exclude_reason.lower():
                        self.stats["skipped_low_words"] += 1
                        self.stats["files_not_saved"] += 1
                        self.omitted_results.append(
                            {
                                "sic_code": sic_code,
                                "course_name": course_name,
                                "title": title,
                                "url": url,
                                "description": description,
                                "omission_reason": f"Bajo conteo de palabras clave: {total_keywords} (Mínimo: {min_words})",
                            }
                        )
                        self._emit_event(
                            "WARNING",
                            f"Omitido por bajo contenido ({total_keywords} palabras clave)",
                            {"url": url, "min_words": min_words},
                        )

                    else:
                        self.stats["skipped_zero_keywords"] += 1
                        self.stats["files_not_saved"] += 1
                        self.omitted_results.append(
                            {
                                "sic_code": sic_code,
                                "course_name": course_name,
                                "title": title,
                                "url": url,
                                "description": description,
                                "omission_reason": "Sin coincidencias de palabras clave",
                            }
                        )
                        self._emit_event(
                            "WARNING",
                            f"Omitido por cero palabras clave: {url}",
                            {"sic": sic_code, "course": course_name},
                        )
                    return None

                formatted_word_counts = self.text_processor.format_word_counts(
                    total_words, word_counts
                )
                if (
                    formatted_word_counts.startswith("Total words:")
                    and len(formatted_word_counts.split("|")) == 1
                ):
                    self.stats["skipped_zero_keywords"] += 1
                    self.stats["files_not_saved"] += 1
                    self.omitted_results.append(
                        {
                            "sic_code": sic_code,
                            "course_name": course_name,
                            "title": title,
                            "url": url,
                            "description": description,
                            "omission_reason": "Sin coincidencias de palabras clave",
                        }
                    )
                    self._emit_event(
                        "WARNING",
                        f"Omitido por cero palabras clave (formato): {url}",
                        {"sic": sic_code, "course": course_name},
                    )
                    return None

                description = self.text_processor.clean_description(description)
                if len(description) < 100 and full_content:
                    content_preview = full_content[:1000]
                    content_preview = self.text_processor.clean_description(
                        content_preview
                    )
                    if len(content_preview) > len(description) * 2:
                        description = content_preview

                result_data = {
                    "sic_code": sic_code,
                    "course_name": course_name,
                    "title": title,
                    "description": description,
                    "url": url,
                    "total_words": formatted_word_counts,
                    "lang": result.get("lang", "en"),
                }
                return result_data
        except Exception as e:
            logger.error(f"Error procesando URL {result.get('url', '')}: {e}")
            logger.error(traceback.format_exc())
            self.stats["failed_content_extraction"] += 1
            self.stats["total_errors"] += 1
            self.stats["files_not_saved"] += 1
            self.omitted_results.append(
                {
                    "sic_code": result.get("sic_code", ""),
                    "course_name": result.get("course_name", ""),
                    "title": result.get("title", "Sin Título"),
                    "url": result.get("url", ""),
                    "description": result.get("description", "Sin Descripción"),
                    "omission_reason": f"Error en extracción de contenido: {e}",
                }
            )
            self._emit_event(
                "ERROR", f"Error procesando URL: {e}", {"url": result.get("url", "")}
            )
            return None

    async def check_browser_availability(self) -> bool:
        """
        Verifica si el navegador está disponible para el scraping.

        Returns:
            True si el navegador está disponible, False en caso contrario
        """
        return await self.browser_manager.check_playwright_browser()

    def _get_courses_in_range_by_position(
        self, all_courses: List[Tuple[str, str, str, str]], from_sic: str, to_sic: str
    ) -> List[Tuple[str, str, str, str]]:
        """
        Obtiene los cursos en el rango especificado usando POSICIÓN EN LA LISTA.
        ESTO ES LO QUE ESTABA MAL - ahora usa posición, no comparación alfabética.

        Args:
            all_courses: Lista completa de tuplas (sic_code, course_name, status, server)
            from_sic: Código SIC inicial del rango
            to_sic: Código SIC final del rango

        Returns:
            Lista de cursos en el rango especificado
        """
        try:
            # Encontrar las posiciones de los códigos en la lista
            from_index = None
            to_index = None

            for i, (sic_code, course_name, status, server) in enumerate(all_courses):
                if sic_code == from_sic:
                    from_index = i
                    logger.info(
                        f"Código 'desde' encontrado en posición {i}: {sic_code} - {course_name}"
                    )
                if sic_code == to_sic:
                    to_index = i
                    logger.info(
                        f"Código 'hasta' encontrado en posición {i}: {sic_code} - {course_name}"
                    )

            # Verificar que se encontraron ambos códigos
            if from_index is None:
                logger.error(f"Código 'desde' no encontrado: {from_sic}")
                self._emit_event(
                    "ERROR",
                    f"Código 'desde' no encontrado: {from_sic}",
                    {"from_sic": from_sic},
                )
                return []

            if to_index is None:
                logger.error(f"Código 'hasta' no encontrado: {to_sic}")
                self._emit_event(
                    "ERROR",
                    f"Código 'hasta' no encontrado: {to_sic}",
                    {"to_sic": to_sic},
                )
                return []

            # Asegurar que from_index <= to_index (intercambiar si es necesario)
            if from_index > to_index:
                logger.info(
                    f"Intercambiando índices: from_index={from_index}, to_index={to_index}"
                )
                from_index, to_index = to_index, from_index

            # Extraer el rango (inclusive)
            courses_in_range = all_courses[from_index : to_index + 1]

            logger.info(
                f"RANGO CALCULADO: desde posición {from_index} hasta {to_index} (inclusive)"
            )
            logger.info(f"TOTAL DE CURSOS EN RANGO: {len(courses_in_range)}")

            # Log detallado de todos los cursos en el rango
            for i, (sic, course_name, status, server) in enumerate(courses_in_range):
                logger.info(
                    f"  Curso {i + 1}: {sic} - {course_name} (Estado: {status}, Servidor: {server})"
                )

            return courses_in_range

        except Exception as e:
            logger.error(f"Error calculando rango por posición: {str(e)}")
            self._emit_event(
                "ERROR",
                f"Error calculando rango por posición: {str(e)}",
                {"from_sic": from_sic, "to_sic": to_sic},
            )
            return []

    def _clean_memory(self):
        """
        Fuerza la recolección de basura para liberar memoria.
        """
        gc.collect()
        logger.debug("Forced garbage collection")

    def request_stop(self):
        """
        Solicita la detención del proceso de scraping.
        Sobrescribe el método de la clase base para añadir lógica adicional.
        """
        logger.info("Detención solicitada por el usuario")
        self.stop_requested = True
        self._emit_event("INFO", "Detención solicitada por el usuario")

    def pause_scraping(self):
        """
        Pausa el proceso de scraping, típicamente por CAPTCHAs.
        """
        logger.info("Scraping pausado - probablemente por CAPTCHA")
        self._is_paused.clear()  # Clear the event to pause
        self._emit_event("WARNING", "Scraping pausado por CAPTCHA")

    async def resume_scraping(self):
        """
        Reanuda el proceso de scraping después de un pausa.
        """
        logger.info("Scraping reanudado")
        self._is_paused.set()  # Set the event to resume
        self._emit_event("INFO", "Scraping reanudado")

    def is_stop_requested(self):
        """
        Verifica si se ha solicitado la detención del proceso.

        Returns:
            True si se ha solicitado la detención, False en caso contrario
        """
        return self.stop_requested

    async def _process_search_phase(
        self,
        courses_in_range: List[Tuple[str, str, str, str]],
        progress_callback: Optional[Callable] = None,
        search_engine: str = "DuckDuckGo",
        site_domain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta la fase de búsqueda del scraping.
        """
        all_search_results = []
        total_courses = len(courses_in_range)
        current_course = 0

        logger.info(f"=== FASE 1: BÚSQUEDA DE RESULTADOS con {search_engine} ====")
        logger.info(f"Total de cursos a procesar en búsqueda: {total_courses}")

        for sic_code, course_name, status, server in courses_in_range:
            if self.stop_requested:
                logger.info(
                    "Scraping detenido por el usuario durante la fase de búsqueda"
                )
                self._emit_event(
                    "INFO", "Scraping detenido durante la fase de búsqueda"
                )
                break

            current_course += 1
            self.progress_reporter.set_course_counts(current_course, total_courses)
            current_course_info = f"{sic_code} - {course_name}"

            if progress_callback:
                progress_callback(
                    0,
                    f"Buscando curso {current_course} de {total_courses} - {current_course_info}",
                    self.stats,
                )

            search_term = course_name if course_name else sic_code
            logger.info(
                f"Buscando '{search_term}' con código SIC {sic_code} ({current_course}/{total_courses})"
            )
            self._emit_event(
                "SEARCH",
                f"Iniciando búsqueda para '{search_term}'",
                {"sic": sic_code, "course": course_name, "engine": search_engine},
            )

            logger.info(
                f"DEBUG: Motor de búsqueda seleccionado: '{search_engine}', Dominio: '{site_domain}'"
            )

            server_id = self.config.get("server_id", "UNKNOWN_SERVER")
            self.csv_handler.update_course_status(
                sic_code, course_name, "procesando", server_id
            )

            try:
                if self.stop_requested:
                    logger.info(
                        "Scraping detenido por el usuario antes de iniciar búsqueda"
                    )
                    self._emit_event(
                        "INFO", "Scraping detenido antes de iniciar búsqueda"
                    )
                    break

                search_results = []

                try:
                    search_results = await self.search_engine.get_search_results(
                        search_term, search_engine, site_domain
                    )
                except ManualCaptchaPendingError:
                    logger.warning(
                        f"ACCIÓN REQUERIDA: Se ha detectado un CAPTCHA para '{search_term}'."
                    )
                    logger.warning(
                        "El scraping se ha pausado. Por favor, resuelva el CAPTCHA en el navegador y reanude el proceso desde el cliente."
                    )
                    if progress_callback:
                        progress_callback(
                            0,
                            f"PAUSADO: Resuelve el CAPTCHA para '{search_term}' y reanuda.",
                            self.stats,
                        )

                    self.pause_scraping()
                    await self._is_paused.wait()

                    # Una vez reanudado, se reintentará la búsqueda para el término actual.
                    logger.info("Reanudando scraping después del CAPTCHA...")
                    self._emit_event("INFO", "Reanudando scraping después del CAPTCHA")
                    continue

                if self.stop_requested:
                    logger.info("Scraping detenido por el usuario después de búsqueda")
                    self._emit_event("INFO", "Scraping detenido después de búsqueda")
                    break

                for result in search_results:
                    result["sic_code"] = sic_code
                    result["course_name"] = course_name
                    result["search_term"] = search_term
                    all_search_results.append(result)

                self.stats["total_urls_found"] += len(search_results)
                logger.info(
                    f"Encontrados {len(search_results)} resultados para '{search_term}'"
                )
                self._emit_event(
                    "SEARCH_COMPLETED",
                    f"Búsqueda completada: {len(search_results)} resultados.",
                    {"term": search_term, "engine": search_engine},
                )

                if progress_callback:
                    progress_callback(
                        0,
                        f"Buscando curso {current_course} de {total_courses} - {current_course_info} | Encontrados: {len(search_results)} resultados",
                        self.stats,
                    )

                if not search_results:
                    logger.info(
                        f"No se encontraron resultados para '{search_term}' con código SIC {sic_code}"
                    )

                if current_course % 5 == 0:
                    self._clean_memory()

            except asyncio.TimeoutError:
                logger.error(
                    f"Timeout durante la búsqueda de '{search_term}'. Continuando con el siguiente curso."
                )
                self.stats["total_errors"] += 1
                self._emit_event(
                    "ERROR",
                    f"Timeout durante la búsqueda de '{search_term}'",
                    {"term": search_term},
                )
                continue
            except Exception as e:
                logger.error(f"Error durante la búsqueda de '{search_term}': {str(e)}")
                logger.error(traceback.format_exc())
                self.stats["total_errors"] += 1
                self._emit_event(
                    "ERROR",
                    f"Error durante la búsqueda de '{search_term}': {str(e)}",
                    {"term": search_term},
                )
                continue

        return all_search_results

    async def _process_common_crawl_search_phase(
        self,
        courses_in_range: List[Tuple[str, str, str, str]],
        site_domain: str,
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta la fase de búsqueda del scraping usando Common Crawl.
        """
        all_search_results = []
        total_courses = len(courses_in_range)
        current_course = 0

        if not site_domain:
            logger.error(
                "Error Crítico: La búsqueda en Common Crawl se inició sin un dominio especificado."
            )
            if progress_callback:
                progress_callback(
                    100, "Error: Dominio no especificado para Common Crawl."
                )
            self._emit_event("ERROR", "Dominio no especificado para Common Crawl")
            return []

        logger.info(f"=== FASE 1: BÚSQUEDA DE RESULTADOS con Common Crawl ====")
        logger.info(f"Total de cursos a procesar en búsqueda: {total_courses}")

        from utils.comcrawl_local import IndexClient

        for sic_code, course_name, status, server in courses_in_range:
            if self.stop_requested:
                logger.info(
                    "Scraping detenido por el usuario durante la fase de búsqueda"
                )
                self._emit_event(
                    "INFO",
                    "Scraping detenido durante la fase de búsqueda (Common Crawl)",
                )
                break

            current_course += 1
            self.progress_reporter.set_course_counts(current_course, total_courses)
            current_course_info = f"{sic_code} - {course_name}"

            if progress_callback:
                progress_callback(
                    0,
                    f"Buscando curso {current_course} de {total_courses} - {current_course_info}",
                )

            search_term = course_name if course_name else sic_code
            logger.info(
                f"Buscando en Common Crawl: '{search_term}' en el dominio '{site_domain}' ({current_course}/{total_courses})"
            )
            self._emit_event(
                "SEARCH",
                f"Iniciando búsqueda para '{search_term}' en Common Crawl",
                {
                    "sic": sic_code,
                    "course": course_name,
                    "engine": "Common Crawl",
                    "domain": site_domain,
                },
            )

            server_id = self.config.get("server_id", "UNKNOWN_SERVER")
            self.csv_handler.update_course_status(
                sic_code, course_name, "procesando", server_id
            )

            try:
                if self.stop_requested:
                    logger.info(
                        "Scraping detenido por el usuario antes de iniciar búsqueda"
                    )
                    self._emit_event(
                        "INFO",
                        "Scraping detenido antes de iniciar búsqueda (Common Crawl)",
                    )
                    break

                search_results = []
                client = IndexClient()
                client.search(f"*.{site_domain}/*", search_term=search_term)
                results = client.results

                for result in results:
                    search_results.append(
                        {
                            "url": result["url"],
                            "title": result.get("title", "Sin Título"),
                            "description": result.get("description", "Sin Descripción"),
                            "sic_code": sic_code,
                            "course_name": course_name,
                            "search_term": search_term,
                            "warc_filename": result.get("warc_filename"),
                            "warc_record_offset": result.get("warc_record_offset"),
                            "warc_record_length": result.get("warc_record_length"),
                        }
                    )

                if self.stop_requested:
                    logger.info("Scraping detenido por el usuario después de búsqueda")
                    self._emit_event(
                        "INFO", "Scraping detenido después de búsqueda (Common Crawl)"
                    )
                    break

                for result in search_results:
                    result["sic_code"] = sic_code
                    result["course_name"] = course_name
                    result["search_term"] = search_term
                    all_search_results.append(result)

                self.stats["total_urls_found"] += len(search_results)
                logger.info(
                    f"Encontrados {len(search_results)} resultados para '{search_term}'"
                )
                self._emit_event(
                    "SEARCH_COMPLETED",
                    f"Búsqueda completada en Common Crawl: {len(search_results)} resultados.",
                    {"term": search_term, "engine": "Common Crawl"},
                )

                if progress_callback:
                    progress_callback(
                        0,
                        f"Buscando curso {current_course} de {total_courses} - {current_course_info} | Encontrados: {len(search_results)} resultados",
                    )

                if not search_results:
                    logger.info(
                        f"No se encontraron resultados para '{search_term}' con código SIC {sic_code}"
                    )

                if current_course % 5 == 0:
                    self._clean_memory()

            except Exception as e:
                logger.error(
                    f"Error durante la búsqueda en Common Crawl de '{search_term}': {str(e)}"
                )
                logger.error(traceback.format_exc())
                self.stats["total_errors"] += 1
                self._emit_event(
                    "ERROR",
                    f"Error durante la búsqueda en Common Crawl de '{search_term}': {str(e)}",
                    {"term": search_term},
                )
                continue

        return all_search_results

    async def _process_wayback_machine_search_phase(
        self,
        courses_in_range: List[Tuple[str, str, str, str]],
        site_domain: str,
        progress_callback: Optional[Callable] = None,
        gov_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta la fase de búsqueda del scraping usando la API de Scraping de Internet Archive.
        Ahora soporta la opción gov_only para retornar solo snapshots cuyo host termina en .gov.
        """
        all_search_results = []
        total_courses = len(courses_in_range)
        current_course = 0

        if not site_domain:
            logger.error(
                "Error Crítico: La búsqueda en Wayback Machine se inició sin un dominio especificado."
            )
            if progress_callback:
                progress_callback(
                    100, "Error: Dominio no especificado para Wayback Machine."
                )
            self._emit_event("ERROR", "Dominio no especificado para Wayback Machine")
            return []

        logger.info(
            f"=== FASE 1: BÚSQUEDA DE RESULTADOS con Internet Archive Scraping API (gov_only={gov_only}) ===="
        )
        logger.info(f"Total de cursos a procesar en búsqueda: {total_courses}")

        # Reuse SearchEngine.search_wayback logic if present
        from utils.scraper.search_engine import SearchEngine

        search_engine = SearchEngine(
            self.browser_manager, self.text_processor, self.config
        )

        for sic_code, course_name, status, server in courses_in_range:
            if self.stop_requested:
                logger.info(
                    "Scraping detenido por el usuario durante la fase de búsqueda"
                )
                self._emit_event(
                    "INFO",
                    "Scraping detenido durante la fase de búsqueda (Wayback Machine)",
                )
                break

            current_course += 1
            self.progress_reporter.set_course_counts(current_course, total_courses)
            current_course_info = f"{sic_code} - {course_name}"

            if progress_callback:
                progress_callback(
                    0,
                    f"Buscando curso {current_course} de {total_courses} - {current_course_info}",
                )

            search_term = course_name if course_name else sic_code
            logger.info(
                f"Buscando en Internet Archive para: '{search_term}' en el dominio '{site_domain}' (curso {current_course}/{total_courses})"
            )
            self._emit_event(
                "SEARCH",
                f"Iniciando búsqueda para '{search_term}' en Wayback Machine",
                {
                    "sic": sic_code,
                    "course": course_name,
                    "engine": "Wayback Machine",
                    "domain": site_domain,
                },
            )

            try:
                # Use the search engine's API-only wayback search with verification
                results = await search_engine.search_wayback(
                    search_term, site_domain=site_domain, max_items=50
                )

                # If gov_only is set, filter results to hosts that end with .gov
                if gov_only:
                    filtered = []
                    for r in results:
                        try:
                            from urllib.parse import urlparse

                            parsed = urlparse(
                                r.get("url") or r.get("normalized_url") or ""
                            )
                            host = parsed.netloc.lower()
                            if host.endswith(".gov"):
                                filtered.append(r)
                        except Exception:
                            continue
                    results = filtered

                # Attach SIC/course metadata and append
                for r in results:
                    r["sic_code"] = sic_code
                    r["course_name"] = course_name
                    r["search_term"] = search_term
                    all_search_results.append(r)

                self.stats["total_urls_found"] += len(results)
                logger.info(
                    f"Encontrados {len(results)} resultados verificados para '{search_term}'"
                )
                self._emit_event(
                    "SEARCH_COMPLETED",
                    f"Búsqueda completada en Wayback Machine: {len(results)} resultados.",
                    {"term": search_term, "engine": "Wayback Machine"},
                )

                if progress_callback:
                    progress_callback(
                        0,
                        f"Buscando curso {current_course} de {total_courses} - {current_course_info} | Encontrados: {len(results)} resultados verificados",
                    )

                if current_course % 5 == 0:
                    self._clean_memory()

            except Exception as e:
                logger.error(
                    f"Error durante la búsqueda en Wayback para '{search_term}': {str(e)}"
                )
                logger.error(traceback.format_exc())
                self.stats["total_errors"] += 1
                self._emit_event(
                    "ERROR",
                    f"Error durante la búsqueda en Wayback para '{search_term}': {str(e)}",
                    {"term": search_term},
                )
                continue

        return all_search_results

    async def _process_cordis_api_phase(
        self,
        courses_in_range: List[Tuple[str, str, str, str]],
        search_mode: str = "broad",
        progress_callback: Optional[Callable] = None,
        languages: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta la fase de búsqueda usando la API de Cordis Europa.

        Args:
            courses_in_range: Lista de cursos a procesar
            search_mode: Modo de búsqueda ('broad' o 'exact')
            progress_callback: Callback para reportar progreso
            languages: Lista de idiomas a incluir (ej: ['en', 'es', 'de']).
                      Si es None, usa todos los idiomas disponibles.
        """
        all_search_results = []
        total_courses = len(courses_in_range)
        current_course = 0

        logger.info(f"=== FASE 1: BÚSQUEDA DE RESULTADOS con CORDIS EUROPA API ====")
        logger.info(f"Total de cursos a procesar en búsqueda: {total_courses}")
        logger.info(f"Idiomas CORDIS seleccionados: {languages}")

        for sic_code, course_name, status, server in courses_in_range:
            if self.stop_requested:
                logger.info(
                    "Scraping detenido por el usuario durante la fase de búsqueda"
                )
                self._emit_event(
                    "INFO", "Scraping detenido durante la fase de búsqueda (Cordis API)"
                )
                break

            current_course += 1
            self.progress_reporter.set_course_counts(current_course, total_courses)
            current_course_info = f"{sic_code} - {course_name}"

            if progress_callback:
                progress_callback(
                    0,
                    f"Buscando curso {current_course} de {total_courses} - {current_course_info}",
                    self.stats,
                )

            search_term = course_name if course_name else sic_code

            # SANITIZACIÓN CRITICA: Eliminar prefijos tipo "101.0 - " o "123 - " que rompen la búsqueda exacta
            # El usuario tiene cursos como "101.0 - Iron ore mining". Buscamos solo "Iron ore mining".
            # ACTUALIZADO: El guión es opcional para casos como "101.0 Iron mining"
            search_term = re.sub(r"^[\d\.]+\s*[-–]?\s*", "", search_term).strip()

            # QUITAR TODO texto entre paréntesis incluyendo los paréntesis
            # Ejemplos: "TECHNOLOGY (3)" -> "TECHNOLOGY", "Course (Advanced)" -> "Course"
            search_term = re.sub(r"\s*\([^)]*\)\s*", " ", search_term).strip()

            # Limpiar múltiples espacios
            search_term = re.sub(r"\s+", " ", search_term).strip()

            logger.info(
                f"Buscando en Cordis API: '{search_term}' (Original: '{course_name if course_name else sic_code}')"
            )
            self._emit_event(
                "SEARCH",
                f"Iniciando búsqueda para '{search_term}' en Cordis API",
                {"sic": sic_code, "course": course_name, "engine": "Cordis API"},
            )

            # Callback para reportar total de resultados detectados
            def on_total_hits_detected(total_hits):
                info_msg = f"🔍 '{search_term}' tiene {total_hits:,} resultados disponibles en CORDIS."
                logger.info(info_msg)
                self._emit_event(
                    "INFO",
                    info_msg,
                    {"term": search_term, "total_hits": total_hits},
                )

            # Callback de progreso detallado para CORDIS
            last_progress_emit = [0]  # Use list to allow mutation in nested function

            def cordis_progress_callback(page, total_hits, collected):
                print(
                    f"[CORDIS CALLBACK] 📡 page={page}, total={total_hits}, collected={collected}"
                )
                logger.info(
                    f"[CORDIS CALLBACK] 📡 page={page}, total_hits={total_hits}, collected={collected}"
                )
                # Emitir progreso cada 500 resultados o cada 5 páginas
                should_emit = (collected >= last_progress_emit[0] + 500) or (
                    page % 5 == 0
                )
                if should_emit:
                    last_progress_emit[0] = collected
                    progress_pct = (
                        min(100, int((collected / total_hits) * 100))
                        if total_hits > 0
                        else 0
                    )
                    msg = f"⏳ CORDIS: {course_name} | Página {page} | {collected:,}/{total_hits:,} resultados ({progress_pct}%)"
                    logger.info(msg)
                    self._emit_event(
                        "PROGRESS",
                        msg,
                        {
                            "page": page,
                            "collected": collected,
                            "total": total_hits,
                            "course": course_name,
                        },
                    )
                    # Actualizar barra de progreso general y monitor de actividad
                    if progress_callback:
                        progress_callback(
                            progress_pct,
                            f"CORDIS: {course_name} - {collected:,}/{total_hits:,} ({progress_pct}%)",
                            self.stats,
                        )

            try:
                results = await self.cordis_api_client.search_projects_and_publications(
                    search_term,
                    search_mode=search_mode,
                    progress_callback=cordis_progress_callback,
                    languages=languages
                    if languages
                    else ["en", "es", "de", "fr", "it", "pl"],
                    total_hits_callback=on_total_hits_detected,
                )

                for r in results:
                    r["sic_code"] = sic_code
                    r["course_name"] = course_name
                    r["search_term"] = search_term
                    all_search_results.append(r)

                self.stats["total_urls_found"] += len(results)

                # Logging detallado
                logger.info(f"═══════════════════════════════════════════════════════")
                logger.info(f"🎯 CURSO PROCESADO: {sic_code} - {course_name}")
                logger.info(f"   📝 Término de búsqueda: '{search_term}'")
                logger.info(f"   ✅ Resultados encontrados: {len(results)}")
                logger.info(f"   📊 Progreso: {current_course}/{total_courses} cursos")
                logger.info(f"═══════════════════════════════════════════════════════")

                self._emit_event(
                    "SEARCH_COMPLETED",
                    f"✅ {course_name}: {len(results)} resultados",
                    {
                        "sic": sic_code,
                        "course": course_name,
                        "term": search_term,
                        "results": len(results),
                        "progress": f"{current_course}/{total_courses}",
                    },
                )

                # Actualizar progreso a 100% al completar
                if progress_callback:
                    progress_callback(
                        100,
                        f"✅ {course_name}: {len(results)} resultados de CORDIS",
                        self.stats,
                    )

            except Exception as e:
                logger.error(f"Error en búsqueda Cordis API para '{search_term}': {e}")
                self.stats["total_errors"] += 1
                self._emit_event(
                    "ERROR",
                    f"Error en búsqueda Cordis API para '{search_term}': {e}",
                    {"term": search_term},
                )
                continue

        logger.info(
            f"=== CORDIS SEARCH COMPLETE: {len(all_search_results)} total results collected ==="
        )
        return all_search_results

    async def _process_tabulation_phase(
        self,
        all_search_results: List[Dict[str, Any]],
        total_courses: int,
        min_words: int,
        search_engine: str,
        progress_callback: Optional[Callable] = None,
        require_keywords: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta la fase de tabulación del scraping.
        """
        processed_results = []
        self.total_results_to_process = len(all_search_results)
        self.processed_results_count = 0
        self.progress_reporter.set_result_counts(0, self.total_results_to_process)
        self.current_phase = 2
        self.current_tabulation_course = 0
        self.progress_reporter.set_phase(2)

        results_by_course = {}
        for result in all_search_results:
            sic_code = result.get("sic_code", "")
            course_name = result.get("course_name", "")
            key = (sic_code, course_name)
            if key not in results_by_course:
                results_by_course[key] = []
            results_by_course[key].append(result)

        logger.info(f"=== FASE 2: TABULACIÓN DE RESULTADOS ====")
        logger.info(
            f"Se encontraron {self.total_results_to_process} resultados totales para procesar"
        )
        logger.info(f"📋 Cursos con resultados: {len(results_by_course)}")

        self._emit_event(
            "INFO",
            f"🔄 Iniciando tabulación: {self.total_results_to_process} resultados de {len(results_by_course)} cursos",
        )

        if progress_callback:
            progress_callback(
                0,
                f"🔄 Tabulación: {self.total_results_to_process} resultados",
            )

        logger.info(f"📋 Cursos con resultados: {len(results_by_course)}")

        logger.info(f"═══════════════════════════════════════════════════════")
        logger.info(f"🔄 FASE 2: TABULACIÓN DE RESULTADOS")
        logger.info(f"   📊 Total resultados: {self.total_results_to_process}")
        logger.info(f"   📚 Cursos a tabular: {len(results_by_course)}")
        logger.info(f"═══════════════════════════════════════════════════════")

        self._emit_event(
            "INFO",
            f"🔄 Tabulación: {self.total_results_to_process} resultados de {len(results_by_course)} cursos",
        )

        if progress_callback:
            progress_callback(
                0,
                f"🔄 Tabulación: {self.total_results_to_process} resultados de {len(results_by_course)} cursos",
            )

        if self.stop_requested:
            logger.info(
                "Scraping detenido por el usuario antes de iniciar la fase de tabulación"
            )
            self._emit_event(
                "INFO", "Scraping detenido antes de iniciar la fase de tabulación"
            )
            # Final cleanup check to ensure no empty files are left behind
            self.result_manager.cleanup_if_empty()

            return processed_results

        for i, ((sic_code, course_name), course_results) in enumerate(
            results_by_course.items()
        ):
            if self.stop_requested:
                logger.info(
                    "Scraping detenido por el usuario durante la fase de tabulación"
                )
                self._emit_event(
                    "INFO", "Scraping detenido durante la fase de tabulación"
                )
                break

            self.current_tabulation_course = i + 1
            self.progress_reporter.set_tabulation_course(self.current_tabulation_course)

            logger.info(f"───────────────────────────────────────────────────────────")
            logger.info(
                f"📋 Tabulando curso {i + 1}/{len(results_by_course)}: {sic_code} - {course_name}"
            )
            logger.info(f"   📄 Resultados a procesar: {len(course_results)}")

            self._emit_event(
                "TABULATION_START",
                f"📋 {course_name}: {len(course_results)} resultados",
                {
                    "sic": sic_code,
                    "course": course_name,
                    "results": len(course_results),
                },
            )

            if progress_callback:
                progress_percentage = (
                    self.processed_results_count / self.total_results_to_process
                ) * 100
                tabulation_message = self.progress_reporter.report_tabulation_progress(
                    self.processed_results_count,
                    self.total_results_to_process,
                    sic_code,
                    course_name,
                    total_results=self.total_results_to_process,
                )
                progress_callback(progress_percentage, tabulation_message, self.stats)

            for j in range(0, len(course_results), self._batch_size):
                if self.stop_requested:
                    logger.info(
                        "Scraping detenido por el usuario durante el procesamiento de lotes"
                    )
                    self._emit_event(
                        "INFO", "Scraping detenido durante el procesamiento de lotes"
                    )
                    break

                batch = course_results[j : j + self._batch_size]

                tasks = [
                    asyncio.create_task(
                        self._process_single_result(
                            result,
                            min_words,
                            search_engine,
                            require_keywords=require_keywords,
                        )
                    )
                    for result in batch
                ]

                try:
                    done, pending = await asyncio.wait(
                        tasks, timeout=180.0, return_when=asyncio.ALL_COMPLETED
                    )

                    if pending:
                        logger.warning(
                            f"{len(pending)} tasks timed out in batch processing"
                        )
                        for task in pending:
                            task.cancel()

                    batch_results = []
                    for task in done:
                        try:
                            if not task.exception():
                                result = task.result()
                                if result:
                                    batch_results.append(result)
                        except Exception as e:
                            logger.error(f"Error getting task result: {str(e)}")
                            self._emit_event(
                                "ERROR",
                                f"Error obteniendo resultado de tarea: {str(e)}",
                            )

                except Exception as e:
                    logger.error(f"Error processing batch: {str(e)}")
                    self._emit_event("ERROR", f"Error procesando lote: {str(e)}")
                    batch_results = []

                for result_data in batch_results:
                    processed_results.append(result_data)
                    logger.info(
                        f"💾 Intentando guardar resultado: {result_data.get('title', 'NO TITLE')[:50]}..."
                    )

                    # Add the result with error handling
                    try:
                        success = self.result_manager.add_result(result_data)
                        if success:
                            self.stats["files_saved"] += 1
                            logger.info(
                                f"✅ Resultado guardado: {result_data['title']} - {result_data['url']}"
                            )
                        else:
                            logger.error(
                                f"❌ FALLO al guardar resultado: {result_data['title']}"
                            )
                            self.stats["files_not_saved"] += 1
                    except Exception as e:
                        logger.error(f"❌ ERROR guardando resultado: {e}")
                        self.stats["files_not_saved"] += 1

                self.processed_results_count += len(batch)
                self.progress_reporter.set_result_counts(
                    self.processed_results_count, self.total_results_to_process
                )

                if progress_callback:
                    progress_percentage = (
                        self.processed_results_count / self.total_results_to_process
                    ) * 100
                    tabulation_message = (
                        self.progress_reporter.report_tabulation_progress(
                            self.processed_results_count,
                            self.total_results_to_process,
                            sic_code,
                            course_name,
                            total_results=self.total_results_to_process,
                        )
                    )
                    progress_callback(
                        progress_percentage, tabulation_message, self.stats
                    )

                if j % (self._batch_size * 5) == 0:
                    self._clean_memory()

                await asyncio.sleep(0.5)

            server_id = self.config.get("server_id", "UNKNOWN_SERVER")
            self.csv_handler.update_course_status(
                sic_code, course_name, "COMPLETADO", server_id
            )

            # Resumen detallado del curso
            logger.info(f"═══════════════════════════════════════════════════════")
            logger.info(f"✅ CURSO COMPLETADO: {sic_code} - {course_name}")
            logger.info(f"   📊 Resultados encontrados: {len(course_results)}")
            logger.info(f"   ✅ Procesados correctamente: {len(batch_results)}")
            logger.info(f"   📈 Progreso: {i + 1}/{len(results_by_course)} cursos")
            logger.info(
                f"   ⏭️ Siguiente: {results_by_course[list(results_by_course.keys())[i + 1]][0].get('course_name', 'N/A') if i + 1 < len(results_by_course) else 'FIN'}"
            )
            logger.info(f"═══════════════════════════════════════════════════════")

            self._emit_event(
                "TABULATION_COMPLETE",
                f"✅ {course_name}: {len(batch_results)}/{len(course_results)}",
                {
                    "sic": sic_code,
                    "course": course_name,
                    "processed": len(batch_results),
                    "total": len(course_results),
                },
            )

        return processed_results

    def _save_omitted_to_excel(self, custom_path=None) -> str:
        """
        Guarda los resultados omitidos en un archivo Excel.
        """
        try:
            if not self.omitted_results and custom_path is None:
                if not self.omitted_file:
                    logger.warning(
                        "No hay resultados omitidos para guardar y no se especificó ruta"
                    )
                    return ""
                custom_path = self.omitted_file

            file_path = custom_path if custom_path else self.omitted_file

            if not file_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Save in results/omitidos so it gets zipped by download_results
                project_root = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
                omitted_dir = os.path.join(project_root, "results", "omitidos")
                os.makedirs(omitted_dir, exist_ok=True)
                file_path = os.path.join(omitted_dir, f"omitidos_{timestamp}.xlsx")
                logger.info(
                    f"No se especificó archivo para omitidos, usando: {file_path}"
                )

            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

            self.result_manager.omitted_results = self.omitted_results
            self.result_manager.omitted_file = file_path
            saved_path = self.result_manager.save_omitted_to_excel()

            logger.info(
                f"Se guardaron {len(self.omitted_results)} resultados omitidos en: {saved_path}"
            )

            return saved_path

        except Exception as e:
            logger.error(f"Error guardando resultados omitidos: {str(e)}")
            return ""

    def set_proxy_manager(self, proxy_manager):
        """
        Establece el gestor de proxies a utilizar.
        """
        if proxy_manager:
            self.proxy_manager = proxy_manager
            if hasattr(self, "browser_manager"):
                logger.info(
                    "Proxy manager disponible pero NO establecido automáticamente"
                )
            else:
                logger.warning("BrowserManager no inicializado")
        else:
            logger.info("Proxy manager es None - usando conexión directa")

    def enable_proxies(self, enable: bool = True):
        """
        Habilita o deshabilita el uso de proxies explícitamente.
        """
        if enable and self.proxy_manager:
            if hasattr(self, "browser_manager"):
                self.browser_manager.set_proxy_manager(self.proxy_manager)
                logger.info("Proxies HABILITADOS explícitamente")
            else:
                logger.warning(
                    "BrowserManager no inicializado, no se pueden habilitar proxies"
                )
        else:
            if hasattr(self, "browser_manager"):
                self.browser_manager.set_proxy_manager(None)
                logger.info("Proxies DESHABILITADOS explícitamente")

    async def run_scraping(
        self,
        params: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
        worker_id: Optional[int] = None,
        batch: Optional[List[Tuple]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta el proceso de scraping.

        Args:
            params: Diccionario de parámetros para la tarea.
            progress_callback: Callback para reportar el progreso.
            worker_id: ID opcional para el trabajador en modo paralelo.
            batch: Lote opcional de cursos a procesar (para modo multiproceso).
        """
        try:
            self.stop_requested = False

            # Extract search_engine early to decide whether browser is needed
            search_engine = (
                params.get("search_engine", "DuckDuckGo")
                if isinstance(params, dict)
                else "DuckDuckGo"
            )
            site_domain = (
                params.get("site_domain") if isinstance(params, dict) else None
            )

            # NUEVO: Configurar modo de salida de resultados (Por curso o Conglomerado)
            output_mode = (
                params.get("results_output_mode", "Por curso")
                if isinstance(params, dict)
                else "Por curso"
            )
            self.result_manager.output_mode = output_mode
            logger.info(f"Modo de salida de resultados: {output_mode}")

            # Decide whether browser is needed based on requested search engine
            # Browser is NOT required for 'Wayback Machine' or 'Cordis Europa API' (API-only) searches.
            if search_engine not in ["Wayback Machine", "Cordis Europa API"]:
                browser_available = (
                    await self.browser_manager.check_playwright_browser()
                )
                logger.info(
                    f"Resultado de check_playwright_browser: {browser_available}"
                )
                if not browser_available:
                    logger.error(
                        "Navegador no disponible, no se puede realizar el scraping para el motor solicitado"
                    )
                    if progress_callback:
                        progress_callback(
                            100,
                            "Error: Navegador no disponible para el motor solicitado",
                        )
                    return []
            else:
                logger.info(
                    f"Modo API-only seleccionado para {search_engine}; omitiendo verificación de navegador."
                )
                # CRITICAL: Disable browser in ContentExtractor to prevent accidental launches/hangs
                if hasattr(self, "content_extractor"):
                    self.content_extractor.browser_disabled = True
                    logger.info(
                        "Browser fallback DISABLED in ContentExtractor for API-only mode."
                    )

            self.processed_records = set()
            self.stats = {
                "total_urls_found": 0,
                "skipped_non_gov": 0,
                "skipped_low_words": 0,
                "skipped_zero_keywords": 0,
                "skipped_duplicates": 0,
                "files_saved": 0,
                "failed_content_extraction": 0,
                "files_not_saved": 0,
                "total_errors": 0,
                "captchas_detected": 0,
                "captchas_solved": 0,
            }

            self.total_results_to_process = 0
            self.processed_results_count = 0
            self.omitted_results = []
            self.omitted_file = ""

            from_sic = params.get("from_sic")
            to_sic = params.get("to_sic")
            from_course = params.get("from_course", "")
            to_course = params.get("to_course", "")
            min_words = params.get("min_words", 30)
            search_engine = params.get("search_engine", "DuckDuckGo")
            site_domain = params.get("site_domain")
            gov_only = params.get("gov_only", False)

            if from_course and not to_course:
                to_course = from_course

            if not from_sic or not to_sic:
                logger.error("Faltan parámetros requeridos")
                return []

            logger.info(
                f"Creando tarea de fondo para scraping: {{'de_sic': '{from_sic}', 'a_sic': '{to_sic}', 'de_curso': '{from_course}', 'a_curso': '{to_course}', 'min_palabras': {min_words}, 'motor': '{search_engine}', 'dominio': '{site_domain}'}}"
            )

            # UPDATE SEMAPHORE WITH USER CONFIG (Fix for concurrency issue)
            num_workers = params.get("num_workers", 4)
            if num_workers > 0:
                logger.info(
                    f"🚀 Estableciendo concurrencia a {num_workers} workers (Solicitado por usuario)"
                )
                self._processing_semaphore = asyncio.Semaphore(num_workers)

            output_file, omitted_file = self.result_manager.initialize_output_files(
                from_sic,
                to_sic,
                from_course,
                to_course,
                search_engine,
                worker_id=worker_id,
            )
            self.omitted_file = omitted_file

            # Verify that the CSV file was created
            if os.path.exists(output_file):
                logger.info(f"✅ Archivo CSV creado exitosamente: {output_file}")
                # Check file size
                file_size = os.path.getsize(output_file)
                logger.info(f"   Tamaño inicial del archivo: {file_size} bytes")
            else:
                logger.error(
                    f"❌ ERROR: El archivo CSV no se pudo crear: {output_file}"
                )

            if (
                hasattr(self.browser_manager, "proxy_manager")
                and self.browser_manager.proxy_manager
            ):
                proxy_count = len(self.browser_manager.proxy_manager.proxies)
                if proxy_count > 0:
                    logger.info(
                        f"Usando {proxy_count} proxies para el scraping con rotación automática"
                    )
                    if progress_callback:
                        progress_callback(
                            0,
                            f"Archivo CSV creado: {output_file} | Usando {proxy_count} proxies",
                        )
                else:
                    logger.warning(
                        "No hay proxies configurados, usando conexión directa"
                    )
            else:
                logger.info("Usando conexión directa (sin proxies)")

            if progress_callback:
                progress_callback(0, f"Archivo CSV creado: {output_file}")

            server_id = self.config.get("server_id", "UNKNOWN_SERVER")

            if batch:
                logger.info(
                    f"MODO MULTIPROCESO: Usando lote proporcionado de {len(batch)} cursos."
                )
                courses_in_range = []
                for item in batch:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        # Transformar a formato esperado (sic, name, status, server)
                        courses_in_range.append(
                            (item[0], item[1], "PENDING", server_id)
                        )
                    else:
                        logger.warning(f"Item de lote inválido: {item}")
            else:
                all_sic_codes_with_courses = (
                    self.csv_handler.get_detailed_sic_codes_with_courses()
                )

                if not all_sic_codes_with_courses:
                    logger.warning(
                        "No se encontraron códigos SIC detallados con cursos en los datos CSV"
                    )
                    return []

                courses_in_range = self._get_courses_in_range_by_position(
                    all_sic_codes_with_courses, from_sic, to_sic
                )

            logger.info(
                f"CURSOS EN RANGO CALCULADOS: {len(courses_in_range)} códigos SIC desde '{from_sic}' hasta '{to_sic}'"
            )

            total_courses = len(courses_in_range)
            logger.info(f"TOTAL DE CURSOS A PROCESAR: {total_courses}")

            if total_courses == 0:
                logger.warning("No se encontraron cursos en el rango especificado")
                # Cleanup empty file if exists (Auto-fix)
                self.result_manager.cleanup_if_empty()
                return []

            server_id = self.config.get("server_id", "UNKNOWN_SERVER")
            logger.info(
                f"Marcando {len(courses_in_range)} cursos como 'PROCESANDO' en el servidor {server_id}..."
            )

            courses_to_update = [(c[0], c[1]) for c in courses_in_range]
            self.csv_handler.update_range_status(
                courses_to_update, "PROCESANDO", server_id
            )

            if search_engine == "Common Crawl":
                all_search_results = await self._process_common_crawl_search_phase(
                    courses_in_range, site_domain, progress_callback
                )
            elif search_engine == "Wayback Machine":
                # Pass gov_only flag to the wayback phase
                all_search_results = await self._process_wayback_machine_search_phase(
                    courses_in_range, site_domain, progress_callback, gov_only=gov_only
                )
            elif search_engine == "Cordis Europa API":
                # Obtener idiomas CORDIS desde la configuración
                cordis_languages = (
                    params.get("cordis_languages", ["en", "es", "de", "fr", "it", "pl"])
                    if isinstance(params, dict)
                    else ["en", "es", "de", "fr", "it", "pl"]
                )
                all_search_results = await self._process_cordis_api_phase(
                    courses_in_range,
                    progress_callback=progress_callback,
                    languages=cordis_languages,
                )
            else:
                all_search_results = await self._process_search_phase(
                    courses_in_range, progress_callback, search_engine, site_domain
                )

            if not all_search_results:
                logger.warning("No se encontraron resultados para procesar")
                # Cleanup empty file if exists (Auto-fix)
                self.result_manager.cleanup_if_empty()
                if progress_callback:
                    progress_callback(100, "No se encontraron resultados para procesar")
                return []

            logger.warning(
                f"🔍 DEBUG: all_search_results tiene {len(all_search_results)} resultados, entrando a tabulación..."
            )

            if self.stop_requested:
                logger.info(
                    "Scraping detenido por el usuario después de la fase de búsqueda"
                )

                if self.omitted_results:
                    self._save_omitted_to_excel()
                    logger.info(
                        f"Resultados omitidos guardados en: {os.path.abspath(self.omitted_file)}"
                    )

                if progress_callback:
                    progress_callback(
                        100,
                        f"Proceso detenido por el usuario. Se encontraron {len(all_search_results)} resultados pero no se procesaron.",
                    )

                return []

            self._clean_memory()

            logger.info(
                f"=== PREPARANDO FASE 2: {len(all_search_results)} resultados para tabular ==="
            )

            require_keywords = params.get("require_keywords", False)
            try:
                processed_results = await self._process_tabulation_phase(
                    all_search_results,
                    total_courses,
                    min_words,
                    search_engine,
                    progress_callback,
                    require_keywords=require_keywords,
                )
            except Exception as e:
                logger.error(f"❌ ERROR en fase de tabulación: {str(e)}", exc_info=True)
                self.stats["total_errors"] += 1
                processed_results = []
                if progress_callback:
                    progress_callback(100, f"Error en tabulación: {str(e)}")

            # After tabulation, ensure all results are flushed to disk
            logger.info(
                f"✅ Processo terminado. Resultados procesados: {len(processed_results)}"
            )
            logger.info(f"📊 Actualizando estadísticas finales...")

            # Force save any remaining results
            if len(self.result_manager.results) > len(processed_results):
                logger.warning(
                    f"⚠️  Encontrados {len(self.result_manager.results) - len(processed_results)} resultados pendientes en el cache"
                )

            omitted_file_path = self._save_omitted_to_excel()
            if omitted_file_path:
                logger.info(
                    f"Resultados omitidos guardados en: {os.path.abspath(omitted_file_path)}"
                )
                self.omitted_file = omitted_file_path
            else:
                logger.warning(
                    "No se pudieron guardar los resultados omitidos o no hay resultados omitidos"
                )

            try:
                if hasattr(self.browser_manager, "captcha_solver"):
                    captcha_stats = self.browser_manager.captcha_solver.get_stats()
                    self.stats["captchas_detected"] = captcha_stats[
                        "captcha_detected_count"
                    ]
                    self.stats["captchas_solved"] = captcha_stats[
                        "captcha_solved_count"
                    ]
                    logger.info(
                        f"Estadísticas de CAPTCHAs: Detectados={self.stats['captchas_detected']}, Resueltos={self.stats['captchas_solved']}"
                    )
            except Exception as e:
                logger.error(f"Error actualizando estadísticas de CAPTCHAs: {str(e)}")

            # Verify final file status
            if os.path.exists(output_file):
                final_file_size = os.path.getsize(output_file)
                logger.info(f"📄 Archivo CSV final: {os.path.abspath(output_file)}")
                logger.info(f"📊 Tamaño final del archivo: {final_file_size} bytes")

                # Count lines in CSV to verify record count
                try:
                    with open(output_file, "r", encoding="utf-8") as f:
                        line_count = sum(1 for line in f)

                    logger.info(
                        f"📈 Líneas en el archivo CSV: {line_count - 1 if line_count > 1 else 0}"
                    )

                    if line_count <= 1:
                        logger.warning(
                            f"🗑️ Eliminando archivo vacío (solo cabecera): {os.path.basename(output_file)}"
                        )
                        os.remove(output_file)
                        logger.info(
                            "Archivo eliminado para evitar archivos vacíos en el export."
                        )
                except Exception as e:
                    logger.error(f"❌ Error leyendo el archivo CSV: {e}")
            else:
                logger.error(f"❌ ERROR: Archivo CSV no existe al final: {output_file}")

            logger.info(f"Estadísticas finales: {self.stats}")

            # Compare stats with expected values
            if self.stats["saved_records"] != (line_count - 1 if line_count > 1 else 0):
                logger.warning(
                    f"⚠️  DESAJUSTE: saved_records={self.stats['saved_records']} != líneas en CSV={line_count - 1 if line_count > 1 else 0}"
                )

            if progress_callback:
                captcha_info = (
                    f" | CAPTCHAs: {self.stats['captchas_detected']} detectados, {self.stats['captchas_solved']} resueltos"
                    if self.stats["captchas_detected"] > 0
                    else ""
                )
                progress_callback(
                    100,
                    f"Proceso completado. Se encontraron {len(processed_results)} resultados.{captcha_info}",
                )

            return processed_results

        except Exception as e:
            logger.error(f"Error durante el scraping: {str(e)}")
            logger.error(traceback.format_exc())
            self.stats["total_errors"] += 1

            if progress_callback:
                progress_callback(100, f"Error: {str(e)}")

            return []
