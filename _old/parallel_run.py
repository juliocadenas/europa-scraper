#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Orquestador de Scraping Paralelo
=================================
Este script divide el trabajo de scraping en múltiples procesos para aprovechar
todos los núcleos de la CPU.

Uso:
- Modificar la constante NUM_PROCESSES al número de hilos de CPU deseados.
- Ejecutar `python parallel_run.py` desde la raíz del proyecto.
"""

import os
import sys
import multiprocessing
import logging
import math
from typing import List, Tuple, Dict, Any

# Añadir el directorio raíz al path para asegurar que las importaciones funcionen
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logger import setup_logger
from utils.sqlite_handler import SQLiteHandler
from controllers.scraper_controller import ScraperController
from utils.config import Config
from utils.scraper.browser_manager import BrowserManager

# --- Configuración Principal ---
# IMPORTANTE: Ajusta este valor al número de procesos paralelos que deseas.
# Para tu servidor de 48 hilos, 48 es un buen punto de partida.
NUM_PROCESSES = 4 

# Parámetros por defecto para cada tarea de scraping.
# Estos pueden ser sobrescritos o extendidos si es necesario.
DEFAULT_SCRAPING_PARAMS = {
    "from_course": "",
    "to_course": "",
    "min_words": 30,
    "search_engine": "Wayback Machine",
    "site_domain": "usda.gov",
    "is_headless": True,
    "gov_only": True
}

def get_all_sic_codes() -> List[Tuple[str, str, str, str]]:
    """
    Obtiene todos los códigos SIC y nombres de cursos de la base de datos.
    """
    db_path = os.path.join(project_root, 'courses.db')
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"La base de datos 'courses.db' no se encontró en la ruta: {db_path}")
    
    db_handler = SQLiteHandler(db_path)
    # Usamos get_detailed_sic_codes_with_courses que devuelve tuplas
    # (sic_code, course_name, status, server)
    all_courses = db_handler.get_detailed_sic_codes_with_courses()
    return all_courses

def split_into_chunks(data: List, num_chunks: int) -> List[List]:
    """Divide una lista en un número específico de fragmentos (chunks)."""
    if not data or num_chunks <= 0:
        return []
    chunk_size = math.ceil(len(data) / num_chunks)
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

def worker_run_scraping(worker_id: int, sic_chunk: List[Tuple[str, str, str, str]], params: Dict[str, Any]):
    """
    Función ejecutada por cada proceso trabajador.
    
    Args:
        worker_id: Identificador único para el trabajador (ej: 0, 1, 2...).
        sic_chunk: El fragmento de códigos SIC que este trabajador debe procesar.
        params: Diccionario de parámetros para la tarea de scraping.
    """
    # Configurar un logger específico para este trabajador para evitar conflictos
    log_dir = os.path.join(project_root, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'worker_{worker_id}.log')
    logger = setup_logger(logging.INFO, log_file)
    
    logger.info(f"Worker {worker_id} iniciado. Procesando {len(sic_chunk)} códigos SIC.")
    
    if not sic_chunk:
        logger.warning(f"Worker {worker_id} recibió un chunk vacío. Terminando.")
        return

    # Extraer el primer y último código SIC del chunk para nombrar archivos
    from_sic = sic_chunk[0][0]
    to_sic = sic_chunk[-1][0]
    
    # Fusionar parámetros por defecto con los específicos del chunk
    task_params = DEFAULT_SCRAPING_PARAMS.copy()
    task_params['from_sic'] = from_sic
    task_params['to_sic'] = to_sic
    task_params.update(params) # Permite sobrescribir cualquier parámetro

    # *** Inicialización de Componentes por Proceso ***
    # Cada proceso debe tener sus propias instancias para evitar conflictos.
    config_manager = Config(config_file=os.path.join(project_root, 'client', 'config.json'))
    # Pasamos None para ServerState ya que no hay servidor API en este modo
    browser_manager = BrowserManager(config_manager=config_manager, server_state=None) 
    scraper_controller = ScraperController(config_manager=config_manager, browser_manager=browser_manager)

    try:
        logger.info(f"Worker {worker_id}: Iniciando `run_scraping` para el rango {from_sic} a {to_sic}.")
        
        # Creamos una función de callback simple para el progreso
        def progress_callback(percentage, message, *args):
            logger.info(f"Worker {worker_id} [Progreso: {percentage:.2f}%]: {message}")

        # run_scraping es una corutina, necesitamos ejecutarla en un bucle de eventos asyncio
        asyncio.run(scraper_controller.run_scraping(
            params=task_params,
            progress_callback=progress_callback,
            worker_id=worker_id
        ))
        
        logger.info(f"Worker {worker_id}: Tarea completada para el rango {from_sic} a {to_sic}.")

    except Exception as e:
        logger.error(f"Worker {worker_id}: Ha ocurrido un error catastrófico.", exc_info=True)
    finally:
        logger.info(f"Worker {worker_id}: Finalizado.")


if __name__ == "__main__":
    # --- Punto de Entrada Principal ---
    main_logger = setup_logger(logging.INFO, 'logs/orchestrator.log')
    main_logger.info("--- INICIANDO ORQUESTADOR DE SCRAPING PARALELO ---")
    
    try:
        # 1. Obtener todos los códigos a procesar
        all_codes = get_all_sic_codes()
        main_logger.info(f"Se encontraron {len(all_codes)} códigos SIC en total en la base de datos.")
        
        if not all_codes:
            main_logger.error("No se encontraron códigos SIC para procesar. Abortando.")
            sys.exit(1)

        # 2. Dividir los códigos en fragmentos para cada proceso
        sic_chunks = split_into_chunks(all_codes, NUM_PROCESSES)
        main_logger.info(f"Trabajo dividido en {len(sic_chunks)} fragmentos para {NUM_PROCESSES} procesos.")
        
        # 3. Preparar los argumentos para cada trabajador
        #    Usamos un diccionario vacío para los parámetros específicos por ahora
        tasks = [(i, chunk, {}) for i, chunk in enumerate(sic_chunks)]

        # 4. Iniciar el pool de procesos
        #    Usaremos 'spawn' como contexto de inicio para compatibilidad entre plataformas (especialmente Windows)
        #    y para un aislamiento más limpio, aunque 'fork' (default en Linux) es más rápido.
        multiprocessing.set_start_method('spawn', force=True)
        
        with multiprocessing.Pool(processes=NUM_PROCESSES) as pool:
            main_logger.info(f"Iniciando un pool de {NUM_PROCESSES} procesos trabajadores...")
            # Usamos starmap para pasar múltiples argumentos a la función worker
            pool.starmap(worker_run_scraping, tasks)

        main_logger.info("--- TODOS LOS TRABAJADORES HAN FINALIZADO ---")

    except Exception as e:
        main_logger.error("Ha ocurrido un error en el orquestador principal.", exc_info=True)

