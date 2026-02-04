#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Clase del Servidor Principal del Scraper Europa
==============================================
Encapsula la lógica y el estado del servidor FastAPI, actuando como
un orquestador de scraping multiproceso.
"""

import os
import sys
import asyncio
import logging
import socket
import time
import multiprocessing
import threading
from multiprocessing.managers import SyncManager
from queue import Empty
from typing import Dict, Any, Optional, List, Tuple
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager
import pandas as pd
import io
import random
import zipfile

# --- Añadir raíz del proyecto al path ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# --- Importaciones de Módulos del Proyecto ---
from utils.logger import setup_logger
from utils.config import Config
from utils.sqlite_handler import SQLiteHandler
from controllers.scraper_controller import ScraperController
from utils.scraper.browser_manager import BrowserManager
from utils.proxy_manager import ProxyManager

# --- Constantes ---
NUM_PROCESSES = os.cpu_count() or 4  # Usar todos los núcleos disponibles, o 4 como fallback
BATCH_SIZE = 10  # Número de cursos a procesar por lote

# --- Modelos de Datos (Pydantic) ---
class ScrapingJob(BaseModel):
    from_sic: str
    to_sic: str
    search_engine: str = 'Cordis Europa'
    site_domain: Optional[str] = None
    is_headless: bool = True
    min_words: int = 30
    num_workers: Optional[int] = None

# ==============================================================================
# FUNCIÓN DEL TRABAJADOR (WORKER) - Se ejecuta en un proceso separado
# ==============================================================================
def worker_process(
    worker_id: int,
    work_queue: multiprocessing.JoinableQueue,
    status_dict: Dict,
    config_path: str
):
    """
    Función principal para cada proceso trabajador del pool.
    Extrae lotes de la cola de trabajo y ejecuta el scraping.
    """
    # Configurar un logger y estado inicial para este trabajador
    log_dir = os.path.join(project_root, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'worker_{worker_id}.log')
    logger = setup_logger(logging.INFO, log_file)
    status_dict[worker_id] = {'id': worker_id, 'status': 'Idle', 'progress': 0, 'current_task': 'Esperando tarea'}
    
    logger.info(f"Worker {worker_id} iniciado.")

    # --- Inicialización de componentes por proceso ---
    # Cada proceso necesita sus propias instancias para evitar conflictos.
    config_manager = Config(config_file=config_path)
    browser_manager = None
    scraper_controller = None
    browser_initialized = False
    
    # Estadísticas acumulativas para la sesión del worker
    cumulative_stats = {
        'processed_count': 0,
        'omitted_count': 0,
        'error_count': 0
    }

    # --- Inicialización del bucle de eventos para el worker ---
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # El bucle principal del trabajador
    while True:
        try:
            # Obtener un lote de trabajo de la cola
            logger.info(f"Worker {worker_id}: Esperando por un trabajo en la cola...")
            work_item = work_queue.get()
            logger.info(f"Worker {worker_id}: ¡Ha recibido un trabajo de la cola!")
            
            if work_item is None:  # Señal de finalización
                logger.info(f"Worker {worker_id} recibió señal de finalización.")
                status_dict[worker_id] = {'id': worker_id, 'status': 'idle', 'progress': 0, 'current_task': 'Shutdown'}
                break
            
            batch, job_params = work_item

            # --- Inicializar navegador y controlador en la primera tarea ---
            if not browser_initialized:
                status_dict[worker_id] = {'id': worker_id, 'status': 'Initializing', 'progress': 0, 'current_task': 'Iniciando navegador...'}
                logger.info(f"Worker {worker_id}: Inicializando componentes para la primera tarea.")
                # Crear un server_state simulado para los workers
                class WorkerServerState:
                    def __init__(self):
                        self.captcha_solution_queue = multiprocessing.Queue()
                    
                    def set_pending_captcha_challenge(self, challenge):
                        logger.info(f"CAPTCHA challenge detectado en worker: {challenge}")
                
                worker_server_state = WorkerServerState()
                
                # --- Configuración de Proxies ---
                proxy_manager = ProxyManager()
                if config_manager.get('proxy_enabled', False):
                    proxy_manager.enable(True)
                    proxy_list_str = config_manager.get('proxy_list', '')
                    if proxy_list_str:
                        proxies = [p.strip() for p in proxy_list_str.split('\n') if p.strip()]
                        proxy_manager.set_proxies(proxies)
                    
                    proxy_manager.set_rotation_enabled(config_manager.get('proxy_rotation', True))
                    proxy_manager.set_timeout(int(config_manager.get('proxy_timeout', 30)))
                    logger.info(f"Worker {worker_id}: Proxies habilitados. {len(proxy_manager.proxies)} proxies cargados.")
                else:
                    logger.info(f"Worker {worker_id}: Proxies deshabilitados.")

                browser_manager = BrowserManager(config_manager=config_manager, server_state=worker_server_state)
                browser_manager.set_proxy_manager(proxy_manager)
                
                try:
                    # Usar el parámetro 'is_headless' del trabajo recibido
                    # Usar el parámetro 'is_headless' del trabajo recibido, pero forzar True en Linux
                    is_headless_param = job_params.get('is_headless', True)
                    search_engine_param = job_params.get('search_engine', 'Cordis Europa')
                    
                    if sys.platform.startswith('linux'):
                        is_headless = True
                        if not is_headless_param:
                            logger.warning(f"Worker {worker_id}: Forzando headless=True en Linux (solicitado: {is_headless_param})")
                    else:
                        is_headless = is_headless_param

                    if search_engine_param == 'Cordis Europa API':
                        logger.info(f"Worker {worker_id}: Modo API detectado ({search_engine_param}). Omitiendo inicialización de navegador.")
                    else:
                        logger.info(f"Worker {worker_id}: Modo headless = {is_headless}")
                        loop.run_until_complete(browser_manager.initialize(headless=is_headless))
                        logger.info(f"Worker {worker_id}: Navegador inicializado correctamente")
                except Exception as e:
                    logger.error(f"Worker {worker_id}: Error inicializando navegador: {e}", exc_info=True)
                    # Si el navegador falla, no podemos continuar
                    status_dict[worker_id] = {'id': worker_id, 'status': 'Error', 'progress': 0, 'current_task': 'Browser Init Failed'}
                    work_queue.task_done()
                    continue

                scraper_controller = ScraperController(config_manager=config_manager, browser_manager=browser_manager)
                browser_initialized = True

            # Si el navegador no se inicializó, no podemos continuar
            if not scraper_controller or not browser_manager:
                logger.error(f"Worker {worker_id}: Controlador o BrowserManager no inicializados, saltando lote.")
                work_queue.task_done()
                continue
            
            batch_id = f"{batch[0][0]}..{batch[-1][0]}"
            logger.info(f"Worker {worker_id} recibió lote {batch_id} con {len(batch)} cursos y parámetros: {job_params}")
            status_dict[worker_id] = {
                'id': worker_id, 
                'status': 'working', 
                'progress': 0, 
                'current_task': batch_id,
                'processed_count': cumulative_stats['processed_count'],
                'omitted_count': cumulative_stats['omitted_count'],
                'error_count': cumulative_stats['error_count']
            }
            
            # --- Lógica de Scraping para el Lote ---
            # El ScraperController espera un rango, no un lote.
            # Combinamos los parámetros del trabajo original con la info del lote.
            params = job_params.copy()
            params.update({
                'from_sic': batch[0][0],
                'to_sic': batch[-1][0],
                'from_course': batch[0][1],
                'to_course': batch[-1][1],
            })

            def progress_callback(percentage, message, *args):
                # Actualizar el progreso del trabajador
                current_status = {
                    'id': worker_id, 
                    'status': 'working', 
                    'progress': percentage, 
                    'current_task': message
                }
                
                # Si se pasan estadísticas (desde scraper_controller), actualizarlas sumando acumulados
                if args and isinstance(args[0], dict):
                    stats = args[0]
                    current_status.update({
                        'processed_count': cumulative_stats['processed_count'] + stats.get('saved_records', 0),
                        'omitted_count': cumulative_stats['omitted_count'] + stats.get('files_not_saved', 0),
                        'error_count': cumulative_stats['error_count'] + stats.get('total_errors', 0)
                    })
                # Si no hay stats nuevos, mantener los anteriores
                else:
                    previous = status_dict.get(worker_id, {})
                    current_status.update({
                        'processed_count': previous.get('processed_count', 0),
                        'omitted_count': previous.get('omitted_count', 0),
                        'error_count': previous.get('error_count', 0)
                    })
                
                status_dict[worker_id] = current_status
            
            # run_scraping es una corutina, la ejecutamos en el bucle de eventos del worker.
            loop.run_until_complete(scraper_controller.run_scraping(
                params=params,
                progress_callback=progress_callback,
                worker_id=worker_id
            ))

            logger.info(f"Worker {worker_id} completó el lote {batch_id}.")
            work_queue.task_done()

            # Obtener estadísticas reales del lote actual
            batch_stats = scraper_controller.stats
            batch_processed = batch_stats.get('saved_records', 0)
            batch_omitted = batch_stats.get('files_not_saved', 0)
            batch_error = batch_stats.get('total_errors', 0)

            # Actualizar acumulados
            cumulative_stats['processed_count'] += batch_processed
            cumulative_stats['omitted_count'] += batch_omitted
            cumulative_stats['error_count'] += batch_error

            # Crear mensaje de estado final detallado
            finished_task_description = (
                f"Completado: {batch_id}. "
                f"Total Procesados: {cumulative_stats['processed_count']}, Total Omitidos: {cumulative_stats['omitted_count']}, Total Errores: {cumulative_stats['error_count']}."
            )

            status_dict[worker_id] = {
                'id': worker_id, 
                'status': 'Completed', 
                'progress': 100, 
                'current_task': finished_task_description,
                'completion_time': time.time(),
                'processed_count': cumulative_stats['processed_count'],
                'omitted_count': cumulative_stats['omitted_count'],
                'error_count': cumulative_stats['error_count']
            }

        except Empty:
            # Esto no debería ocurrir con un `get()` bloqueante, pero es una salvaguarda
            logger.info(f"Worker {worker_id}: Cola de trabajo vacía. Esperando...")
            time.sleep(1)
        except Exception:
            logger.error(f"Worker {worker_id}: Error catastrófico.", exc_info=True)
            status_dict[worker_id] = {'id': worker_id, 'status': 'Error', 'progress': 0, 'current_task': 'CRASHED'}
            # Marcar la tarea como hecha para no bloquear la cola si hay un error
            if 'work_queue' in locals() and isinstance(work_queue, multiprocessing.queues.JoinableQueue):
                work_queue.task_done()


# --- Clase Principal del Servidor ---
class ScraperServer:
    def __init__(self, host="0.0.0.0", port=8001):
        self.host = host
        self.port = port
        self.logger = setup_logger(logging.DEBUG, 'logs/server.log')
        self.config_path = os.path.join(project_root, 'client', 'config.json')

        # --- Gestor de Multiprocesamiento ---
        # Se necesita un SyncManager para compartir objetos (dict, queue) entre procesos.
        self.manager: Optional[SyncManager] = None
        self.worker_pool: List[multiprocessing.Process] = []
        self.work_queue: Optional[multiprocessing.JoinableQueue] = None
        self.worker_states: Optional[Dict] = None

        # --- Bandera de Estado Global ---
        self.is_job_running = False
        
        self.app = FastAPI(
            title="Europa Scraper Server",
            version="3.0.0",
            lifespan=self._lifespan
        )
        self._setup_routes()

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        await self._startup()
        yield
        await self._shutdown()

    async def _startup(self):
        self.logger.info("Iniciando servidor y gestor de multiprocesamiento...")
        # Forzar el método de inicio a 'spawn' para compatibilidad y seguridad
        multiprocessing.set_start_method('spawn', force=True)
        self.manager = multiprocessing.Manager()
        self.worker_states = self.manager.dict()
        self.work_queue = multiprocessing.JoinableQueue()
        self.is_job_running = False
        
        # Iniciar broadcasting para descubrimiento de clientes
        self._start_broadcasting()
        
        # Iniciar el hilo de limpieza para workers finalizados
        self.cleanup_stop_event = threading.Event()
        self.cleanup_thread = threading.Thread(target=self._cleanup_finished_workers, daemon=True)
        self.cleanup_thread.start()
        self.logger.info("Iniciado el monitor de limpieza de workers.")
        # No iniciamos el pool aquí, se inicia bajo demanda.

    async def _shutdown(self):
        self.logger.info("Deteniendo el pool de trabajadores...")
        self._stop_worker_pool()
        self._stop_broadcasting()
        if hasattr(self, 'cleanup_stop_event'):
            self.cleanup_stop_event.set()
        if self.manager:
            self.logger.info("Cerrando el gestor de multiprocesamiento...")
            self.manager.shutdown()

    def _start_worker_pool(self, num_workers: int):
        if self.worker_pool:
            self.logger.warning("El pool de trabajadores ya está en ejecución. No se iniciará de nuevo.")
            return

        self.logger.info(f"Iniciando un pool de {num_workers} procesos trabajadores...")
        self.worker_pool = [
            multiprocessing.Process(
                target=worker_process,
                args=(i, self.work_queue, self.worker_states, self.config_path)
            ) for i in range(num_workers)
        ]
        for p in self.worker_pool:
            p.start()

    def _stop_worker_pool(self):
        if not self.worker_pool:
            return
        
        self.logger.info("Enviando señal de finalización a todos los trabajadores...")
        for _ in self.worker_pool:
            self.work_queue.put(None) # Enviar una señal de "veneno" por cada trabajador

        for p in self.worker_pool:
            p.join(timeout=10) # Esperar a que los procesos terminen
            if p.is_alive():
                self.logger.warning(f"El trabajador {p.pid} no terminó a tiempo, forzando terminación.")
                p.terminate()

        self.worker_pool = []
        self.is_job_running = False
        self.logger.info("Pool de trabajadores detenido.")

    def _start_broadcasting(self):
        """Inicia el broadcasting para descubrimiento de clientes."""
        self.broadcast_thread = threading.Thread(target=self._broadcast_server_presence, daemon=True)
        self.broadcast_thread.start()
        self.logger.info("Iniciado broadcasting de presencia del servidor")

    def _stop_broadcasting(self):
        """Detiene el broadcasting."""
        if hasattr(self, 'broadcast_thread') and self.broadcast_thread.is_alive():
            self.logger.info("Deteniendo broadcasting del servidor")
        
    def _broadcast_server_presence(self):
        """Envia broadcasts periódicos para que los clientes puedan descubrir el servidor."""
        BROADCAST_PORT = 6000
        BROADCAST_INTERVAL = 5  # segundos
        
        # Obtener la IP local real para el broadcasting
        try:
            # Crear un socket para determinar la IP local
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
        except Exception:
            local_ip = "127.0.0.1"
        
        message = f"EUROPA_SCRAPER_SERVER;{local_ip};{self.port}"
        
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.sendto(message.encode('utf-8'), ('<broadcast>', BROADCAST_PORT))
                    self.logger.debug(f"Broadcast enviado: {message}")
            except Exception as e:
                self.logger.error(f"Error enviando broadcast: {e}")
            
            time.sleep(BROADCAST_INTERVAL)
        
    def _setup_routes(self):
        self.app.post("/start_scraping", status_code=202)(self.start_scraping_job)
        self.app.post("/stop_scraping")(self.stop_scraping_job)
        self.app.get("/detailed_status")(self.get_detailed_status)
        self.app.post("/upload_courses")(self.upload_courses)
        self.app.get("/get_all_courses")(self.get_all_courses)
        self.app.get("/download_results")(self.download_results)
        self.app.get("/")(self.root_endpoint)
        self.app.get("/ping")(self.ping_endpoint)
        
        # Agregar logging para verificar que las rutas se registraron
        self.logger.info("Rutas registradas:")
        for route in self.app.routes:
            self.logger.info(f"  {route.methods} {route.path}")

    # --- Endpoints de la API ---

    async def start_scraping_job(self, request_data: dict):
        self.logger.info(f"¡¡¡ENDPOINT /start_scraping ALCANZADO!!! Datos: {request_data}")
        if self.is_job_running:
            self.logger.warning("Intento de iniciar un trabajo mientras otro ya está en progreso.")
            raise HTTPException(status_code=409, detail="Ya hay un trabajo de scraping en progreso.")

        self.logger.info(f"Recibido nuevo trabajo de scraping: {request_data}")
        self.is_job_running = True

        try:
            # Manejar múltiples formatos de entrada del frontend
            if 'job_params' in request_data:
                # Formato anidado del frontend (nuevo)
                job_params = request_data['job_params']
                from_sic = job_params.get('from_sic', '01.0')
                to_sic = job_params.get('to_sic', '011903.0')
                search_engine = job_params.get('search_engine', 'Cordis Europa')
                min_words = int(job_params.get('min_words', 30))  # Convertir a entero
                is_headless = job_params.get('headless_mode', True)
                num_workers = int(job_params.get('num_workers', NUM_PROCESSES))
                self.logger.info(f"Usando formato anidado: {from_sic} a {to_sic}, workers={num_workers}")
            else:
                # Formato directo (antiguo) o modelo ScrapingJob
                if isinstance(request_data, ScrapingJob):
                    # Si es un modelo Pydantic
                    from_sic = request_data.from_sic
                    to_sic = request_data.to_sic
                    search_engine = request_data.search_engine
                    min_words = int(request_data.min_words) # Convertir a entero
                    is_headless = request_data.is_headless
                    num_workers = request_data.num_workers or NUM_PROCESSES
                else:
                    # Si es un diccionario directo
                    from_sic = request_data.get('from_sic', '01.0')
                    to_sic = request_data.get('to_sic', '011903.0')
                    search_engine = request_data.get('search_engine', 'Cordis Europa')
                    min_words = int(request_data.get('min_words', 30)) # Convertir a entero
                    is_headless = request_data.get('headless_mode', True)
                    num_workers = int(request_data.get('num_workers', NUM_PROCESSES))
                self.logger.info(f"Usando formato directo: {from_sic} a {to_sic}")

            # 1. Obtener todos los cursos de la base de datos
            db_path = os.path.join(project_root, 'courses.db')
            if not os.path.exists(db_path):
                raise HTTPException(status_code=404, detail="La base de datos 'courses.db' no existe. Por favor, suba un archivo de cursos primero.")
            db_handler = SQLiteHandler(db_path)
            all_courses = db_handler.get_all_courses() # Devuelve lista de tuplas (sic_code, course_name)
            
            # 2. Filtrar cursos basados en el rango SIC del trabajo
            start_index = next((i for i, (sic, _) in enumerate(all_courses) if sic == from_sic), 0)
            end_index = next((i for i, (sic, _) in enumerate(all_courses) if sic == to_sic), len(all_courses) - 1)
            courses_to_process = all_courses[start_index : end_index + 1]
            
            if not courses_to_process:
                self.is_job_running = False
                raise HTTPException(status_code=404, detail="No se encontraron cursos en el rango SIC especificado.")

            # 3. Crear diccionario de parámetros para los workers
            job_params_dict = {
                'from_sic': from_sic,
                'to_sic': to_sic,
                'search_engine': search_engine,
                'min_words': min_words,
                'is_headless': is_headless
            }
            
            # 4. Poner cada curso como una tarea individual en la cola
            num_courses = len(courses_to_process)
            self.logger.info(f"Encolando {num_courses} cursos como tareas individuales.")
            self.logger.info(f"Parámetros del trabajo: {job_params_dict}")
            
            for course_sic, course_name in courses_to_process:
                # Cada item de trabajo es ahora un solo curso en un lote de tamaño 1
                single_course_batch = [(course_sic, course_name)]
                self.work_queue.put((single_course_batch, job_params_dict))

            self.logger.info(f"¡¡¡TAREAS PUESTAS EN LA COLA!!! Tamaño de la cola: {self.work_queue.qsize()}")

            # 5. Iniciar el pool de trabajadores
            self._start_worker_pool(num_workers)

            # 5. Iniciar un hilo monitor para saber cuándo ha terminado todo el trabajo
            monitor_thread = threading.Thread(target=self._monitor_job_completion, daemon=True)
            monitor_thread.start()

            return {"message": f"Trabajo iniciado. {num_courses} cursos encolados para {NUM_PROCESSES} trabajadores."}

        except Exception as e:
            self.logger.error("Error al iniciar el trabajo de scraping.", exc_info=True)
            self.is_job_running = False
            raise HTTPException(status_code=500, detail=f"Error al iniciar el trabajo: {e}")

    def _monitor_job_completion(self):
        """Espera en un hilo separado a que la cola se vacíe y luego detiene el pool."""
        self.work_queue.join() # Bloquea hasta que todas las tareas en la cola estén hechas (task_done)
        self.logger.info("Toda la carga de trabajo de la cola ha sido completada. Los workers están ahora inactivos (idle).")
        self.is_job_running = False # Permitir nuevos trabajos
        # self._stop_worker_pool() # Desactivado para que el estado final persista en la GUI

    def _cleanup_finished_workers(self):
        """
        En un hilo separado, revisa periódicamente los workers y resetea aquellos
        que han estado en estado 'finished' por un tiempo.
        NEUTRALIZADO: Esta función ha sido desactivada para que el estado final
        de los workers (100% y mensaje de estadísticas) persista en la GUI.
        """
        while not self.cleanup_stop_event.is_set():
            try:
                # La lógica de limpieza ha sido desactivada a petición del usuario.
                pass
            except Exception as e:
                self.logger.error(f"Error en el hilo de limpieza de workers: {e}", exc_info=True)
            
            time.sleep(3600) # Dormir por una hora para que no consuma recursos.

    async def stop_scraping_job(self):
        if not self.is_job_running:
            raise HTTPException(status_code=404, detail="No hay ningún trabajo de scraping en ejecución.")
        
        self.logger.info("Se recibió una solicitud para detener el trabajo de scraping.")
        self._stop_worker_pool()
        # Limpiar la cola por si acaso
        while not self.work_queue.empty():
            try:
                self.work_queue.get_nowait()
            except Empty:
                break
        
        self.is_job_running = False
        return {"message": "Solicitud de detención recibida. El pool de trabajadores ha sido detenido."}

    async def get_detailed_status(self):
        return dict(self.worker_states)

    async def get_all_courses(self):
        try:
            db_path = os.path.join(project_root, 'courses.db')
            if not os.path.exists(db_path):
                self.logger.warning("get_all_courses: courses.db no encontrado.")
                return []
            
            db_handler = SQLiteHandler(db_path)
            all_courses = db_handler.get_all_courses()
            return all_courses
        except Exception as e:
            self.logger.exception("Error en get_all_courses")
            raise HTTPException(status_code=500, detail=f"Error interno del servidor al obtener cursos: {e}")

    async def upload_courses(self, file: UploadFile = File(...)):
        self.logger.info(f"Recibida solicitud para cargar archivo de cursos: {file.filename}")
        
        if not file.filename.endswith(('.csv', '.xlsx')):
            raise HTTPException(status_code=400, detail="Formato de archivo no soportado. Por favor, suba un archivo .csv o .xlsx.")

        try:
            contents = await file.read()
            
            if file.filename.endswith('.csv'):
                # Detectar automáticamente el separador (coma, punto y coma, o pipe)
                sample = contents[:2048].decode('utf-8', errors='ignore')
                first_line = sample.split('\n')[0] if '\n' in sample else sample
                
                # Contar ocurrencias de posibles separadores en la primera línea
                separators = {',': first_line.count(','), ';': first_line.count(';'), '|': first_line.count('|')}
                detected_sep = max(separators, key=separators.get)
                self.logger.info(f"Separador detectado: '{detected_sep}' (ocurrencias: {separators})")
                
                df = pd.read_csv(io.BytesIO(contents), sep=detected_sep)
            else:
                df = pd.read_excel(io.BytesIO(contents))

            df.columns = [col.strip().lower() for col in df.columns]

            if 'codigo' in df.columns and 'curso' in df.columns:
                code_col, course_col = 'codigo', 'curso'
            elif 'sic_code' in df.columns and 'course' in df.columns:
                code_col, course_col = 'sic_code', 'course'
            elif 'sic_code' in df.columns and 'course_name' in df.columns:
                code_col, course_col = 'sic_code', 'course_name'
            else:
                raise HTTPException(status_code=400, detail="El archivo debe contener las columnas 'codigo' y 'curso' (o variantes como 'sic_code' y 'course_name').")

            courses_to_load = df[[code_col, course_col]].values.tolist()
            self.logger.info(f"Se encontraron {len(courses_to_load)} cursos en el archivo.")

            db_path = os.path.join(project_root, 'courses.db')
            db_handler = SQLiteHandler(db_path)
            
            self.logger.info("Limpiando la tabla de cursos existente...")
            db_handler.clear_courses_table()
            
            self.logger.info("Insertando nuevos cursos en la base de datos...")
            success = db_handler.insert_courses(courses_to_load)
            
            if success:
                 # VERIFICACIÓN INMEDIATA
                 verify_courses = db_handler.get_all_courses()
                 verify_count = len(verify_courses)
                 self.logger.info(f"VERIFICACIÓN: Leídos {verify_count} cursos de la DB inmediatamente después de insertar.")
                 
                 if verify_count == 0:
                     self.logger.error("ALERTA CRÍTICA: La base de datos está vacía después de una inserción supuestamente exitosa.")
                     raise HTTPException(status_code=500, detail="Error Crítico: Los cursos se procesaron pero no se guardaron en la base de datos (0 filas encontradas).")

                 return {"message": f"Carga exitosa. Se han cargado {len(courses_to_load)} cursos en la base de datos. Verificación: {verify_count} registros."}
            else:
                 raise HTTPException(status_code=500, detail="Error interno: No se pudieron guardar los cursos en la base de datos (SQLite error).")

        except Exception as e:
            self.logger.exception("Error procesando el archivo de cursos cargado.")
            raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

    async def download_results(self):
        """Descarga todos los archivos de la carpeta results como un ZIP."""
        results_dir = os.path.join(project_root, 'results')
        if not os.path.exists(results_dir):
            raise HTTPException(status_code=404, detail="No hay resultados para descargar (carpeta vacía o inexistente).")
            
        # Crear un archivo ZIP en memoria o temporal
        zip_filename = "resultados_europa.zip"
        zip_path = os.path.join(project_root, zip_filename)
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Recorrer todos los archivos en results
                files_found = False
                for root, dirs, files in os.walk(results_dir):
                    for file in files:
                        files_found = True
                        file_path = os.path.join(root, file)
                        # Agregar al zip con nombre relativo
                        zipf.write(file_path, os.path.relpath(file_path, os.path.join(results_dir, '..')))
                
                if not files_found:
                     # Si no hay archivos, crear al menos un archivo de texto vacío
                     zipf.writestr("leeme.txt", "No se encontraron archivos en la carpeta results.")

            if not os.path.exists(zip_path):
                 raise HTTPException(status_code=500, detail="Error creando el archivo ZIP.")
                 
            return FileResponse(zip_path, media_type='application/zip', filename=zip_filename)
            
        except Exception as e:
            self.logger.error(f"Error generando ZIP de resultados: {e}")
            raise HTTPException(status_code=500, detail=f"Error generando descarga: {str(e)}")

    async def root_endpoint(self):
        """Endpoint raíz para verificar que el servidor está activo."""
        return {"status": "active", "message": "Europa Scraper Server is running"}

    async def ping_endpoint(self):
        """Endpoint simple para ping de prueba."""
        return "EUROPA_SCRAPER_SERVER_PONG"

    def run(self):
        os.makedirs("logs", exist_ok=True)
        self.logger.info(f"Iniciando servidor en http://{self.host}:{self.port}")
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )

