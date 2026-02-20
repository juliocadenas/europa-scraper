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
import shutil
from multiprocessing.managers import SyncManager
from queue import Empty
from typing import Dict, Any, Optional, List, Tuple
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from datetime import datetime
from collections import deque
import enum
import queue 
import platform
import traceback
import random
import json
import hashlib
import re

# --- SYSTEM EVENTS ENUM ---
class EventType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    WORKER = "WORKER"
    SCRAPER = "SCRAPER"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"

# --- EVENT LOG SYSTEM ---
class EventLog:
    def __init__(self, max_size=5000):
        self._log = deque(maxlen=max_size)
        self._lock = asyncio.Lock()
        self._counter = 0

    async def add(self, event_type: str, source: str, message: str, details: Dict = None):
        async with self._lock:
            self._counter += 1
            event = {
                "id": self._counter,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "type": event_type,
                "source": source,
                "message": message,
                "details": details or {}
            }
            self._log.append(event)
            return event

    async def get_events(self, min_id: int = 0):
        """Retorna eventos con ID > min_id"""
        if min_id == 0:
            return list(self._log)[-50:]
        return [e for e in self._log if e["id"] > min_id]

# --- Constantes ---
NUM_PROCESSES = os.cpu_count() or 4
BATCH_SIZE = 10
BROADCAST_PORT = 50001
BROADCAST_INTERVAL = 5

# GLOBAL EVENT LOG
global_event_log = EventLog()

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
    search_mode: str = "broad"
    require_keywords: bool = False
    num_workers: Optional[int] = None

# ==============================================================================
# FUNCIÓN DEL TRABAJADOR (WORKER) - Se ejecuta en un proceso separado
# ==============================================================================
def worker_process(
    worker_id: int,
    work_queue: multiprocessing.JoinableQueue,
    status_dict: Dict,
    course_states: Dict,
    config_path: str,
    event_queue: multiprocessing.Queue # Corregido: era event_log y faltaba tipo
):
    """
    Función principal para cada proceso trabajador del pool.
    """
    # Helper for logging events to queue from worker
    def log_event_sync(type_str, msg, details=None):
        try:
            event_data = {
                "type": type_str,
                "source": f"Worker-{worker_id}",
                "message": msg,
                "details": details or {}
            }
            event_queue.put(event_data)
        except Exception as e:
            # Fallback to print if event queue fails
            print(f"Error putting event in queue from Worker-{worker_id}: {e}")

    # Set logging configuration for worker process
    setup_logger(logging.DEBUG, os.path.join(project_root, 'logs', f"worker_{worker_id}.log"))
    logger = logging.getLogger(f"worker_{worker_id}") # Get the logger instance

    status_dict[worker_id] = {'id': worker_id, 'status': 'Idle', 'progress': 0, 'current_task': 'Esperando tarea'}
    
    logger.info(f"Worker {worker_id} iniciado.")
    log_event_sync(EventType.WORKER, "Worker iniciado.")

    # --- Inicialización de componentes por proceso ---
    # Cada proceso necesita sus propias instancias para evitar conflictos.
    config_manager = Config(config_path)
    
    # Pre-cargar configuración para evitar lecturas de disco repetitivas
    # NOTA: search_engine se obtiene de job_params, NO de config global
    is_headless_param = config_manager.get('headless', True)
    
    scraper_controller = None
    browser_manager = None

    # Inicializar Loop de Eventos para Asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        try:
            # Obtener un lote de trabajo de la cola
            logger.info(f"Worker {worker_id}: Esperando por un trabajo en la cola...")
            log_event_sync(EventType.WORKER, "Esperando tarea.")
            
            work_item = work_queue.get()
            logger.info(f"Worker {worker_id}: ¡Ha recibido un trabajo de la cola!")
            log_event_sync(EventType.WORKER, "Tarea recibida de la cola.")
            
            if work_item is None:  # Señal de finalización
                logger.info(f"Worker {worker_id} recibió señal de finalización.")
                log_event_sync(EventType.WORKER, "Señal de finalización recibida. Apagando.")
                break
            
            batch, job_params = work_item
            batch_id = f"batch_{int(time.time())}_{worker_id}"
            
            # OBTENER search_engine DE job_params, NO de config global
            search_engine_param = job_params.get('search_engine', 'DuckDuckGo')
            logger.info(f"Worker {worker_id}: Motor de búsqueda del trabajo: '{search_engine_param}'")
            
            browser_initialized = (scraper_controller is not None)

            if not browser_initialized:
                status_dict[worker_id] = {'id': worker_id, 'status': 'Initializing', 'progress': 0, 'current_task': 'Iniciando navegador...'}
                logger.info(f"Worker {worker_id}: Inicializando componentes para la primera tarea.")
                log_event_sync(EventType.WORKER, "Inicializando componentes para la primera tarea.")
                
                # Crear un server_state simulado para los workers
                class WorkerServerState:
                    def __init__(self):
                        self.captcha_solution_queue = multiprocessing.Queue()
                        
                    def set_pending_captcha_challenge(self, challenge):
                        logger.info(f"CAPTCHA challenge detectado en worker: {challenge}")
                        log_event_sync(EventType.WARNING, "CAPTCHA challenge detectado.", {"challenge": challenge})
                
                worker_server_state = WorkerServerState()
                
                # Configurar proxy manager
                proxy_file_path = os.path.join(project_root, 'config', 'proxies.txt')
                proxy_manager = ProxyManager() # Constructor sin argumentos
                
                # Cargar proxies desde archivo si existe
                if os.path.exists(proxy_file_path):
                    try:
                        with open(proxy_file_path, 'r', encoding='utf-8') as f:
                            proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                            if proxies:
                                proxy_manager.set_proxies(proxies)
                                logger.info(f"Cargados {len(proxies)} proxies desde {proxy_file_path}")
                    except Exception as e:
                        logger.error(f"Error cargando archivo de proxies: {e}")
                
                # start_web_server_if_needed(project_root) # Eliminado: no existe esta función
                
                # Configurar rotación de proxies desde config
                if config_manager.get('use_proxies', False):
                    proxy_manager.set_rotation_enabled(config_manager.get('proxy_rotation', True))
                    proxy_manager.set_timeout(int(config_manager.get('proxy_timeout', 30)))
                    logger.info(f"Worker {worker_id}: Proxies habilitados. {len(proxy_manager.proxies)} proxies cargados.")
                    log_event_sync(EventType.SYSTEM, f"Proxies habilitados. {len(proxy_manager.proxies)} proxies cargados.")
                else:
                    logger.info(f"Worker {worker_id}: Proxies deshabilitados.")
                    log_event_sync(EventType.SYSTEM, "Proxies deshabilitados.")

                browser_manager = BrowserManager(config_manager=config_manager, server_state=worker_server_state)
                browser_manager.set_proxy_manager(proxy_manager)
                
                # Inicializar navegador si es necesario (no si es API-only y ya estamos seguros)
                # Pero ScraperController maneja esto internamente mejor, aquí solo preparamos.
                try:
                    is_headless = True
                    # Check os for headless
                    if platform.system() == "Linux":
                         is_headless = True
                         if not is_headless_param:
                             logger.warning(f"Worker {worker_id}: Forzando headless=True en Linux (solicitado: {is_headless_param})")
                             log_event_sync(EventType.WARNING, "Forzando headless=True en Linux.", {"requested_headless": is_headless_param})
                    else:
                         is_headless = is_headless_param

                    if search_engine_param == 'Cordis Europa API':
                        logger.info(f"Worker {worker_id}: Modo API detectado ({search_engine_param}). Omitiendo inicialización de navegador.")
                        log_event_sync(EventType.SYSTEM, "Modo API detectado. Omitiendo inicialización de navegador.")
                    else:
                        logger.info(f"Worker {worker_id}: Modo headless = {is_headless}")
                        log_event_sync(EventType.SYSTEM, f"Modo headless = {is_headless}.")
                        # Añadir un retraso aleatorio para evitar race conditions al iniciar múltiples navegadores
                        delay = random.uniform(2.0, 8.0)
                        logger.info(f"Worker {worker_id}: Esperando {delay:.2f}s antes de inicializar navegador...")
                        time.sleep(delay)
                        
                        loop.run_until_complete(browser_manager.initialize(headless=is_headless))
                        logger.info(f"Worker {worker_id}: Navegador inicializado correctamente")
                        log_event_sync(EventType.SYSTEM, "Navegador inicializado correctamente.")
                except Exception as e:
                    import traceback
                    error_detail = f"Error inicializando navegador: {str(e)}"
                    logger.error(error_detail)
                    log_event_sync(EventType.ERROR, error_detail, {"traceback": traceback.format_exc()})
                    # Enviar el error detallado al status_dict para que el usuario lo vea en la GUI
                    status_dict[worker_id] = {
                        'id': worker_id, 
                        'status': 'Error', 
                        'progress': 0, 
                        'current_task': f"Error Init: {str(e)[:50]}"
                    }
                    if 'work_queue' in locals():
                        work_queue.task_done()
                    continue

                # Inicializar ScraperController
                scraper_controller = ScraperController(config_manager, browser_manager)
                
                # INYECTAR CALLBACK DE EVENTOS AL CONTROLADOR
                def controller_event_callback(type_str, msg, details=None):
                    log_event_sync(type_str, msg, details)
                
                scraper_controller.set_event_callback(controller_event_callback)

            # Si el navegador no se inicializó, no podemos continuar
            if not scraper_controller or not browser_manager:
                logger.error(f"Worker {worker_id}: Controlador o BrowserManager no inicializados, saltando lote.")
                log_event_sync(EventType.ERROR, "Controlador o BrowserManager no inicializados, saltando lote.")
                if 'work_queue' in locals():
                    work_queue.task_done()
                continue

            # Actualizar estado a Working
            course_name_display = batch[0][1] if batch and len(batch) > 0 else "Desconocido"
            
            logger.info(f"Worker {worker_id} recibió lote {batch_id} con {len(batch)} cursos y parámetros: {job_params}")
            log_event_sync(EventType.SCRAPER, f"Recibido lote {batch_id} para {len(batch)} cursos.", {"job_params": job_params})
            
            status_dict[worker_id] = {
                'id': worker_id, 
                'status': 'working', 
                'progress': 0, 
                'current_task': f"Procesando: {course_name_display}"
            }

            # Definir callback de progreso para este trabajador
            def progress_callback(percentage, message, stats=None):
                current_status = status_dict[worker_id]
                current_status.update({
                    'progress': percentage,
                    'current_task': message
                })
                if stats:
                    current_status.update({
                        'total_urls_found': stats.get('total_urls_found', 0),
                        'files_saved': stats.get('files_saved', 0)
                    })
                status_dict[worker_id] = current_status
                
                # Actualizar estado del curso
                if batch and len(batch) > 0:
                    course_sic = batch[0][0]
                    if course_sic in course_states:
                        try:
                            c_state = course_states[course_sic]
                            c_state.update({
                                'progress': percentage,
                                'status': 'Procesando' if percentage < 100 else 'Completado'
                            })
                            course_states[course_sic] = c_state
                        except Exception:
                            pass
            
            # Marcar inicio del curso
            if batch and len(batch) > 0:
                course_sic = batch[0][0]
                if course_sic in course_states:
                    try:
                        c_state = course_states[course_sic]
                        c_state['status'] = 'Procesando'
                        course_states[course_sic] = c_state
                    except Exception:
                        pass

            # run_scraping es una corutina, la ejecutamos en el bucle de eventos del worker.
            loop.run_until_complete(scraper_controller.run_scraping(
                job_params, 
                progress_callback=progress_callback,
                worker_id=worker_id,
                batch=batch
            ))
            
            # Marcar fin explícito si fue éxito (el error se manda en `except`)
            if batch and len(batch) > 0:
                course_sic = batch[0][0]
                if course_sic in course_states:
                    try:
                        c_state = course_states[course_sic]
                        c_state['status'] = 'Completado'
                        c_state['progress'] = 100
                        course_states[course_sic] = c_state
                    except Exception:
                        pass


            logger.info(f"Worker {worker_id} completó el lote {batch_id}.")
            log_event_sync(EventType.SUCCESS, f"Lote {batch_id} completado.")
            work_queue.task_done()

            # Obtener estadísticas reales del lote actual
            try:
                cumulative_stats = scraper_controller.stats
                msg_finished = f"Completado: {course_name_display} | URLs: {cumulative_stats['total_urls_found']} | Guardados: {cumulative_stats['files_saved']} | Omitidos: {cumulative_stats['files_not_saved']} | Errores: {cumulative_stats['total_errors']}"
                
                status_dict[worker_id] = {
                    'id': worker_id, 
                    'status': 'finished', 
                    'progress': 100, 
                    'current_task': msg_finished,
                    'total_urls_found': cumulative_stats['total_urls_found'],
                    'files_saved': cumulative_stats['files_saved'],
                    'omitted_count': cumulative_stats['files_not_saved'],
                    'error_count': cumulative_stats['total_errors']
                }
                log_event_sync(EventType.SUCCESS, "Tarea finalizada.", {"stats": cumulative_stats})

            except Exception:
                logger.error("Error al actualizar estado final", exc_info=True)

        except queue.Empty:
            # Esto no debería ocurrir con un `get()` bloqueante, pero es una salvaguarda
            log_event_sync(EventType.WORKER, "Cola de trabajo vacía. Esperando...")
            time.sleep(1)
        except Exception as e:
            import traceback
            error_msg = f"Error crítico en Worker-{worker_id}: {str(e)}"
            logger.error(f"Worker {worker_id}: {error_msg}", exc_info=True)
            log_event_sync(EventType.ERROR, error_msg, {"traceback": traceback.format_exc()})
            status_dict[worker_id] = {
                'id': worker_id, 
                'status': 'Error', 
                'progress': 0, 
                'current_task': f"CRASHED: {str(e)[:40]}..."
            }
            # Marcar la tarea como hecha para no bloquear la cola si hay un error
            if 'work_queue' in locals() and isinstance(work_queue, multiprocessing.queues.JoinableQueue):
                work_queue.task_done()
            time.sleep(5)


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
        self.course_states: Optional[Dict] = None

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
        await global_event_log.add(EventType.SYSTEM, "Server", "Iniciando servidor y gestor de multiprocesamiento.")
        # Forzar el método de inicio a 'spawn' para compatibilidad y seguridad
        multiprocessing.set_start_method('spawn', force=True)
        self.manager = multiprocessing.Manager()
        self.work_queue = self.manager.JoinableQueue()
        self.worker_states = self.manager.dict()
        self.course_states = self.manager.dict()
        self.cleanup_stop_event = threading.Event()
        
        # --- NUEVO: COLA DE EVENTOS Y HILO CONSUMIDOR ---
        self.event_queue = self.manager.Queue()
        self.event_consumer_stop = threading.Event()
        self.event_consumer_thread = threading.Thread(target=self._consume_events, daemon=True)
        self.event_consumer_thread.start()
        
        self.cleanup_thread = threading.Thread(target=self._cleanup_finished_workers, daemon=True)
        self.cleanup_thread.start()
        self.logger.info("Iniciado el monitor de limpieza de workers.")
        await global_event_log.add(EventType.SYSTEM, "Server", "Iniciado el monitor de limpieza de workers y consumidor de eventos.")
        # No iniciamos el pool aquí, se inicia bajo demanda.

    def _consume_events(self):
        """Consume eventos de la cola multiproceso y los añade al log global async."""
        # Se requiere un loop para ejecutar el async add dentro del thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while not self.event_consumer_stop.is_set():
            try:
                # Get con timeout para revisar el stop event
                event_data = self.event_queue.get(timeout=1)
                
                # Ejecutar corutina de añadido
                loop.run_until_complete(global_event_log.add(
                    event_data['type'], 
                    event_data['source'], 
                    event_data['message'], 
                    event_data['details']
                ))
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error en consumidor de eventos: {e}")

    async def _shutdown(self):
        self.logger.info("Deteniendo el pool de trabajadores...")
        await global_event_log.add(EventType.SYSTEM, "Server", "Deteniendo el pool de trabajadores.")
        self._stop_worker_pool()
        self._stop_broadcasting()
        if hasattr(self, 'cleanup_stop_event'):
            self.cleanup_stop_event.set()
        
        # Detener consumidor de eventos
        if hasattr(self, 'event_consumer_stop'):
            self.event_consumer_stop.set()
            # Give the consumer thread a moment to finish
            if self.event_consumer_thread.is_alive():
                self.event_consumer_thread.join(timeout=5)
            if self.event_consumer_thread.is_alive():
                self.logger.warning("Event consumer thread did not terminate gracefully.")
        
        if self.manager:
            self.logger.info("Cerrando el gestor de multiprocesamiento...")
            await global_event_log.add(EventType.SYSTEM, "Server", "Cerrando el gestor de multiprocesamiento.")
            self.manager.shutdown()

    def _start_worker_pool(self, num_workers: int):
        if self.worker_pool:
            self.logger.warning("El pool de trabajadores ya está en ejecución. No se iniciará de nuevo.")
            asyncio.create_task(global_event_log.add(EventType.WARNING, "Server", "Intento de iniciar pool de workers, pero ya está en ejecución."))
            return

        self.logger.info(f"Iniciando un pool de {num_workers} procesos trabajadores...")
        asyncio.create_task(global_event_log.add(EventType.SYSTEM, "Server", f"Iniciando un pool de {num_workers} procesos trabajadores."))
        self.worker_pool = [
            multiprocessing.Process(
                target=worker_process,
                args=(i, self.work_queue, self.worker_states, self.course_states, self.config_path, self.event_queue) # Pass event_queue
            ) for i in range(num_workers)
        ]
        for p in self.worker_pool:
            p.start()

    def _stop_worker_pool(self):
        if not self.worker_pool:
            return
        
        self.logger.info("Enviando señal de finalización a todos los trabajadores...")
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(global_event_log.add(EventType.SYSTEM, "Server", "Enviando señal de finalización a todos los trabajadores."))
        except RuntimeError:
            asyncio.run(global_event_log.add(EventType.SYSTEM, "Server", "Enviando señal de finalización a todos los trabajadores."))
        for _ in self.worker_pool:
            self.work_queue.put(None) # Enviar una señal de "veneno" por cada trabajador

        for p in self.worker_pool:
            p.join(timeout=10) # Esperar a que los procesos terminen
            if p.is_alive():
                self.logger.warning(f"El trabajador {p.pid} no terminó a tiempo, forzando terminación.")
                try: asyncio.get_running_loop().create_task(global_event_log.add(EventType.WARNING, "Server", f"El trabajador {p.pid} no terminó a tiempo, forzando terminación."))
                except RuntimeError: asyncio.run(global_event_log.add(EventType.WARNING, "Server", f"El trabajador {p.pid} no terminó a tiempo, forzando terminación."))
                p.terminate()

        self.worker_pool = []
        self.is_job_running = False
        self.logger.info("Pool de trabajadores detenido.")
        try: asyncio.get_running_loop().create_task(global_event_log.add(EventType.SYSTEM, "Server", "Pool de trabajadores detenido."))
        except RuntimeError: asyncio.run(global_event_log.add(EventType.SYSTEM, "Server", "Pool de trabajadores detenido."))

    def _start_broadcasting(self):
        """Inicia el broadcasting para descubrimiento de clientes."""
        self.broadcast_thread = threading.Thread(target=self._broadcast_server_presence, daemon=True)
        self.broadcast_thread.start()
        self.logger.info("Iniciado broadcasting de presencia del servidor")
        asyncio.run(global_event_log.add(EventType.SYSTEM, "Server", "Iniciado broadcasting de presencia del servidor."))

    def _stop_broadcasting(self):
        """Detiene el broadcasting."""
        if hasattr(self, 'broadcast_thread') and self.broadcast_thread.is_alive():
            self.logger.info("Deteniendo broadcasting del servidor")
            asyncio.run(global_event_log.add(EventType.SYSTEM, "Server", "Deteniendo broadcasting del servidor."))
        
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
                asyncio.run(global_event_log.add(EventType.ERROR, "Server", f"Error enviando broadcast: {e}"))
            
            time.sleep(BROADCAST_INTERVAL)
        
    def _setup_routes(self):
        # Endpoints estándar
        self.app.post("/api/start_scraping", status_code=202)(self.start_scraping_job)
        self.app.post("/api/stop_scraping")(self.stop_scraping_job)
        self.app.post("/api/reset")(self.force_reset_state)
        self.app.get("/api/detailed_status")(self.get_detailed_status)
        self.app.post("/api/upload_courses")(self.upload_courses)
        self.app.get("/api/get_all_courses")(self.get_all_courses)
        self.app.get("/api/download_results")(self.download_results)
        self.app.post("/api/cleanup_files")(self.cleanup_files_endpoint)
        self.app.get("/")(self.root_endpoint)
        self.app.get("/api/ping")(self.ping_endpoint)
        
        # Endpoints de diagnóstico y eventos
        self.app.get("/api/events")(self.get_events_endpoint)
        self.app.get("/api/debug_info")(self.debug_info)
        self.app.get("/api/version")(self.version_endpoint)
        
        # Endpoints de visualización de resultados
        self.app.get("/api/list_results")(self.list_results_files)
        self.app.get("/api/list_omitidos")(self.list_omitidos_files)
        self.app.get("/api/download_file")(self.download_single_file)
        self.app.delete("/api/delete_file")(self.delete_single_file)  # NUEVO: borrado individual
        self.app.get("/api/preview_csv")(self.preview_csv)
        self.app.get("/viewer")(self.results_viewer_html)
        self.app.get("/api/cloudflare_url")(self.get_cloudflare_url)
        
        # Agregar logging para verificar que las rutas se registraron
        self.logger.info("Rutas registradas:")
        for route in self.app.routes:
            self.logger.info(f"  {route.methods} {route.path}")
            asyncio.run(global_event_log.add(EventType.SYSTEM, "Server", f"Ruta registrada: {route.methods} {route.path}"))

    # --- Endpoints de la API ---

    async def start_scraping_job(self, request_data: dict):
        self.logger.info(f"¡¡¡ENDPOINT /start_scraping ALCANZADO!!! Datos: {request_data}")
        await global_event_log.add(EventType.SYSTEM, "Server", "Solicitud para iniciar scraping recibida.", {"request_data": request_data})
        if self.is_job_running:
            self.logger.warning("Intento de iniciar un trabajo mientras otro ya está en progreso.")
            await global_event_log.add(EventType.WARNING, "Server", "Intento de iniciar un trabajo mientras otro ya está en progreso.")
            raise HTTPException(status_code=409, detail="Ya hay un trabajo de scraping en progreso.")

        self.logger.info(f"Recibido nuevo trabajo de scraping: {request_data}")
        self.is_job_running = True
        
        # Generar un ID de tarea real
        task_id = f"task_{int(time.time())}"

        # LIMPIEZA DE ESTADO: Resetear worker_states para que la GUI no muestre datos antiguos
        if self.worker_states is not None:
            self.logger.info("Limpiando estados previos de los trabajadores...")
            await global_event_log.add(EventType.SYSTEM, "Server", "Limpiando estados previos de los trabajadores.")
            self.worker_states.clear()
            
        if self.course_states is not None:
            self.course_states.clear()

        try:
            # Manejar múltiples formatos de entrada del frontend
            if 'job_params' in request_data:
                # Formato anidado del frontend (nuevo)
                job_params = request_data['job_params']
                from_sic = job_params.get('from_sic', '01.0')
                to_sic = job_params.get('to_sic', '011903.0')
                search_engine = job_params.get('search_engine', 'Cordis Europa')
                num_workers = int(job_params.get('num_workers', NUM_PROCESSES))
                search_mode = job_params.get('search_mode', 'broad')
                require_keywords = job_params.get('require_keywords', False)
                self.logger.info(f"Usando formato anidado: {from_sic} a {to_sic}, workers={num_workers}, mode={search_mode}")
            else:
                # Formato directo (antiguo) o modelo ScrapingJob
                if isinstance(request_data, ScrapingJob):
                    # Si es un modelo Pydantic
                    from_sic = request_data.from_sic
                    to_sic = request_data.to_sic
                    search_engine = request_data.search_engine
                    min_words = int(request_data.min_words) # Convertir a entero
                    is_headless = request_data.is_headless
                    search_mode = request_data.search_mode
                    require_keywords = request_data.require_keywords
                    
                    # LIMITACIÓN DE RECURSOS: Si no se especifica o es muy alto, limitar num_workers
                    MAX_DEFAULT_WORKERS = min(8, NUM_PROCESSES)
                    requested_workers = request_data.num_workers
                    if not requested_workers or int(requested_workers) <= 0:
                        num_workers = MAX_DEFAULT_WORKERS
                    else:
                        num_workers = int(requested_workers)
                        # Si pide mas de 24, avisar pero permitir por ahora (o podrías capar)
                        if num_workers > 24:
                            self.logger.warning(f"Solicitados {num_workers} workers. Esto puede causar inestabilidad.")
                            await global_event_log.add(EventType.WARNING, "Server", f"Solicitados {num_workers} workers. Esto puede causar inestabilidad.")
                else:
                    # Si es un diccionario directo
                    from_sic = request_data.get('from_sic', '01.0')
                    to_sic = request_data.get('to_sic', '011903.0')
                    search_engine = request_data.get('search_engine', 'Cordis Europa')
                    min_words = int(request_data.get('min_words', 30)) # Convertir a entero
                    is_headless = request_data.get('headless_mode', True)
                    search_mode = request_data.get('search_mode', 'broad')
                    require_keywords = request_data.get('require_keywords', False)
                    
                    MAX_DEFAULT_WORKERS = min(8, NUM_PROCESSES)
                    requested_workers = request_data.get('num_workers')
                    if not requested_workers:
                        num_workers = MAX_DEFAULT_WORKERS
                    else:
                        num_workers = int(requested_workers)
                self.logger.info(f"Usando formato directo: {from_sic} a {to_sic}")
                job_params = request_data  # Definir job_params para el log de eventos
            await global_event_log.add(EventType.SYSTEM, "Server", f"Parámetros de trabajo procesados: {from_sic} a {to_sic}, {num_workers} workers.", {"job_params": job_params})

            # 1. Obtener todos los cursos de la base de datos
            db_path = os.path.join(project_root, 'courses.db')
            if not os.path.exists(db_path):
                await global_event_log.add(EventType.ERROR, "Server", "La base de datos 'courses.db' no existe. Por favor, suba un archivo de cursos primero.")
                raise HTTPException(status_code=404, detail="La base de datos 'courses.db' no existe. Por favor, suba un archivo de cursos primero.")
            db_handler = SQLiteHandler(db_path)
            all_courses = db_handler.get_all_courses() # Devuelve lista de tuplas (sic_code, course_name)
            
            # 2. Filtrar cursos basados en el rango SIC del trabajo
            start_index = next((i for i, (sic, _) in enumerate(all_courses) if sic == from_sic), 0)
            end_index = next((i for i, (sic, _) in enumerate(all_courses) if sic == to_sic), len(all_courses) - 1)
            courses_to_process = all_courses[start_index : end_index + 1]
            
            if not courses_to_process:
                self.is_job_running = False
                await global_event_log.add(EventType.WARNING, "Server", "No se encontraron cursos en el rango SIC especificado.")
                raise HTTPException(status_code=404, detail="No se encontraron cursos en el rango SIC especificado.")

            # 3. Crear diccionario de parámetros para los workers
            job_params_dict = {
                'from_sic': from_sic,
                'to_sic': to_sic,
                'search_engine': search_engine,
                'min_words': min_words,
                'is_headless': is_headless,
                'search_mode': search_mode,
                'require_keywords': require_keywords
            }
            
            # 4. Poner cada curso como una tarea individual en la cola
            num_courses = len(courses_to_process)
            self.logger.info(f"Encolando {num_courses} cursos como tareas individuales.")
            self.logger.info(f"Parámetros del trabajo: {job_params_dict}")
            await global_event_log.add(EventType.SYSTEM, "Server", f"Encolando {num_courses} cursos como tareas individuales.", {"job_params": job_params_dict})
            
            for course_sic, course_name in courses_to_process:
                # Cada item de trabajo es ahora un solo curso en un lote de tamaño 1
                single_course_batch = [(course_sic, course_name)]
                self.work_queue.put((single_course_batch, job_params_dict))
                self.course_states[course_sic] = {
                    'sic': course_sic,
                    'name': course_name,
                    'status': 'Pendiente',
                    'progress': 0
                }

            self.logger.info(f"¡¡¡TAREAS PUESTAS EN LA COLA!!! Tamaño de la cola: {self.work_queue.qsize()}")
            await global_event_log.add(EventType.SYSTEM, "Server", f"Tareas puestas en la cola. Tamaño de la cola: {self.work_queue.qsize()}")

            # 5. Iniciar el pool de trabajadores
            # Si el pool ya existe pero tiene un número diferente de workers, reiniciarlo.
            if self.worker_pool and len(self.worker_pool) != num_workers:
                self.logger.info(f"Reiniciando pool: Solicitados {num_workers}, Activos {len(self.worker_pool)}")
                await global_event_log.add(EventType.SYSTEM, "Server", f"Reiniciando pool de workers: Solicitados {num_workers}, Activos {len(self.worker_pool)}.")
                self._stop_worker_pool()
            
            # Si el pool no está corriendo (o lo acabamos de detener), iniciarlo.
            if not self.worker_pool:
                self._start_worker_pool(num_workers)

            # 5. Iniciar un hilo monitor para saber cuándo ha terminado todo el trabajo
            monitor_thread = threading.Thread(target=self._monitor_job_completion, daemon=True)
            monitor_thread.start()

            return {
                "message": f"Trabajo iniciado. {num_courses} cursos encolados para {num_workers} trabajadores.",
                "task_id": task_id
            }

        except Exception as e:
            import traceback
            self.logger.error("Error al iniciar el trabajo de scraping.", exc_info=True)
            try:
                await global_event_log.add(EventType.ERROR, "Server", f"Error al iniciar el trabajo de scraping: {e}", {"traceback": traceback.format_exc()})
            except Exception as log_e:
                self.logger.error(f"Fallo al registrar evento global: {log_e}")
            self.is_job_running = False
            raise HTTPException(status_code=500, detail=f"Error al iniciar el trabajo: {e}")

    def _monitor_job_completion(self):
        """Espera en un hilo separado a que la cola se vacíe y luego detiene el pool."""
        self.work_queue.join() # Bloquea hasta que todas las tareas en la cola estén hechas (task_done)
        self.logger.info("Toda la carga de trabajo de la cola ha sido completada. Los workers están ahora inactivos (idle).")
        asyncio.run(global_event_log.add(EventType.SUCCESS, "Server", "Toda la carga de trabajo de la cola ha sido completada."))
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
                asyncio.run(global_event_log.add(EventType.ERROR, "Server", f"Error en el hilo de limpieza de workers: {e}", {"traceback": traceback.format_exc()}))
            
            time.sleep(3600) # Dormir por una hora para que no consuma recursos.

    async def stop_scraping_job(self):
        if not self.is_job_running:
            await global_event_log.add(EventType.WARNING, "Server", "Intento de detener scraping, pero no hay ningún trabajo en ejecución.")
            raise HTTPException(status_code=404, detail="No hay ningún trabajo de scraping en ejecución.")
        
        self.logger.info("Se recibió una solicitud para detener el trabajo de scraping.")
        await global_event_log.add(EventType.SYSTEM, "Server", "Solicitud para detener el trabajo de scraping recibida.")
        self._stop_worker_pool()
        # Limpiar la cola por si acaso
        while not self.work_queue.empty():
            try:
                self.work_queue.get_nowait()
            except Empty:
                break
        
        self.is_job_running = False
        await global_event_log.add(EventType.SUCCESS, "Server", "Trabajo de scraping detenido.")
        return {"message": "Solicitud de detención recibida. El pool de trabajadores ha sido detenido."}

    async def force_reset_state(self):
        """Forza el reseteo del estado global del servidor, deteniendo todo."""
        self.logger.warning("SOLICITUD DE REINICIO FORZADO RECIBIDA.")
        await global_event_log.add(EventType.WARNING, "Server", "SOLICITUD DE REINICIO FORZADO RECIBIDA.")
        
        # 1. Detener el pool de trabajadores
        self._stop_worker_pool()
        
        # 2. Limpiar la cola de trabajo
        try:
            while not self.work_queue.empty():
                self.work_queue.get_nowait()
        except Exception:
            pass
            
        # 3. Resetear banderas
        self.is_job_running = False
        
        # 4. Limpiar los estados de los workers para la GUI
        if self.worker_states is not None:
            self.worker_states.clear()
            
        await global_event_log.add(EventType.SUCCESS, "Server", "Servidor reiniciado forzosamente. El estado ahora es 'Inactivo'.")
        return {"message": "Servidor reiniciado forzosamente. El estado ahora es 'Inactivo'."}

    async def scan_events(self, min_id: int = 0):
        """Endpoint para obtener el stream de eventos de auditoría."""
        events = await global_event_log.get_events(min_id)
        return {"events": events, "latest_id": events[-1]["id"] if events else min_id}

    async def get_detailed_status(self):
        workers_dict = dict(self.worker_states) if self.worker_states else {}
        courses_dict = dict(self.course_states) if self.course_states else {}
        return {
            "workers": workers_dict, 
            "courses": courses_dict,
            "is_running": self.is_job_running
        }

    async def get_all_courses(self):
        try:
            db_path = os.path.join(project_root, 'courses.db')
            if not os.path.exists(db_path):
                self.logger.warning("get_all_courses: courses.db no encontrado.")
                return []
            
            db_handler = SQLiteHandler(db_path)
            all_courses = db_handler.get_all_courses()
            # Convert tuples to dictionaries for GUI compatibility
            return [{"sic_code": c[0], "course_name": c[1]} for c in all_courses]
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
                # Fallback a coma si no hay separadores claros
                if separators[detected_sep] == 0:
                     detected_sep = ','
                     
                self.logger.info(f"Separador detectado: '{detected_sep}'")
                
                # LEER TODO COMO STRING PARA NO PERDER CEROS INICIALES ("01.0")
                # header=None para evitar que la primera fila se pierda si el usuario no pone cabeceras estandar
                # Pero si tiene cabeceras, la primera fila sera basura. Mas adelante lo limpiamos.
                # ESTRATEGIA: Leer con cabecera (default) y luego tratar.
                df = pd.read_csv(io.BytesIO(contents), sep=detected_sep, dtype=str)
            else:
                # Excel: Leer todo como texto
                df = pd.read_excel(io.BytesIO(contents), dtype=str)

            # ESTRATEGIA DE COLUMNAS FLEXIBLE (PeticiÃ³n del usuario: "No importa como se llame")
            # Simplemente tomamos las dos primeras columnas, sean cuales sean.
            if len(df.columns) < 2:
                raise HTTPException(status_code=400, detail="El archivo requiere al menos 2 columnas (CÃ³digo y Nombre).")
            
            # Renombrar columnas internamente para estandarizar
            # CSV FORMATO: id, sic_code, course_name (3 columnas) O sic_code, course_name (2 columnas)
            if len(df.columns) >= 3:
                # Formato con ID: columnas 1 y 2
                code_col_orig = df.columns[1]
                course_col_orig = df.columns[2]
                col_indices = [1, 2]
            else:
                # Formato sin ID: columnas 0 y 1
                code_col_orig = df.columns[0]
                course_col_orig = df.columns[1]
                col_indices = [0, 1]
            
            # Si la primera fila parece un encabezado repetido o no vÃ¡lido, podrÃ­amos querer saltarla,
            # pero es difÃ­cil saberlo. Respetamos la data tal cual.
            # Limpiar espacios
            df[code_col_orig] = df[code_col_orig].astype(str).str.strip()
            df[course_col_orig] = df[course_col_orig].astype(str).str.strip()
            
            # --- SANITIZACIÓN SIC CODE (ANTI-EXCEL) ---
            # Excel guarda 01.0 como "1.0" en CSV. Recuperamos el cero perdido.
            def sanitize_sic(code):
                # Caso: "1.0" -> "01.0"
                # Si tiene formato D.D (un digito punto algo), agregamos cero.
                # SIC codes de agricultura son 01-09. Mineria es 10+.
                import re
                if re.match(r'^\d\.', code):
                    return "0" + code
                return code
            
            df[code_col_orig] = df[code_col_orig].apply(sanitize_sic)
            # ------------------------------------------

            self.logger.info(f"Usando columna 0 ('{code_col_orig}') como CÃ³digo y columna 1 ('{course_col_orig}') como Curso.")

            courses_to_load = df.iloc[:, col_indices].values.tolist()
            
            # Limpieza extra: Eliminar filas vacÃ­as o con 'nan'
            courses_to_load = [c for c in courses_to_load if c[0] and c[1] and c[0].lower() != 'nan']
            
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
                 self.logger.warning("No se encontraron archivos en la carpeta 'results' para descargar.")
                 raise HTTPException(status_code=404, detail="Carpeta de resultados está vacía.")
                 
            return FileResponse(zip_path, filename="resultados.zip", media_type="application/zip")
            
        except Exception as e:
            self.logger.error(f"Error comprimiendo resultados: {e}")
            raise HTTPException(status_code=500, detail=f"Error creando el archivo ZIP: {str(e)}")

    async def cleanup_files_endpoint(self):
        """Elimina el contenido de las carpetas 'results' y 'omitidos'."""
        try:
            results_dir = os.path.join(project_root, 'results')
            omitted_dir = os.path.join(project_root, 'results', 'omitidos')
            
            deleted_files = 0
            
            # Helper to clear directory contents (files and subdirs)
            def clear_directory(directory_path):
                count = 0
                if os.path.exists(directory_path):
                    for item in os.listdir(directory_path):
                        item_path = os.path.join(directory_path, item)
                        try:
                            if os.path.isfile(item_path) or os.path.islink(item_path):
                                os.unlink(item_path)
                                count += 1
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                                count += 1
                        except Exception as e:
                            self.logger.error(f"Error borrando {item_path}: {e}")
                return count

            deleted_files += clear_directory(results_dir)
            deleted_files += clear_directory(omitted_dir)
            
            self.logger.info(f"Endpoint /cleanup_files ejecutado. {deleted_files} elementos eliminados.")
            return {"message": f"Limpieza completada. Se eliminaron {deleted_files} archivos/carpetas de resultados y omitidos."}
            
        except Exception as e:
            self.logger.error(f"Error en cleanup_files: {e}")
            raise HTTPException(status_code=500, detail=f"Error limpiando archivos: {str(e)}")

    async def list_results_files(self):
        """Lista todos los archivos CSV/XLSX en la carpeta results y sus subcarpetas."""
        try:
            results_dir = os.path.join(project_root, 'results')
            self.logger.info(f"Listando archivos recursivamente en: {results_dir}")
            
            if not os.path.exists(results_dir):
                self.logger.warning(f"La carpeta results no existe: {results_dir}")
                return {"files": [], "message": f"La carpeta results no existe: {results_dir}", "results_dir": results_dir}
            
            files_info = []
            # Búsqueda recursiva
            for root, dirs, files in os.walk(results_dir):
                for filename in files:
                    if filename.endswith('.csv') or filename.endswith('.xlsx'):
                        filepath = os.path.join(root, filename)
                        stat = os.stat(filepath)
                        relative_path = os.path.relpath(filepath, results_dir).replace('\\', '/')
                        
                        # Determinar categoría basado en la subcarpeta
                        category = "General"
                        if "/EN/" in f"/{relative_path}/": category = "EN"
                        elif "/ES/" in f"/{relative_path}/": category = "ES"
                        elif "/omitidos/" in f"/{relative_path}/": category = "Omitidos"

                        files_info.append({
                            "name": filename,
                            "path": relative_path,
                            "size": stat.st_size,
                            "size_human": self._human_readable_size(stat.st_size),
                            "modified": stat.st_mtime,
                            "modified_human": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime)),
                            "category": category
                        })
            
            # Ordenar por fecha de modificación (más reciente primero)
            files_info.sort(key=lambda x: x['modified'], reverse=True)
            
            return {
                "files": files_info,
                "total": len(files_info),
                "results_dir": results_dir
            }
        except Exception as e:
            self.logger.error(f"Error listando archivos: {e}")
            raise HTTPException(status_code=500, detail=f"Error listando archivos: {str(e)}")

    async def list_omitidos_files(self):
        """Lista todos los archivos CSV en la carpeta omitidos con información detallada."""
        try:
            # Check both locations: legacy (root) and new (results/omitidos)
            dirs_to_check = [
                os.path.join(project_root, 'omitidos'),
                os.path.join(project_root, 'results', 'omitidos')
            ]
            
            files_info = []
            seen_files = set()

            for omitidos_dir in dirs_to_check:
                if os.path.exists(omitidos_dir):
                    for filename in os.listdir(omitidos_dir):
                        if (filename.endswith('.csv') or filename.endswith('.xlsx')) and filename not in seen_files:
                            filepath = os.path.join(omitidos_dir, filename)
                            try:
                                stat = os.stat(filepath)
                                files_info.append({
                                    "name": filename,
                                    "size": stat.st_size,
                                    "size_human": self._human_readable_size(stat.st_size),
                                    "modified": stat.st_mtime,
                                    "modified_human": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
                                })
                                seen_files.add(filename)
                            except OSError:
                                continue
            
            # Ordenar por fecha de modificación (más reciente primero)
            files_info.sort(key=lambda x: x['modified'], reverse=True)
            
            return {
                "files": files_info,
                "total": len(files_info),
                "omitidos_dir": "merged_view"
            }
        except Exception as e:
            self.logger.error(f"Error listando archivos omitidos: {e}")
            raise HTTPException(status_code=500, detail=f"Error listando archivos omitidos: {str(e)}")

    async def download_single_file(self, filename: str):
        """Descarga un archivo individual de la carpeta results o omitidos."""
        try:
            results_dir = os.path.join(project_root, 'results')
            omitidos_new = os.path.join(project_root, 'results', 'omitidos')
            omitidos_old = os.path.join(project_root, 'omitidos')
            
            # Check results
            filepath = os.path.join(results_dir, filename)
            if os.path.exists(filepath):
                 return FileResponse(filepath, filename=filename, media_type='text/csv')
                 
            # Check new omitidos
            filepath = os.path.join(omitidos_new, filename)
            if os.path.exists(filepath):
                 return FileResponse(filepath, filename=filename, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

            # Check old omitidos
            filepath = os.path.join(omitidos_old, filename)
            if os.path.exists(filepath):
                 return FileResponse(filepath, filename=filename, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

            raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {filename}")
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error descargando archivo {filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Error descargando archivo: {str(e)}")

    async def delete_single_file(self, filename: str):
        """Elimina un archivo individual de la carpeta results o omitidos."""
        try:
            # Sanitizar el nombre para prevenir path traversal
            safe_name = os.path.basename(filename)
            if not safe_name or safe_name != filename:
                raise HTTPException(status_code=400, detail="Nombre de archivo no válido.")

            results_dir = os.path.join(project_root, 'results')
            omitidos_new = os.path.join(project_root, 'results', 'omitidos')
            omitidos_old = os.path.join(project_root, 'omitidos')

            search_paths = [results_dir, omitidos_new, omitidos_old]
            deleted = False
            for directory in search_paths:
                filepath = os.path.join(directory, safe_name)
                if os.path.exists(filepath) and os.path.isfile(filepath):
                    os.unlink(filepath)
                    deleted = True
                    self.logger.info(f"Archivo eliminado: {filepath}")
                    await global_event_log.add(EventType.SYSTEM, "Server", f"Archivo eliminado: {safe_name}")
                    break

            if not deleted:
                raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {safe_name}")

            return {"message": f"Archivo '{safe_name}' eliminado correctamente."}
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error eliminando archivo {filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Error eliminando archivo: {str(e)}")

    async def preview_csv(self, filename: str, rows: int = 10):
        """Muestra una vista previa de un archivo CSV (primeras N filas)."""
        try:
            results_dir = os.path.join(project_root, 'results')
            omitidos_new = os.path.join(project_root, 'results', 'omitidos')
            omitidos_old = os.path.join(project_root, 'omitidos')
            
            filepath = os.path.join(results_dir, filename)
            if not os.path.exists(filepath):
                filepath = os.path.join(omitidos_new, filename)
            
            if not os.path.exists(filepath):
                filepath = os.path.join(omitidos_old, filename)
            
            if not os.path.exists(filepath):
                raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {filename}")
            
            # Leer el archivo según extensión
            if filename.endswith('.xlsx'):
                df = pd.read_excel(filepath, nrows=int(rows))
            else:
                df = pd.read_csv(filepath, nrows=int(rows))
            
            # Convertir a HTML para visualización
            html_table = df.to_html(classes='table table-striped table-hover', index=False)
            
            # Obtener información del archivo
            stat = os.stat(filepath)
            total_rows = sum(1 for _ in open(filepath)) - 1  # -1 por el encabezado
            
            return {
                "filename": filename,
                "preview_html": html_table,
                "preview_rows": int(rows),
                "total_rows": total_rows,
                "columns": list(df.columns),
                "size_human": self._human_readable_size(stat.st_size)
            }
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error generando preview de {filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Error generando preview: {str(e)}")

    async def results_viewer_html(self):
        """Retorna una página HTML simple para visualizar los resultados con auto-refresh."""
        html_content = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Europa Scraper - Resultados</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; background-color: #f5f5f5; }
        .card { margin-bottom: 20px; }
        .file-row { cursor: pointer; transition: background-color 0.2s; }
        .file-row:hover { background-color: #e9ecef; }
        .preview-container { max-height: 500px; overflow-y: auto; }
        #previewModal .modal-dialog { max-width: 90vw; }
        #previewModal .modal-body { padding: 0; }
        .table-responsive { margin: 0; }
        table { font-size: 0.9em; }
        th { background-color: #0d6efd; color: white; }
        .nav-tabs .nav-link { cursor: pointer; }
        .nav-tabs .nav-link.active { background-color: #0d6efd; color: white; }
        .url-box { background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .url-box h5 { margin: 0 0 10px 0; }
        .url-box .url { word-break: break-all; font-family: monospace; background: #fff; padding: 10px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h4 class="mb-0">Archivos del Scraper</h4>
                        <div>
                            <span class="badge bg-success" id="lastUpdate">Actualizado: --:--:--</span>
                            <button class="btn btn-sm btn-primary ms-2" onclick="loadFiles()">Actualizar</button>
                        </div>
                    </div>
                    <div class="card-body">
                        <ul class="nav nav-tabs" role="tablist">
                            <li class="nav-item">
                                <a class="nav-link active" id="tab-results" data-bs-toggle="tab" href="#" onclick="switchTab('results')">
                                    Resultados Exitosos
                                </a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" id="tab-omitidos" data-bs-toggle="tab" href="#" onclick="switchTab('omitidos')">
                                    Archivos Omitidos
                                </a>
                            </li>
                        </ul>
                        <div class="row mb-3">
                            <div class="col-md-4">
                                <label>Auto-refresh:</label>
                                <select id="refreshInterval" class="form-select form-select-sm" onchange="setRefreshInterval()">
                                    <option value="0">Desactivado</option>
                                    <option value="5000">5 segundos</option>
                                    <option value="10000" selected>10 segundos</option>
                                    <option value="30000">30 segundos</option>
                                    <option value="60000">1 minuto</option>
                                </select>
                            </div>
                            <div class="col-md-8 text-end">
                                <span class="badge bg-info" id="fileCount">0 archivos</span>
                            </div>
                        </div>
                        <div class="table-responsive">
                            <table class="table table-sm table-hover">
                                <thead>
                                    <tr>
                                        <th>Nombre</th>
                                        <th>Tamaño</th>
                                        <th>Modificado</th>
                                        <th>Acciones</th>
                                    </tr>
                                </thead>
                                <tbody id="filesTableBody">
                                    <tr><td colspan="4" class="text-center">Cargando...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="url-box">
        <h5>URL de Acceso (Cloudflare)</h5>
        <div class="url" id="cloudflareUrl">Cargando URL...</div>
        <small class="text-muted">Esta URL se mantiene activa mientras el servidor corra. Si la URL cambia, recarga la pagina.</small>
    </div>

    <!-- Preview Modal -->
    <div class="modal fade" id="previewModal" tabindex="-1">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="previewTitle">Vista Previa</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body preview-container" id="previewBody">
                    <div class="text-center p-4">Cargando vista previa...</div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                    <button type="button" class="btn btn-primary" id="downloadFromPreview">Descargar</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let refreshTimer = null;
        let currentPreviewFile = null;
        let currentTab = 'results';

        function switchTab(tab) {
            currentTab = tab;
            document.getElementById('tab-results').classList.remove('active');
            document.getElementById('tab-omitidos').classList.remove('active');
            document.getElementById('tab-' + tab).classList.add('active');
            loadFiles();
        }

        function loadFiles() {
            const endpoint = currentTab === 'results' ? '/api/list_results' : '/api/list_omitidos';
            
            fetch(endpoint)
                .then(r => r.json())
                .then(data => {
                    const tbody = document.getElementById('filesTableBody');
                    const countBadge = document.getElementById('fileCount');
                    
                    if (data.files.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No hay archivos aun</td></tr>';
                        countBadge.textContent = '0 archivos';
                        return;
                    }
                    
                    tbody.innerHTML = data.files.map(f => `
                        <tr class="file-row">
                            <td><strong>${escapeHtml(f.name)}</strong></td>
                            <td>${f.size_human}</td>
                            <td>${f.modified_human}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-primary" onclick="previewFile('${escapeHtml(f.name)}')">Ver</button>
                                <button class="btn btn-sm btn-outline-success" onclick="downloadFile('${escapeHtml(f.name)}')">Descargar</button>
                            </td>
                        </tr>
                    `).join('');
                    
                    countBadge.textContent = `${data.total} archivo${data.total !== 1 ? 's' : ''}`;
                    document.getElementById('lastUpdate').textContent = 'Actualizado: ' + new Date().toLocaleTimeString();
                })
                .catch(err => {
                    console.error('Error:', err);
                    document.getElementById('filesTableBody').innerHTML =
                        '<tr><td colspan="4" class="text-center text-danger">Error cargando archivos</td></tr>';
                });
        }

        function previewFile(filename) {
            currentPreviewFile = filename;
            document.getElementById('previewTitle').textContent = 'Vista Previa: ' + filename;
            document.getElementById('previewBody').innerHTML = '<div class="text-center p-4"><div class="spinner-border"></div></div>';
            
            const modal = new bootstrap.Modal(document.getElementById('previewModal'));
            modal.show();
            
            fetch(`/api/preview_csv?filename=${encodeURIComponent(filename)}&rows=50`)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('previewBody').innerHTML = `
                        <div class="p-3">
                            <div class="mb-3">
                                <span class="badge bg-primary">${data.total_rows} filas totales</span>
                                <span class="badge bg-secondary">${data.size_human}</span>
                                <span class="badge bg-info">Mostrando primeras ${data.preview_rows} filas</span>
                            </div>
                            <div class="table-responsive">
                                ${data.preview_html}
                            </div>
                        </div>
                    `;
                })
                .catch(err => {
                    document.getElementById('previewBody').innerHTML =
                        '<div class="text-center p-4 text-danger">Error cargando vista previa</div>';
                });
        }

        function downloadFile(filename) {
            window.location.href = `/api/download_file?filename=${encodeURIComponent(filename)}`;
        }

        document.getElementById('downloadFromPreview').addEventListener('click', () => {
            if (currentPreviewFile) {
                downloadFile(currentPreviewFile);
            }
        });

        function setRefreshInterval() {
            const interval = parseInt(document.getElementById('refreshInterval').value);
            if (refreshTimer) {
                clearInterval(refreshTimer);
                refreshTimer = null;
            }
            if (interval > 0) {
                refreshTimer = setInterval(loadFiles, interval);
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function updateCloudflareUrl() {
            fetch('/api/cloudflare_url')
                .then(r => r.json())
                .then(data => {
                    const urlBox = document.getElementById('cloudflareUrl');
                    if (data.url) {
                        urlBox.textContent = data.url;
                        urlBox.style.background = '#fff';
                    } else {
                        urlBox.textContent = 'URL no disponible - cloudflared no esta corriendo';
                        urlBox.style.background = '#f8d7da';
                    }
                })
                .catch(err => {
                    console.error('Error:', err);
                    const urlBox = document.getElementById('cloudflareUrl');
                    urlBox.textContent = 'Error obteniendo URL';
                    urlBox.style.background = '#f8d7da';
                });
        }

        // Cargar archivos al inicio
        loadFiles();
        setRefreshInterval();
        setInterval(updateCloudflareUrl, 10000);
        updateCloudflareUrl();
    </script>
</body>
</html>
        """
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)

    async def get_cloudflare_url(self):
        """Endpoint para obtener la URL de cloudflared desde los logs del visor de resultados."""
        try:
            import os
            import re
            
            # Directorio donde se guardan los logs de cloudflared
            cloudflare_log_dir = "/home/julio/cloudflared_logs"
            
            if not os.path.exists(cloudflare_log_dir):
                return {"url": None, "message": "No se encontraron logs de cloudflared"}
            
            # Buscar el archivo de log más reciente
            log_files = sorted(
                [f for f in os.listdir(cloudflare_log_dir) if f.startswith('cloudflared_')],
                key=lambda x: os.path.getmtime(os.path.join(cloudflare_log_dir, x)),
                reverse=True
            )
            
            if not log_files:
                return {"url": None, "message": "No se encontraron logs de cloudflared"}
            
            latest_log = os.path.join(cloudflare_log_dir, log_files[0])
            
            # Buscar la URL en el log
            url_pattern = r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com'
            
            with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                match = re.search(url_pattern, content)
                if match:
                    return {"url": match.group(0), "message": "URL encontrada"}
            
            return {"url": None, "message": "No se encontró URL en los logs de cloudflared"}
            
        except Exception as e:
            self.logger.error(f"Error obteniendo URL de cloudflared: {e}")
            return {"url": None, "message": f"Error: {str(e)}"}

    def _human_readable_size(self, size_bytes):
        """Convierte bytes a formato legible."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    async def root_endpoint(self):
        """Endpoint raíz para verificar que el servidor está activo."""
        return {"status": "active", "message": "Europa Scraper Server is running"}

    async def ping_endpoint(self):
        """Endpoint simple para ping de prueba."""
        return "EUROPA_SCRAPER_SERVER_PONG"

    async def emergency_reset(self):
        """Detiene todo, limpia colas y resetea el estado global."""
        self.logger.info("🚨 Recibida solicitud de RESET DE EMERGENCIA")
        await global_event_log.add(EventType.SYSTEM, "Server", "Iniciando RESET DE EMERGENCIA.")
        
        # 1. Detener procesos
        await self.stop_scraping_job()
        
        # 2. Limpiar estados
        if self.worker_states is not None:
            self.worker_states.clear()
        
        self.is_job_running = False
        
        await global_event_log.add(EventType.SUCCESS, "Server", "Sistema reseteado correctamente.")
        return {"status": "ok", "message": "Sistema reseteado correctamente"}

    async def get_events_endpoint(self, min_id: int = Query(0)):
        """Endpoint para que el cliente obtenga los eventos recientes."""
        events = await global_event_log.get_events(min_id)
        return {"events": events}

    async def debug_info(self):
        """Diagnostic endpoint to see server environment."""
        try:
            return {
                "cwd": os.getcwd(),
                "project_root": project_root,
                "results_exists": os.path.exists(os.path.join(project_root, 'results')),
                "files_in_results": len(os.listdir(os.path.join(project_root, 'results'))) if os.path.exists(os.path.join(project_root, 'results')) else 0,
                "environment": {k: v for k, v in os.environ.items() if "KEY" not in k and "AUTH" not in k},
                "version": "3.1.7-STABLE"
            }
        except Exception as e:
            return {"error": str(e)}

    async def version_endpoint(self):
        """Returns the current server version."""
        return {"version": "3.1.7-STABLE", "status": "OK"}

    def run(self):
        os.makedirs("logs", exist_ok=True)
        self.logger.info(f"Iniciando servidor en http://{self.host}:{self.port}")
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )

