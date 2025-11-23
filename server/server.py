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
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager
import pandas as pd
import io

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
    status_dict[worker_id] = {'id': worker_id, 'status': 'Idle', 'progress': 0, 'current_task': 'None'}
    
    logger.info(f"Worker {worker_id} iniciado.")

    # --- Inicialización de componentes por proceso ---
    # Cada proceso necesita sus propias instancias para evitar conflictos.
    config_manager = Config(config_file=config_path)
    # ServerState es None aquí porque el worker no gestiona el estado global
    browser_manager = BrowserManager(config_manager=config_manager, server_state=None) 
    scraper_controller = ScraperController(config_manager=config_manager, browser_manager=browser_manager)

    # El bucle principal del trabajador
    while True:
        try:
            # Obtener un lote de trabajo de la cola
            batch: List[Tuple[str, str]] = work_queue.get()
            
            if batch is None:  # Señal de finalización
                logger.info(f"Worker {worker_id} recibió señal de finalización.")
                status_dict[worker_id] = {'id': worker_id, 'status': 'Finished', 'progress': 100, 'current_task': 'None'}
                break

            batch_id = f"{batch[0][0]}..{batch[-1][0]}"
            logger.info(f"Worker {worker_id} recibió lote {batch_id} con {len(batch)} cursos.")
            status_dict[worker_id] = {'id': worker_id, 'status': 'Running', 'progress': 0, 'current_task': batch_id}
            
            # --- Lógica de Scraping para el Lote ---
            # El ScraperController espera un rango, no un lote.
            # Adaptamos los parámetros para que coincidan.
            params = {
                'from_sic': batch[0][0],
                'to_sic': batch[-1][0],
                'from_course': batch[0][1],
                'to_course': batch[-1][1],
                'is_headless': True # O obtener de config
            }

            def progress_callback(percentage, message, *args):
                # Actualizar el progreso del trabajador
                status_dict[worker_id] = {'id': worker_id, 'status': 'Running', 'progress': percentage, 'current_task': message}
            
            # run_scraping es una corutina, necesitamos ejecutarla en un bucle de eventos.
            # Cada worker tiene su propio bucle.
            asyncio.run(scraper_controller.run_scraping(
                params=params,
                progress_callback=progress_callback,
                worker_id=worker_id,
                # Pasamos el lote de cursos para que el controlador sepa exactamente qué procesar
                course_batch=batch 
            ))

            logger.info(f"Worker {worker_id} completó el lote {batch_id}.")
            work_queue.task_done()

        except Empty:
            # Esto no debería ocurrir con un `get()` bloqueante, pero es una salvaguarda
            logger.info(f"Worker {worker_id}: Cola de trabajo vacía. Esperando...")
            time.sleep(1)
        except Exception:
            logger.error(f"Worker {worker_id}: Error catastrófico.", exc_info=True)
            status_dict[worker_id] = {'id': worker_id, 'status': 'Error', 'progress': 0, 'current_task': 'CRASHED'}
            # Marcar la tarea como hecha para no bloquear la cola si hay un error
            if 'work_queue' in locals() and isinstance(work_queue, multiprocessing.JoinableQueue):
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
        # No iniciamos el pool aquí, se inicia bajo demanda.

    async def _shutdown(self):
        self.logger.info("Deteniendo el pool de trabajadores...")
        self._stop_worker_pool()
        self._stop_broadcasting()
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
        self.app.get("/")(self.root_endpoint)
        self.app.get("/ping")(self.ping_endpoint)
        
        # Agregar logging para verificar que las rutas se registraron
        self.logger.info("Rutas registradas:")
        for route in self.app.routes:
            self.logger.info(f"  {route.methods} {route.path}")

    # --- Endpoints de la API ---

    async def start_scraping_job(self, job_params: ScrapingJob):
        if self.is_job_running:
            raise HTTPException(status_code=409, detail="Ya hay un trabajo de scraping en progreso.")

        self.logger.info(f"Recibido nuevo trabajo de scraping: {job_params.model_dump()}")
        self.is_job_running = True

        try:
            # 1. Obtener todos los cursos de la base de datos
            db_path = os.path.join(project_root, 'courses.db')
            if not os.path.exists(db_path):
                raise HTTPException(status_code=404, detail="La base de datos 'courses.db' no existe. Por favor, suba un archivo de cursos primero.")
            db_handler = SQLiteHandler(db_path)
            all_courses = db_handler.get_all_courses() # Devuelve lista de tuplas (sic_code, course_name)
            
            # 2. Filtrar cursos basados en el rango SIC del trabajo
            start_index = next((i for i, (sic, _) in enumerate(all_courses) if sic == job_params.from_sic), 0)
            end_index = next((i for i, (sic, _) in enumerate(all_courses) if sic == job_params.to_sic), len(all_courses) - 1)
            courses_to_process = all_courses[start_index : end_index + 1]
            
            if not courses_to_process:
                self.is_job_running = False
                raise HTTPException(status_code=404, detail="No se encontraron cursos en el rango SIC especificado.")

            # 3. Dividir el trabajo en lotes pequeños y ponerlos en la cola
            num_courses = len(courses_to_process)
            self.logger.info(f"Se procesarán {num_courses} cursos. Dividiendo en lotes de {BATCH_SIZE}.")
            for i in range(0, num_courses, BATCH_SIZE):
                batch = courses_to_process[i:i + BATCH_SIZE]
                self.work_queue.put(batch)

            # 4. Iniciar el pool de trabajadores
            self._start_worker_pool(NUM_PROCESSES)

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
        self.logger.info("Todas las tareas de la cola han sido completadas.")
        self._stop_worker_pool()

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
                df = pd.read_csv(io.BytesIO(contents))
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
            db_handler.insert_courses(courses_to_load)
            
            return {"message": f"Carga exitosa. Se han cargado {len(courses_to_load)} cursos en la base de datos."}

        except Exception as e:
            self.logger.exception("Error procesando el archivo de cursos cargado.")
            raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

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

