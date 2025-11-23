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

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.scraper_gui import ScraperGUI

logger = logging.getLogger(__name__)

class ClientApp:
    def __init__(self):
        self.root = tk.Tk()
        # El título ahora se establece en la propia clase ScraperGUI
        self.queue = queue.Queue()
        self.gui = ScraperGUI(self.root, self)
        self.gui.pack(fill="both", expand=True)
        
        self.server_base_url = ""
        self.is_scraping = False
        self.status_poll_thread = None
        self.stop_polling = threading.Event()

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

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

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def start_scraping_on_server(self, server_address, params):
        # Extraer IP y puerto de la dirección del servidor
        try:
            if ' (' in server_address and ')' in server_address:
                start = server_address.find('(') + 1
                end = server_address.find(')')
                ip_port = server_address[start:end]
            else:
                ip_port = server_address
            
            self.server_base_url = f"http://{ip_port}"
            logger.info(f"Establecida la URL base del servidor: {self.server_base_url}")

        except Exception as e:
            self.queue.put(('log', f"Dirección de servidor inválida: {e}"))
            return

        threading.Thread(target=self._start_scraping_thread, args=(params,), daemon=True).start()

    def _start_scraping_thread(self, params):
        try:
            response = requests.post(f"{self.server_base_url}/start_scraping", json=params, timeout=10)
            response.raise_for_status()  # Lanza excepción para errores HTTP
            
            data = response.json()
            self.is_scraping = True
            self.queue.put(('log', f"Tarea de scraping iniciada. ID: {data.get('task_id')}"))
            
            # Iniciar el sondeo de estado
            self.stop_polling.clear()
            self.status_poll_thread = threading.Thread(target=self._poll_status, daemon=True)
            self.status_poll_thread.start()

        except requests.exceptions.RequestException as e:
            error_message = f"Error al iniciar el scraping: {e}"
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
        last_logs = []
        while not self.stop_polling.is_set():
            try:
                response = requests.get(f"{self.server_base_url}/status", timeout=30)
                if response.status_code == 200:
                    status = response.json()
                    
                    # Actualizar barra de progreso
                    self.queue.put(('update_progress', status.get('progress', 0)))
                    
                    # Actualizar logs del servidor
                    current_logs = status.get('logs', [])
                    new_logs = [log for log in current_logs if log not in last_logs]
                    for log_msg in new_logs:
                        self.queue.put(('server_log', log_msg))
                    last_logs = current_logs

                    # Manejar desafío CAPTCHA pendiente
                    pending_captcha = status.get('pending_captcha_challenge')
                    if pending_captcha:
                        # La GUI ahora espera el diccionario completo
                        self.gui.show_manual_captcha_input(pending_captcha, self._send_captcha_response)

                    # Comprobar si el scraping ha terminado
                    if not status.get('is_scraping') and self.is_scraping:
                        self.is_scraping = False
                        final_log = next((log for log in reversed(current_logs) if "completed" in log or "stopped" in log or "Error" in log), "Scraping finalizado.")
                        if "stopped" in final_log:
                            self.queue.put(('scraping_stopped', final_log))
                        else:
                            self.queue.put(('scraping_done', None))
                        self.stop_polling.set() # Detener el sondeo
                        break
                else:
                    logger.warning(f"El servidor devolvió un estado no esperado: {response.status_code}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Error al obtener el estado del servidor: {e}")
                time.sleep(5) # Esperar antes de reintentar en caso de error de red
            
            time.sleep(2) # Esperar 2 segundos entre sondeos

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

    def _on_closing(self):
        self.stop_polling.set()
        if self.is_scraping:
            self.stop_scraping() # Intentar detener el scraping si se está ejecutando
        self.root.destroy()

if __name__ == "__main__":
    # Configuración básica de logging para el cliente
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    app = ClientApp()
    app.run()