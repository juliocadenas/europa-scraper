#!/bin/bash
echo "🔧 Aplicando corrección al cliente..."

cd ~/docu_scraper

# Crear el archivo corregido
cat > client/main_fixed.py << 'EOF'
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
                try:
                    func, args = self.queue.get_nowait()
                except queue.Empty:
                    break
                else:
                    func(*args)
        finally:
            self.root.after(100, self.process_queue)

    def _on_closing(self):
        """Clean shutdown when closing the GUI"""
        if self.is_scraping:
            self.stop_scraping()
        self.root.quit()
        self.root.destroy()

    def set_server_address(self, server_address):
        """Set the server base URL from the GUI input"""
        try:
            # Remove any surrounding whitespace
            server_address = server_address.strip()
            
            # Handle different address formats
            if server_address.startswith('http://'):
                ip_port = server_address[7:]  # Remove http://
            elif server_address.startswith('https://'):
                ip_port = server_address[8:]  # Remove https://
            else:
                ip_port = server_address
            
            # Remove any trailing slash
            ip_port = ip_port.rstrip('/')
            
            # Handle tuple format if somehow passed
            if isinstance(ip_port, tuple):
                ip_port = f"{ip_port[0]}:{ip_port[1]}"
            elif '(' in ip_port and ')' in ip_port:
                start = ip_port.find('(') + 1
                end = ip_port.find(')')
                ip_port = ip_port[start:end]
            
            # CORRECCIÓN: Reemplazar 0.0.0.0 por localhost para conexiones de cliente
            if ip_port.startswith("0.0.0.0:"):
                ip_port = "localhost:" + ip_port.split(":")[1]
                
            self.server_base_url = f"http://{ip_port}"
            logger.info(f"Establecida la URL base del servidor: {self.server_base_url}")

        except Exception as e:
            self.queue.put(('log', f"Dirección de servidor inválida: {e}"))        
            return

    def start_scraping(self, params):
        """Start the scraping process"""
        if self.is_scraping:
            self.queue.put(('log', "El scraping ya está en progreso."))
            return

        if not self.server_base_url:
            self.queue.put(('log', "Por favor, configure una dirección de servidor válida."))
            return

        try:
            response = requests.post(f"{self.server_base_url}/start_scraping", json=params, timeout=10)
            
            if response.status_code == 200:
                self.is_scraping = True
                self.stop_polling.clear()
                
                # Start status polling thread
                self.status_poll_thread = threading.Thread(target=self._poll_status, daemon=True)
                self.status_poll_thread.start()
                
                self.queue.put(('log', "Scraping iniciado exitosamente."))
            else:
                self.queue.put(('log', f"Error al iniciar scraping: {response.status_code} - {response.text}"))
                
        except requests.exceptions.ConnectionError:
            self.queue.put(('log', "Error de conexión: No se puede conectar al servidor. Verifique la dirección y que el servidor esté en ejecución."))
        except requests.exceptions.Timeout:
            self.queue.put(('log', "Error de conexión: Tiempo de espera agotado."))
        except Exception as e:
            self.queue.put(('log', f"Error al iniciar scraping: {e}"))

    def stop_scraping(self):
        """Stop the scraping process"""
        if not self.is_scraping or not self.server_base_url:
            return

        try:
            response = requests.post(f"{self.server_base_url}/stop_scraping", timeout=10)
            
            if response.status_code == 200:
                self.queue.put(('log', "Scraping detenido."))
            else:
                self.queue.put(('log', f"Error al detener scraping: {response.status_code}"))
                
        except Exception as e:
            self.queue.put(('log', f"Error al detener scraping: {e}"))
        finally:
            self.is_scraping = False
            self.stop_polling.set()

    def _poll_status(self):
        """Poll the server for status updates"""
        while self.is_scraping and not self.stop_polling.is_set():
            try:
                response = requests.get(f"{self.server_base_url}/status", timeout=30)
                
                if response.status_code == 200:
                    status_data = response.json()
                    
                    # Update GUI with status information
                    self.queue.put(('update_status', status_data))
                    
                    # Check if scraping is complete
                    if status_data.get('status') == 'completed':
                        self.is_scraping = False
                        self.queue.put(('log', "Scraping completado."))
                        break
                    elif status_data.get('status') == 'error':
                        self.is_scraping = False
                        self.queue.put(('log', f"Error en scraping: {status_data.get('error', 'Error desconocido')}"))
                        break
                        
                else:
                    self.queue.put(('log', f"Error al obtener estado: {response.status_code}"))
                    
            except requests.exceptions.ConnectionError:
                self.queue.put(('log', "Error de conexión al obtener estado."))
                break
            except requests.exceptions.Timeout:
                self.queue.put(('log', "Tiempo de espera agotado al obtener estado."))
                continue
            except Exception as e:
                self.queue.put(('log', f"Error al obtener estado: {e}"))
                break
                
            time.sleep(2)  # Poll every 2 seconds

    def submit_captcha_solution(self, captcha_id, solution):
        """Submit CAPTCHA solution to server"""
        if not self.server_base_url:
            return False
            
        try:
            response = requests.post(
                f"{self.server_base_url}/submit_captcha_solution",
                json={
                    'captcha_id': captcha_id,
                    'solution': solution
                },
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            self.queue.put(('log', f"Error al enviar solución CAPTCHA: {e}"))
            return False

def main():
    """Main entry point for the client application"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        app = ClientApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("Cliente detenido por el usuario")
    except Exception as e:
        logger.error(f"Error en cliente: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

# Reemplazar el archivo original
mv client/main_fixed.py client/main.py

echo "✅ Corrección aplicada exitosamente"
echo "🔍 Verificando la corrección..."
grep -n -A3 -B1 "CORRECCIÓN" client/main.py