"""
Progress Reporter
-----------------
Clase para informar el progreso durante el proceso de scraping.
"""

import logging
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger(__name__)

class ProgressReporter:
    """
    Maneja y reporta el progreso de los distintos procesos durante el scraping.
    """
    
    def __init__(self):
        """Inicializa el reportador de progreso."""
        self.callback = None
        self.current_course = 0
        self.total_courses = 0
        self.current_result = 0
        self.total_results = 0
        self.phase = 1  # 1 = Búsqueda, 2 = Tabulación
        self.current_tabulation_course = 0
        self.current_tabulation_result = 0
        self.total_tabulation_results = 0
    
    def set_callback(self, callback: Callable):
        """
        Establece la función de callback para reportar progreso.
        
        Args:
            callback: Función de callback
        """
        self.callback = callback
        
    def set_course_counts(self, current: int, total: int):
        """
        Establece el conteo de cursos actual y total.
        
        Args:
            current: Conteo actual
            total: Conteo total
        """
        self.current_course = current
        self.total_courses = total
        logger.debug(f"Progreso del curso: {current}/{total}")
        
    def set_result_counts(self, current: int, total: int):
        """
        Establece el conteo de resultados actual y total.
        
        Args:
            current: Conteo actual
            total: Conteo total
        """
        self.current_result = current
        self.total_results = total
        logger.debug(f"Progreso de resultados: {current}/{total}")
        
    def set_tabulation_course(self, current: int):
        """
        Establece el curso actual en la fase de tabulación.
        
        Args:
            current: Curso actual
        """
        self.current_tabulation_course = current
        logger.debug(f"Curso de tabulación actual: {current}")
        
    def set_phase(self, phase: int):
        """
        Establece la fase actual del proceso.
        
        Args:
            phase: Número de fase (1 = Búsqueda, 2 = Tabulación)
        """
        self.phase = phase
        logger.debug(f"Fase actual: {phase}")
    
    def set_tabulation_result_counts(self, current: int, total: int):
        """
        Establece el conteo de resultados actual y total durante la tabulación.
        
        Args:
            current: Conteo actual
            total: Conteo total
        """
        self.current_tabulation_result = current
        self.total_tabulation_results = total
        logger.debug(f"Progreso de tabulación: {current}/{total}")
        
    def report_progress(self, progress: float, status: str, stats: Dict[str, Any] = None):
        """
        Reporta el progreso actual.
        
        Args:
            progress: Valor de progreso (0-100)
            status: Mensaje de estado
            stats: Estadísticas del proceso
        """
        if self.callback:
            # Determinar qué fase y contadores usar
            if self.phase == 2:  # Tabulación
                current_course = self.current_tabulation_course
            else:  # Búsqueda
                current_course = self.current_course
                
            # Llamar al callback con todos los parámetros
            self.callback(
                progress,
                status,
                stats,
                current_course,
                self.total_courses,
                self.phase
            )
        else:
            # Si no hay callback, registrar en el log
            logger.info(f"Progreso: {progress:.1f}% - {status}")
            
    def report_search_progress(self, search_term: str, sic_code: str, course_name: str, results_count: int = 0) -> str:
        """
        Reporta el progreso durante la búsqueda.
        
        Args:
            search_term: Término de búsqueda
            sic_code: Código SIC actual
            course_name: Nombre del curso actual
            results_count: Cantidad de resultados encontrados
            
        Returns:
            Mensaje de progreso
        """
        # Construir mensaje para fase de búsqueda
        status_message = f"Buscando curso {self.current_course} de {self.total_courses} - {sic_code} - {course_name}"
        
        # Añadir cantidad de resultados si se proporcionan
        if results_count > 0:
            status_message += f" | Encontrados: {results_count} resultados"
        
        # Registrar el mensaje
        logger.info(status_message)
        
        return status_message
    
    def report_processing_progress(self, current: int, total: int, url: str = "") -> str:
        """
        Reporta el progreso durante el procesamiento.
        
        Args:
            current: Índice actual
            total: Total a procesar
            url: URL actual
            
        Returns:
            Mensaje de progreso
        """
        # Construir mensaje para procesamiento
        status_message = f"Procesando {current} de {total}"
        
        # Añadir URL si se proporciona
        if url:
            status_message += f" | URL: {url}"
        
        # Registrar el mensaje
        logger.debug(status_message)
        
        return status_message
    
    def report_tabulation_progress(self, current: int, total: int, sic_code: str = "", course_name: str = "", total_results: int = 0) -> str:
        """
        Reporta el progreso durante la tabulación.
        
        Args:
            current: Índice actual
            total: Total a procesar
            sic_code: Código SIC actual
            course_name: Nombre del curso actual
            total_results: Total de resultados a procesar
            
        Returns:
            Mensaje de progreso
        """
        # Actualizar contadores internos
        self.current_tabulation_result = current
        
        # Construir mensaje para fase de tabulación
        status_message = f"Tabulando curso {self.current_tabulation_course} de {self.total_courses}"
        
        # Añadir información del curso si está disponible
        if sic_code and course_name:
            status_message += f" - {sic_code} - {course_name}"
        
        # Añadir progreso de resultados si está disponible
        if total > 0:
            status_message += f" | Tabulados {current} de {total}"
        
        # Añadir total de resultados a procesar si está disponible
        if total_results > 0:
            status_message += f" | Total resultados: {total_results}"
        
        # Registrar el mensaje
        logger.info(status_message)
        
        return status_message
