#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Clase del Servidor Principal del Scraper Europa
==============================================
Encapsula la lógica y el estado del servidor FastAPI.
"""

import os
import sys
import asyncio
import logging
import socket
import threading
import time
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager

# Añadir el directorio raíz al path para importar módulos
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import setup_logger
from utils.config import Config
from controllers.scraper_controller import ScraperController
from utils.scraper.browser_manager import BrowserManager

# --- Modelos de Datos (Pydantic) ---
class ScrapingTask(BaseModel):
    from_sic: str
    to_sic: str
    from_course: str
    to_course: str
    min_words: int = 30
    search_engine: str = 'Cordis Europa'
    site_domain: Optional[str] = None
    is_headless: bool = True

class CaptchaSolution(BaseModel):
    captcha_id: str
    solution: str

# --- Estado del Servidor ---
class ServerState:
    """Gestiona el estado concurrente del servidor."""
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.is_scraping = False
        self.status_log: list[str] = []
        self.progress = 0.0
        self.current_task_id: Optional[str] = None
        self.lock = threading.Lock()
        self.captcha_solution_queue = asyncio.Queue()
        self.pending_captcha_challenge: Optional[Dict[str, Any]] = None

    def start_task(self, task_id: str) -> bool:
        with self.lock:
            if self.is_scraping:
                return False
            self.is_scraping = True
            self.current_task_id = task_id
            self.status_log = ["Scraping task started."]
            self.progress = 0.0
            self.pending_captcha_challenge = None
            return True

    def end_task(self, message: str):
        with self.lock:
            self.is_scraping = False
            self.current_task_id = None
            self.status_log.append(message)
            self.pending_captcha_challenge = None

    def add_log(self, message: str):
        with self.lock:
            self.status_log.append(message)

    def set_progress(self, percentage: float):
        with self.lock:
            self.progress = percentage

    def set_pending_captcha_challenge(self, challenge_data: Dict[str, Any]):
        with self.lock:
            self.pending_captcha_challenge = challenge_data
            captcha_id = challenge_data.get('id', '<no-id>')
            self.logger.info(f"CAPTCHA challenge {captcha_id} set as pending.")

    def clear_pending_captcha_challenge(self):
        with self.lock:
            self.pending_captcha_challenge = None
            self.logger.info("Pending CAPTCHA challenge cleared.")

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            status = {
                "is_scraping": self.is_scraping,
                "progress": self.progress,
                "logs": self.status_log[-20:],
                "task_id": self.current_task_id
            }
            if self.pending_captcha_challenge:
                status["pending_captcha_challenge"] = self.pending_captcha_challenge
            return status

# --- Clase Principal del Servidor ---
class ScraperServer:
    def __init__(self, host="0.0.0.0", port=8001):
        self.host = host
        self.port = port
        self.logger = setup_logger(logging.DEBUG, 'logs/server.log')
        
        self.config_manager = Config(config_file=os.path.join(project_root, 'client', 'config.json'))
        self.server_state = ServerState(self.logger)
        self.browser_manager = BrowserManager(config_manager=self.config_manager, server_state=self.server_state)
        self.scraper_controller = ScraperController(config_manager=self.config_manager, browser_manager=self.browser_manager)

        self.app = FastAPI(
            title="Europa Scraper Server",
            version="2.1.0",
            lifespan=self._lifespan
        )
        self._setup_routes()

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        await self._startup()
        yield
        await self._shutdown()

    async def _startup(self):
        self.logger.info("Iniciando servidor Europa Scraper...")

        if getattr(sys, 'frozen', False):
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.join(sys._MEIPASS, 'ms-playwright')

        await asyncio.sleep(2)

        self.logger.info("Inicializando instancia global del navegador...")
        headless_mode = self.config_manager.get("headless_mode", True)
        self.logger.info(f"El navegador se lanzará con headless={headless_mode}")
        await self.browser_manager.initialize(headless=headless_mode)

        self._parse_cli_args()

        broadcast_thread = threading.Thread(target=self._broadcast_presence, daemon=True)
        broadcast_thread.start()

    async def _shutdown(self):
        self.logger.info("Cerrando la instancia global del navegador...")
        await self.browser_manager.close()

    def _parse_cli_args(self):
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                try:
                    self.port = int(sys.argv[i + 1])
                    self.logger.info(f"Puerto del servidor establecido a {self.port} desde la línea de comandos.")
                except ValueError:
                    self.logger.warning(f"Argumento de puerto inválido. Usando el puerto por defecto {self.port}.")
                break

    def _broadcast_presence(self):
        BROADCAST_PORT = 6000
        try:
            server_ip = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            self.logger.error("No se pudo obtener la IP del host. La difusión de presencia está desactivada.")
            return
            
        message = f"EUROPA_SCRAPER_SERVER;{server_ip};{self.port}".encode('utf-8')

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            while True:
                try:
                    sock.sendto(message, ('255.255.255.255', BROADCAST_PORT))
                    self.logger.debug(f"Difundiendo presencia en ('255.255.255.255', {BROADCAST_PORT})")
                    time.sleep(10)
                except Exception as e:
                    self.logger.error(f"Error al difundir presencia: {e}")
                    break

    def _setup_routes(self):
        self.app.post("/start_scraping", status_code=202)(self.start_scraping)
        self.app.post("/stop_scraping")(self.stop_scraping)
        self.app.get("/status")(self.get_status)
        self.app.post("/submit_captcha_solution")(self.submit_captcha_solution)

    async def run_scraping_task(self, task_id: str, params: Dict[str, Any]):
        self.logger.info(f"Procesando tarea: {task_id}")

        def progress_callback(percentage, message, *args):
            self.server_state.set_progress(percentage)
            self.server_state.add_log(message)

        try:
            await self.scraper_controller.run_scraping(
                params=params,
                progress_callback=progress_callback
            )

            final_message = "Proceso de scraping detenido por el usuario." if self.scraper_controller.is_stop_requested() else "Proceso de scraping completado con éxito."
            self.logger.info(f"La tarea {task_id} {'fue detenida' if self.scraper_controller.is_stop_requested() else 'completó normalmente'}.")
            self.server_state.end_task(final_message)

        except Exception as e:
            self.logger.exception(f"Error al procesar la tarea {task_id}")
            self.server_state.end_task(f"Error durante el scraping: {e}")

    async def start_scraping(self, task: ScrapingTask):
        task_id = f"task_{int(asyncio.get_running_loop().time())}"
        if not self.server_state.start_task(task_id):
            raise HTTPException(status_code=409, detail="Ya hay una tarea de scraping en progreso.")
        
        self.logger.info(f"Creando tarea de fondo para scraping: {task.model_dump()}")
        asyncio.create_task(self.run_scraping_task(task_id, task.model_dump()))
        
        return {"message": "Tarea de scraping iniciada.", "task_id": task_id}

    async def stop_scraping(self):
        if not self.server_state.is_scraping:
            raise HTTPException(status_code=404, detail="No hay ninguna tarea de scraping en ejecución.")
        
        self.logger.info("Se recibió una solicitud para detener el scraping.")
        self.scraper_controller.request_stop()
        
        return {"message": "Solicitud de detención recibida. El proceso terminará en breve."}

    async def get_status(self):
        return self.server_state.get_status()

    async def submit_captcha_solution(self, captcha_data: CaptchaSolution):
        await self.server_state.captcha_solution_queue.put(captcha_data.model_dump())
        self.logger.info(f"Solución de CAPTCHA {captcha_data.captcha_id} recibida del cliente.")
        return {"message": "Solución de CAPTCHA recibida."}

    def run(self):
        os.makedirs("logs", exist_ok=True)
        self.logger.info(f"Iniciando servidor en http://{self.host}:{self.port}")
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
