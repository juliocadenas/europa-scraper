import asyncio
import logging
import os
import time
import random
from typing import List, Dict, Tuple, Optional, Any, Callable
from datetime import datetime
import re
import traceback

from utils.csv_handler import CSVHandler
from utils.scraper.browser_manager import BrowserManager
from utils.scraper.search_engine import SearchEngine
from utils.scraper.content_extractor import ContentExtractor
from utils.scraper.text_processor import TextProcessor
from utils.scraper.result_manager import ResultManager
from utils.scraper.progress_reporter import ProgressReporter
from utils.scraper.url_utils import URLUtils

logger = logging.getLogger(__name__)

# Crear un handler personalizado para capturar los logs
class LogCaptureHandler(logging.Handler):
    def __init__(self, callback=None):
        super().__init__()
        self.logs = []
        self.callback = callback
        
    def emit(self, record):
        log_entry = self.format(record)
        self.logs.append(log_entry)
        if self.callback:
            self.callback(log_entry)
    
    def get_logs(self):
        return self.logs
    
    def clear(self):
        self.logs = []

# Instanciar el handler global
log_capture_handler = LogCaptureHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_capture_handler.setFormatter(formatter)

# Añadir el handler al logger raíz para capturar todos los logs
root_logger = logging.getLogger()
root_logger.addHandler(log_capture_handler)

async def should_process_result(title: str, description: str, search_term: str, min_words: int, text_processor: TextProcessor) -> bool:
    """
    Determines if a result should be processed based on its title and description.
    """
    text = f"{title} {description}"
    total_words = text_processor.count_all_words(text)
    if total_words < min_words:
        return False

    significant_words = text_processor.get_significant_words(text)
    keyword_counts = text_processor.estimate_keyword_occurrences(text, search_term)
    if not any(count > 0 for count in keyword_counts.values()):
        return False

    return True

class ScraperController:
    """
    Main controller for the USA.gov scraping application.
    Manages the scraping workflow and processes results.
    """
    
    def __init__(self):
        """Initialize the scraper controller."""
        # Initialize components
        self.browser_manager = BrowserManager()
        self.text_processor = TextProcessor()
        # Corregido: Pasar también text_processor al inicializar SearchEngine
        self.search_engine = SearchEngine(self.browser_manager, self.text_processor)
        self.content_extractor = ContentExtractor(self.browser_manager)
        self.result_manager = ResultManager()
        self.progress_reporter = ProgressReporter()
        self.url_utils = URLUtils()
        self.csv_handler = CSVHandler()
        
        # Initialize state
        self.stop_requested = False
        self.processed_urls = set()  # Set to track processed URLs
        self.stats = {
            'total_urls_found': 0,
            'skipped_non_gov': 0,
            'skipped_low_words': 0,
            'skipped_zero_keywords': 0,
            'skipped_duplicates': 0,
            'saved_records': 0,
            'failed_content_extraction': 0,
            'files_not_saved': 0,
            'total_errors': 0
        }
        
        # Variables for progress tracking
        self.total_results_to_process = 0
        self.processed_results_count = 0
        
        # Variables to track the current phase
        self.current_phase = 1  # 1 = Search, 2 = Tabulation
        self.current_tabulation_course = 0  # Counter for tabulation phase
        
        # Callback para logs
        self.log_callback = None
    
    def set_log_callback(self, callback: Callable[[str], None]):
        """
        Establece el callback para recibir logs en tiempo real.
        
        Args:
            callback: Función que recibe un string con el log
        """
        self.log_callback = callback
        # Actualizar el handler global para usar este callback
        log_capture_handler.callback = callback
    
    async def run_scraping(self, params: Dict[str, Any], progress_callback: Callable = None, log_callback: Callable = None) -> List[Dict[str, Any]]:
        """
        Runs the scraping process.
        
        Args:
            params: Scraping parameters
            progress_callback: Callback for progress updates
            log_callback: Callback for log updates
            
        Returns:
            List of result dictionaries
        """
        try:
            # Limpiar logs anteriores
            log_capture_handler.clear()
            
            # Establecer el callback de logs si se proporciona
            if log_callback:
                self.set_log_callback(log_callback)
            
            # Log inicial
            logger.info("=== INICIANDO PROCESO DE SCRAPING ===")
            logger.info(f"Parámetros: {params}")
            
            # Set the progress callback
            self.progress_reporter.set_callback(progress_callback)
            
            # Check if the browser is available
            if not await self.browser_manager.check_playwright_browser():
                logger.error("Browser not available, cannot perform scraping")
                if progress_callback:
                    progress_callback(100, "Error: Browser not available", {'total_errors': 1}, 0, 0)
                return []
            
            # Reset state
            self.stop_requested = False
            self.processed_urls = set()
            self.stats = {
                'total_urls_found': 0,
                'skipped_non_gov': 0,
                'skipped_low_words': 0,
                'skipped_zero_keywords': 0,
                'skipped_duplicates': 0,
                'saved_records': 0,
                'failed_content_extraction': 0,
                'files_not_saved': 0,
                'total_errors': 0
            }
            
            # Reset progress counters
            self.total_results_to_process = 0
            self.processed_results_count = 0
            
            # Reset phase tracking
            self.current_phase = 1
            self.current_tabulation_course = 0  # Reset counter for tabulation phase
            self.progress_reporter.set_phase(1)

            # Counters for courses
            total_courses = 0
            current_course = 0
            
            # Extract parameters
            from_sic = params.get('from_sic')
            to_sic = params.get('to_sic')
            from_course = params.get('from_course', '')
            to_course = params.get('to_course', '')
            min_words = params.get('min_words', 30)
            
            # Validate parameters
            if not from_sic or not to_sic:
                logger.error("Missing required parameters")
                return []
            
            # Log input values for debugging
            logger.info(f"From SIC: {from_sic}, To SIC: {to_sic}")
            logger.info(f"From Course: {from_course}, To Course: {to_course}")
            logger.info(f"Minimum words: {min_words}")
            
            # Initialize output files
            self.result_manager.initialize_output_files(from_sic, to_sic)
            
            if progress_callback:
                # Start with 0% progress
                progress_callback(0, f"CSV file created: {self.result_manager.get_output_file()}", self.stats, 0, 0)
            
            # Load CSV data directly
            self.csv_handler.load_course_data()
            
            # Get all detailed SIC codes with courses
            all_sic_codes_with_courses = self.csv_handler.get_detailed_sic_codes_with_courses()
            
            # If no SIC codes are found, log and return
            if not all_sic_codes_with_courses:
                logger.warning("No detailed SIC codes with courses found in CSV data")
                return []
            
            # Filtrar los cursos que están dentro del rango especificado
            courses_in_range = []
            
            # Añadir todos los cursos dentro del rango (inclusive)
            for sic, course in all_sic_codes_with_courses:
                # Verificar si el código SIC está en el rango especificado
                if self._is_sic_in_range(sic, from_sic, to_sic):
                    courses_in_range.append((sic, course))
                    logger.info(f"Included in range: {sic} - {course}")
                else:
                    logger.debug(f"Excluded from range: {sic} - {course}")
            
            # Log the number of courses found
            logger.info(f"Found {len(courses_in_range)} courses to process")
            
            # Set the total number of courses
            total_courses = len(courses_in_range)
            
            if total_courses == 0:
                logger.warning("No courses found to process")
                return []
            
            # Set course counts in progress reporter
            self.progress_reporter.set_course_counts(0, total_courses)
            
            # PHASE 1: Collect all search results
            all_search_results = []
            
            logger.info("=== FASE 1: BÚSQUEDA DE RESULTADOS ===")
            
            # Process each course to collect results
            for sic_code, course_name in courses_in_range:
                if self.stop_requested:
                    logger.info("Scraping stopped by user")
                    break
              
                current_course += 1
                
                # Update progress reporter
                self.progress_reporter.set_course_counts(current_course, total_courses)
              
                # Show the current SIC code and course name in the progress bar
                current_course_info = f"{sic_code} - {course_name}"
              
                # IMPORTANTE: Usar un formato específico para el mensaje de búsqueda
                if progress_callback:
                    progress_callback(
                        0,
                        f"Buscando curso {current_course} de {total_courses} - {current_course_info}",
                        self.stats,
                        current_course,
                        total_courses,
                        phase=1  # Explicitly indicate we're in phase 1
                    )
                
                # Use the course name as the search term
                search_term = course_name
                
                logger.info(f"Buscando '{search_term}' con código SIC {sic_code} ({current_course}/{total_courses})")
                
                # Perform search with timeout
                try:
                    # Set a timeout for the search
                    search_task = self.search_engine.search_cordis_europa(search_term)
                    search_results = await asyncio.wait_for(search_task, timeout=1800)  # 30 minutes timeout (increased)
                    
                    # Save the results with their course information
                    for result in search_results:
                        result['sic_code'] = sic_code
                        result['course_name'] = course_name
                        result['search_term'] = search_term
                        all_search_results.append(result)
                    
                    # Update statistics
                    self.stats['total_urls_found'] += len(search_results)
                    
                    logger.info(f"Encontrados {len(search_results)} resultados para '{search_term}'")
                    
                    if progress_callback:
                        progress_callback(
                            0,  # Keep at 0% during search
                            f"Buscando curso {current_course} de {total_courses} - {current_course_info} | Encontrados: {len(search_results)} resultados",
                            self.stats,
                            current_course,
                            total_courses,
                            phase=1  # Explicitly indicate we're in phase 1
                        )
                    
                    if not search_results:
                        logger.info(f"No se encontraron resultados para '{search_term}' con código SIC {sic_code}")
                    
                except asyncio.TimeoutError:
                    logger.error(f"Timeout durante la búsqueda de '{search_term}'. Continuando con el siguiente curso.")
                    self.stats['total_errors'] += 1
                    continue
                except Exception as e:
                    logger.error(f"Error durante la búsqueda de '{search_term}': {str(e)}")
                    logger.error(traceback.format_exc())
                    self.stats['total_errors'] += 1
                    continue
            
            # PHASE 2: Process the collected results
            
            # IMPORTANTE: Verificar que realmente tenemos resultados para procesar
            if not all_search_results:
                logger.warning("No se encontraron resultados para procesar")
                if progress_callback:
                    progress_callback(100, "No se encontraron resultados para procesar", self.stats, 0, 0)
                return []
            
            # Set the total number of results to process
            self.total_results_to_process = len(all_search_results)
            self.progress_reporter.set_result_counts(0, self.total_results_to_process)

            # Change to tabulation phase
            self.current_phase = 2
            self.current_tabulation_course = 0  # Reset counter for tabulation phase
            self.progress_reporter.set_phase(2)

            # Log the number of results found
            logger.info(f"=== FASE 2: TABULACIÓN DE RESULTADOS ===")
            logger.info(f"Se encontraron {self.total_results_to_process} resultados totales para procesar")

            # Explicitly notify about the change to tabulation phase with the first course
            if progress_callback and len(courses_in_range) > 0:
                first_sic, first_course = courses_in_range[0]
                # Send an explicit tabulation message for the first course
                progress_callback(
                    0,  # Start at 0% for the processing phase
                    f"Tabulando curso 1 de {total_courses} - {first_sic} - {first_course}",
                    self.stats,
                    1,  # First course in tabulation
                    total_courses,
                    phase=2  # Explicitly indicate we're in phase 2
                )
            
            # Process each result
            for i, result in enumerate(all_search_results):
                if self.stop_requested:
                    logger.info("Scraping detenido por el usuario")
                    break
                
                # Update the tabulation counter
                current_sic_code = result.get('sic_code', '')
                current_course_name = result.get('course_name', '')
                
                # Only increment when the course changes
                if i == 0 or (current_sic_code != all_search_results[i-1].get('sic_code', '') or 
                             current_course_name != all_search_results[i-1].get('course_name', '')):
                    self.current_tabulation_course += 1
                    self.progress_reporter.set_tabulation_course(self.current_tabulation_course)
                    
                    logger.info(f"Tabulando curso {self.current_tabulation_course} de {total_courses}: {current_sic_code} - {current_course_name}")
                    
                    # Update progress with tabulation information
                    if progress_callback:
                        progress_callback(
                            (self.processed_results_count / self.total_results_to_process) * 100,
                            f"Tabulando curso {self.current_tabulation_course} de {total_courses} - {current_sic_code} - {current_course_name}",
                            self.stats,
                            self.current_tabulation_course,
                            total_courses,
                            phase=2  # Explicitly indicate we're in phase 2
                        )
                
                # Extract information from the result
                sic_code = result.get('sic_code', '')
                course_name = result.get('course_name', '')
                search_term = result.get('search_term', '')
                title = result.get('title', 'No Title')
                url = result.get('url', '')
                description = result.get('description', 'No Description')

                # Early filtering based on title and description
                should_process = await should_process_result(title, description, search_term, min_words, self.text_processor)
                if not should_process:
                    logger.info(f"Omitiendo URL por filtro de título/descripción: {url}")
                    self.stats['skipped_low_words'] += 1  # Or a new counter like 'skipped_early_filter'
                    self.stats['files_not_saved'] += 1

                    # Record in omitted results
                    self.result_manager.add_omitted_result(
                        {
                            'sic_code': sic_code,
                            'course_name': course_name,
                            'title': title,
                            'url': url,
                            'description': description
                        },
                        "Filtro de título/descripción"
                    )

                    # Increment processed results counter
                    self.processed_results_count += 1
                    self.progress_reporter.set_result_counts(self.processed_results_count, self.total_results_to_process)

                    # Update progress
                    if progress_callback:
                        progress_percentage = (self.processed_results_count / self.total_results_to_process) * 100
                        progress_callback(
                            progress_percentage,
                            f"Tabulando curso {self.current_tabulation_course} de {total_courses} - {current_sic_code} - {current_course_name} | Procesando {self.processed_results_count} de {self.total_results_to_process} URL: {url}",
                            self.stats,
                            self.current_tabulation_course,
                            total_courses,
                            phase=2  # Explicitly indicate we're in phase 2
                        )
                    continue
                
                # Mark the URL as processed
                self.processed_urls.add(url)
                
                if not url:
                    # Increment processed results counter
                    self.processed_results_count += 1
                    self.progress_reporter.set_result_counts(self.processed_results_count, self.total_results_to_process)
                    continue
                
                # Update progress for each URL
                if progress_callback:
                    progress_percentage = (self.processed_results_count / self.total_results_to_process) * 100
                    progress_callback(
                        progress_percentage,
                        f"Tabulando curso {self.current_tabulation_course} de {total_courses} - {current_sic_code} - {current_course_name} | Procesando {self.processed_results_count+1} de {self.total_results_to_process} URL: {url}",
                        self.stats,
                        self.current_tabulation_course,
                        total_courses,
                        phase=2  # Explicitly indicate we're in phase 2
                    )
                
                try:
                    # Extract full content from the URL with timeout
                    logger.info(f"Extrayendo contenido completo de: {url}")
                    
                    try:
                        # Set a timeout for content extraction
                        extract_task = self.content_extractor.extract_full_content(url)
                        full_content = await asyncio.wait_for(extract_task, timeout=180)  # 3 minutes timeout
                        
                        if not full_content:
                            logger.warning(f"No se pudo extraer contenido de: {url}")
                            self.stats['failed_content_extraction'] += 1
                            self.stats['files_not_saved'] += 1
                            
                            # Record in omitted results
                            self.result_manager.add_omitted_result(
                                {
                                    'sic_code': sic_code,
                                    'course_name': course_name,
                                    'title': title,
                                    'url': url,
                                    'description': description
                                },
                                "Error en extracción de contenido"
                            )
                            
                            # Increment processed results counter
                            self.processed_results_count += 1
                            self.progress_reporter.set_result_counts(self.processed_results_count, self.total_results_to_process)
                            
                            # Update progress
                            if progress_callback:
                                progress_percentage = (self.processed_results_count / self.total_results_to_process) * 100
                                progress_callback(
                                    progress_percentage,
                                    f"Tabulando curso {self.current_tabulation_course} de {total_courses} - {current_sic_code} - {current_course_name} | Procesando {self.processed_results_count} de {self.total_results_to_process} URL: {url}",
                                    self.stats,
                                    self.current_tabulation_course,
                                    total_courses,
                                    phase=2  # Explicitly indicate we're in phase 2
                                )
                            
                            continue
                        
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout durante la extracción de contenido de {url}. Omitiendo URL.")
                        self.stats['failed_content_extraction'] += 1
                        self.stats['total_errors'] += 1
                        self.stats['files_not_saved'] += 1
                        
                        # Record in omitted results
                        self.result_manager.add_omitted_result(
                            {
                                'sic_code': sic_code,
                                'course_name': course_name,
                                'title': title,
                                'url': url,
                                'description': description
                            },
                            "Timeout en extracción de contenido"
                        )
                        
                        # Increment processed results counter
                        self.processed_results_count += 1
                        self.progress_reporter.set_result_counts(self.processed_results_count, self.total_results_to_process)
                        
                        # Update progress
                        if progress_callback:
                            progress_percentage = (self.processed_results_count / self.total_results_to_process) * 100
                            progress_callback(
                                progress_percentage,
                                f"Tabulando curso {self.current_tabulation_course} de {total_courses} - {current_sic_code} - {current_course_name} | Procesando {self.processed_results_count} de {self.total_results_to_process} URL: {url}",
                                self.stats,
                                self.current_tabulation_course,
                                total_courses,
                                phase=2  # Explicitly indicate we're in phase 2
                            )
                        
                        continue
                    
                    # Count all words in the full content
                    total_words = self.text_processor.count_all_words(full_content)
                    
                    # Count occurrences of keywords from the search term
                    word_counts = self.text_processor.estimate_keyword_occurrences(full_content, search_term)
                    
                    # Check if the result should be excluded
                    should_exclude, exclude_reason = self.text_processor.should_exclude_result(total_words, word_counts, min_words)
                    
                    if should_exclude:
                        if "total words" in exclude_reason.lower():
                            logger.info(f"Excluyendo URL por bajo conteo de palabras: {url} - {exclude_reason}")
                            self.stats['skipped_low_words'] += 1
                            self.stats['files_not_saved'] += 1
                            
                            # Record in omitted results
                            self.result_manager.add_omitted_result(
                                {
                                    'sic_code': sic_code,
                                    'course_name': course_name,
                                    'title': title,
                                    'url': url,
                                    'description': description
                                },
                                f"Bajo conteo de palabras: {total_words}"
                            )
                        else:
                            logger.info(f"Excluyendo URL por conteo cero de palabras clave: {url} - {exclude_reason}")
                            self.stats['skipped_zero_keywords'] += 1
                            self.stats['files_not_saved'] += 1
                            
                            # Record in omitted results
                            self.result_manager.add_omitted_result(
                                {
                                    'sic_code': sic_code,
                                    'course_name': course_name,
                                    'title': title,
                                    'url': url,
                                    'description': description
                                },
                                "Sin coincidencias de palabras clave"
                            )
                        
                        # Increment processed results counter
                        self.processed_results_count += 1
                        self.progress_reporter.set_result_counts(self.processed_results_count, self.total_results_to_process)
                        
                        # Update progress
                        if progress_callback:
                            progress_percentage = (self.processed_results_count / self.total_results_to_process) * 100
                            progress_callback(
                                progress_percentage,
                                f"Tabulando curso {self.current_tabulation_course} de {total_courses} - {current_sic_code} - {current_course_name} | Procesando {self.processed_results_count} de {self.total_results_to_process} URL: {url}",
                                self.stats,
                                self.current_tabulation_course,
                                total_courses,
                                phase=2  # Explicitly indicate we're in phase 2
                            )
                        
                        continue
                    
                    # Format the word count
                    formatted_word_counts = self.text_processor.format_word_counts(total_words, word_counts)
                    
                    # Check if it only contains "Total words: X" without keyword matches
                    if formatted_word_counts.startswith("Total words:") and len(formatted_word_counts.split("|")) == 1:
                        logger.info(f"Excluyendo URL sin coincidencias de palabras clave: {url}")
                        self.stats['skipped_zero_keywords'] += 1
                        self.stats['files_not_saved'] += 1
                        
                        # Record in omitted results
                        self.result_manager.add_omitted_result(
                            {
                                'sic_code': sic_code,
                                'course_name': course_name,
                                'title': title,
                                'url': url,
                                'description': description
                            },
                            "Sin coincidencias de palabras clave"
                        )
                        
                        # Increment processed results counter
                        self.processed_results_count += 1
                        self.progress_reporter.set_result_counts(self.processed_results_count, self.total_results_to_process)
                        
                        # Update progress
                        if progress_callback:
                            progress_percentage = (self.processed_results_count / self.total_results_to_process) * 100
                            progress_callback(
                                progress_percentage,
                                f"Tabulando curso {self.current_tabulation_course} de {total_courses} - {current_sic_code} - {current_course_name} | Procesando {self.processed_results_count} de {self.total_results_to_process} URL: {url}",
                                self.stats,
                                self.current_tabulation_course,
                                total_courses,
                                phase=2  # Explicitly indicate we're in phase 2
                            )
                        
                        continue
                    
                    # Clean the description of URLs and other unwanted elements
                    description = self.text_processor.clean_description(description)

                    # If the description is very short, try to use part of the full content
                    if len(description) < 100 and full_content:
                        # Take the first 1000 characters of the full content
                        content_preview = full_content[:1000]
                        # Clean the content of URLs and other unwanted elements
                        content_preview = self.text_processor.clean_description(content_preview)
                        
                        # If the content is significantly longer than the description, use it
                        if len(content_preview) > len(description) * 2:
                            description = content_preview
                    
                    # Create a record for each result
                    result_data = {
                        'sic_code': sic_code,
                        'course_name': course_name,
                        'title': title,
                        'description': description,
                        'url': url,
                        'total_words': formatted_word_counts
                    }
                    
                    # Add to the result manager
                    self.result_manager.add_result(result_data)
                    self.stats['saved_records'] += 1
                    
                    logger.info(f"Resultado guardado: {title} - {url}")
                    
                    # Increment processed results counter
                    self.processed_results_count += 1
                    self.progress_reporter.set_result_counts(self.processed_results_count, self.total_results_to_process)
                    
                    # Update progress
                    if progress_callback:
                        progress_percentage = (self.processed_results_count / self.total_results_to_process) * 100
                        progress_callback(
                            progress_percentage,
                            f"Tabulando curso {self.current_tabulation_course} de {total_courses} - {current_sic_code} - {current_course_name} | Procesando {self.processed_results_count} de {self.total_results_to_process} URL: {url}",
                            self.stats,
                            self.current_tabulation_course,
                            total_courses,
                            phase=2  # Explicitly indicate we're in phase 2
                        )
                    
                    # Small pause to avoid overload
                    await asyncio.sleep(random.uniform(0.5, 1))
                    
                except Exception as e:
                    logger.error(f"Error procesando URL {url}: {str(e)}")
                    logger.error(traceback.format_exc())
                    self.stats['failed_content_extraction'] += 1
                    self.stats['total_errors'] += 1
                    self.stats['files_not_saved'] += 1
                    
                    # Record in omitted results
                    self.result_manager.add_omitted_result(
                        {
                            'sic_code': sic_code,
                            'course_name': course_name,
                            'title': title,
                            'url': url,
                            'description': description
                        },
                        f"Error en extracción de contenido: {str(e)}"
                    )
                    
                    # Increment processed results counter
                    self.processed_results_count += 1
                    self.progress_reporter.set_result_counts(self.processed_results_count, self.total_results_to_process)
                    
                    # Update progress
                    if progress_callback:
                        progress_percentage = (self.processed_results_count / self.total_results_to_process) * 100
                        progress_callback(
                            progress_percentage,
                            f"Tabulando curso {self.current_tabulation_course} de {total_courses} - {current_sic_code} - {current_course_name} | Procesando {self.processed_results_count} de {self.total_results_to_process} URL: {url}",
                            self.stats,
                            self.current_tabulation_course,
                            total_courses,
                            phase=2  # Explicitly indicate we're in phase 2
                        )
            
            # Save omitted results to Excel
            omitted_results = self.result_manager.get_omitted_results()
            if omitted_results:
                self.result_manager.save_omitted_to_excel()
                logger.info(f"Resultados omitidos guardados en: {os.path.abspath(self.result_manager.get_omitted_file())}")
                
                # Update final progress message
                if progress_callback:
                    progress_callback(
                        100, 
                        f"Proceso completado. Se encontraron {len(self.result_manager.get_results())} resultados y se omitieron {len(omitted_results)}.",
                        self.stats
                    )
            
            # Make sure to close resources
            try:
                await self.browser_manager.close()
            except Exception as e:
                logger.error(f"Error cerrando recursos: {str(e)}")
                logger.error(traceback.format_exc())
            try:
                await self.browser_manager.close()
            except Exception as e:
                logger.error(f"Error cerrando recursos: {str(e)}")
                logger.error(traceback.format_exc())
                self.stats['total_errors'] += 1
            
            # Mostrar resultados finales en el log
            logger.info("=== RESULTADOS FINALES ===")
            logger.info(f"Resultados guardados en: {os.path.abspath(self.result_manager.get_output_file())}")
            logger.info(f"Total de resultados guardados: {self.stats['saved_records']}")
            logger.info(f"Total de resultados omitidos: {len(omitted_results)}")
            logger.info(f"Estadísticas finales: {self.stats}")

            # Update final progress
            if progress_callback:
                progress_callback(
                    100, 
                    f"Proceso completado. Se encontraron {len(self.result_manager.get_results())} resultados.",
                    self.stats
                )

            return self.result_manager.get_results()
            
        except Exception as e:
            logger.error(f"Error durante el scraping: {str(e)}")
            logger.error(traceback.format_exc())
            self.stats['total_errors'] += 1
            
            # Try to close resources even in case of error
            try:
                await self.browser_manager.close()
            except Exception as close_error:
                logger.error(f"Error cerrando el navegador después de un error: {str(close_error)}")
                logger.error(traceback.format_exc())
                self.stats['total_errors'] += 1
            
            if progress_callback:
                progress_callback(100, f"Error: {str(e)}", self.stats, 0, 0)
            
            return []
    
    def stop_scraping(self):
        """Stops the scraping process."""
        self.stop_requested = True
        logger.info("Detención solicitada por el usuario")

    def _is_sic_in_range(self, sic: str, from_sic: str, to_sic: str) -> bool:
        """
        Verifies if a SIC code is within a specified range (inclusive).
        
        Args:
            sic: The SIC code to check.
            from_sic: The starting SIC code of the range.
            to_sic: The ending SIC code of the range.
            
        Returns:
            True if the SIC code is within the range, False otherwise.
        """
        # Si es exactamente igual a alguno de los límites, está en el rango
        if sic == from_sic or sic == to_sic:
            return True
            
        # Comparación simple para códigos SIC
        return from_sic <= sic <= to_sic
    
    def get_logs(self):
        """
        Obtiene todos los logs capturados hasta el momento.
        
        Returns:
            Lista de strings con los logs
        """
        return log_capture_handler.get_logs()
