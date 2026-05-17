#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cliente Principal del Scraper Europa
==================================
Este script maneja la lógica del cliente, incluyendo la comunicación con el servidor y la GUI.
"""

import tkinter as tk
import threading
import queue
import json
import logging
import time
import requests
import sys
import os
import base64
from PIL import Image, ImageTk
import io

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.scraper_gui import ScraperGUI

logger = logging.getLogger(__name__)

class ClientApp:
    def __init__(self):
        self.root = tk.Tk()
        self.queue = queue.Queue()
        
        # Cargar configuración del servidor PRIMERO
        self.server_base_url = self._load_server_config()
        
        self.gui = ScraperGUI(self.root, self)
        self.gui.pack(fill="both", expand=True)
        
        self.is_scraping = False
        self.scraping_start_time = None
        self.stop_polling = threading.Event()
        
        # Iniciar hilo de monitoreo de estado
        self.status_poll_thread = threading.Thread(target=self._poll_status, daemon=True)
        self.status_poll_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _load_server_config(self):
        """Cargar configuración del servidor desde server_config.json"""
        try:
            # Primero intentar cargar la configuración empotrada o local
            config_path = get_resource_path(os.path.join('client', 'server_config.json'))
            if not os.path.exists(config_path):
                # Fallback por si acaso estamos en dev
                config_path = os.path.join(os.path.dirname(__file__), 'server_config.json')
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    server_config = config.get('server', {})
                    host = server_config.get('host') or 'localhost'
                    port = server_config.get('port', 8001)
                    
                    # Detect scheme based on port
                    scheme = "https" if port == 443 else "http"
                    url = f"{scheme}://{host}:{port}"
                    
                    logger.info(f"Configuracion del servidor cargada: {url}")
                    return url
            else:
                return "http://localhost:8001"
        except Exception as e:
            logger.error(f"Error cargando configuracion del servidor: {e}")
            return "http://localhost:8001"

    def run(self):
        self.process_queue()
        self.root.mainloop()

    def process_queue(self):
        try:
            while True:
                message_type, data = self.queue.get_nowait()
                if message_type == 'log':
                    self.gui._log_callback(data)
                elif message_type == 'update_progress':
                    self.gui.progress_frame.update_progress(data)
                elif message_type == 'server_log':
                    self.gui.results_frame.add_log(f"[SERVER] {data}")
                elif message_type == 'scraping_done':
                    self.gui.handle_scraping_finished()
                elif message_type == 'scraping_stopped':
                    self.gui.handle_scraping_stopped(data)
                elif message_type == 'add_server_to_listbox':
                    if data not in self.gui.server_listbox.get(0, tk.END):
                        self.gui.server_listbox.insert(tk.END, data)
                elif message_type == 'discovery_finished':
                    self.gui.refresh_servers_button.config(state=tk.NORMAL)
                    self.gui.discovery_status_label.config(text="Búsqueda finalizada.")
                elif message_type == 'update_worker_status':
                    if hasattr(self.gui, '_render_worker_status'):
                        self.gui._render_worker_status(data)

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def start_scraping_on_server(self, server_address, params):
        if self.is_scraping:
            self.queue.put(('log', "❌ Error: Ya hay un trabajo de scraping en progreso."))
            return

        # Extraer IP y puerto de la dirección del servidor
        try:
            if ' (' in server_address and ')' in server_address:
                start = server_address.find('(') + 1
                end = server_address.find(')')
                ip_port = server_address[start:end]
            else:
                ip_port = server_address
            
            # Fix: Replace 0.0.0.0 with localhost for client connections
            if ip_port.startswith('0.0.0.0:'):
                ip_port = ip_port.replace('0.0.0.0:', 'localhost:')
            
            # Soporte para HTTPS y HTTP explícitos
            if ip_port.startswith("http://") or ip_port.startswith("https://"):
                self.server_base_url = ip_port
            else:
                self.server_base_url = f"http://{ip_port}"
            
            logger.info(f"Establecida la URL base del servidor: {self.server_base_url}")

        except Exception as e:
            self.queue.put(('log', f"Dirección de servidor inválida: {e}"))
            return

        threading.Thread(target=self._start_scraping_thread, args=(params,), daemon=True).start()

    def _start_scraping_thread(self, params):
        try:
            url = f"{self.server_base_url}/start_scraping"
            logger.info(f"🚀 Enviando solicitud POST a: {url}")
            logger.info(f"📦 Parámetros: {json.dumps(params, indent=2)}")
            
            response = requests.post(url, json=params, timeout=10)
            response.raise_for_status()  
            
            data = response.json()
            task_id = data.get('task_id', 'N/A')
            message = data.get('message', 'Sin mensaje del servidor')
            
            self.is_scraping = True
            self.scraping_start_time = time.time()
            self.queue.put(('log', f"✅ {message}"))
            self.queue.put(('log', f"🆔 Tarea iniciada. ID: {task_id}"))
            
            # Ya no iniciamos el sondeo redundante aquí. La GUI (scraper_gui.py) 
            # tiene su propio mecanismo superior de polling de estado.
            self.stop_polling.clear()

        except requests.exceptions.RequestException as e:
            error_message = f"❌ Error al iniciar el scraping: {e}"
            logger.error(error_message)
            self.queue.put(('log', error_message))
            self.is_scraping = False

    def stop_scraping(self):
        if not self.is_scraping or not self.server_base_url:
            self.queue.put(('log', "No hay ninguna tarea de scraping activa para detener."))
            return

        try:
            response = requests.post(f"{self.server_base_url}/stop_scraping", timeout=10)
            response.raise_for_status()
            self.queue.put(('log', "Solicitud de detención enviada al servidor."))
        except requests.exceptions.RequestException as e:
            self.queue.put(('log', f"Error al enviar la solicitud de detención: {e}"))
        finally:
            self.is_scraping = False
            self.stop_polling.set() # Detener el sondeo

    def _poll_status(self):
        """
        OBSOLETO: El polling redundante ha sido eliminado.
        La GUI (scraper_gui.py) ahora se encarga de realizar un único polling a /detailed_status
        para sincronizar temporizadores, interfaz y estado final.
        """
        pass

    def _send_captcha_response(self, captcha_id, solution):
        try:
            response = requests.post(
                f"{self.server_base_url}/submit_captcha_solution",
                json={'captcha_id': captcha_id, 'solution': solution},
                timeout=10
            )
            response.raise_for_status()
            self.queue.put(('log', f"Solución de CAPTCHA {captcha_id} enviada al servidor."))
        except requests.exceptions.RequestException as e:
            error_message = f"Error al enviar la solución de CAPTCHA {captcha_id}: {e}"
            logger.error(error_message)
            self.queue.put(('log', error_message))

    def force_reset_state(self):
        """Forza el reseteo del estado de scraping del cliente y del servidor."""
        logger.warning("Forzando el reseteo del estado del cliente y servidor.")
        self.is_scraping = False
        self.stop_polling.set()
        
        # Intentar notificar al servidor del reseteo
        try:
            url = f"{self.server_base_url}/force_reset"
            requests.post(url, timeout=5)
            logger.info("Solicitud de reseteo enviada al servidor.")
        except Exception as e:
            logger.error(f"No se pudo notificar al servidor del reseteo: {e}")

        self.queue.put(('log', "⚠️ Sistema reiniciado (Cliente + Servidor). El estado ahora es 'Inactivo'."))
        
        # Notificar a la GUI para que actualice los botones
        if self.gui:
            self.gui.control_frame.start_button.config(state=tk.NORMAL)
            self.gui.control_frame.stop_button.config(state=tk.DISABLED)

    def _on_closing(self):
        self.stop_polling.set()
        # if self.is_scraping:
        #     self.stop_scraping() # Intentar detener el scraping si se está ejecutando
        self.root.destroy()

if __name__ == "__main__":
    # Configuración básica de logging para el cliente
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    app = ClientApp()
    app.run()