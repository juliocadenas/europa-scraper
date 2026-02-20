#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GUI del Scraper para el Cliente Europa (Simplificada)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import os
import sys
import threading
import requests
from typing import List
import queue
import base64
from PIL import Image, ImageTk
import io

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket

from gui.styles import setup_styles
from gui.timer_manager import TimerManager
from gui.components.gui_components import ProgressFrame, ResultsFrame, ControlFrame
from utils.sqlite_handler import SQLiteHandler
from utils.logger import get_global_log_handler
from gui.config_tab import ConfigTab
from gui.components.worker_status_frame import WorkerStatusFrame
from utils.config import Config

logger = logging.getLogger(__name__)

class ScraperClientGUI(ttk.Frame):
    """ Interfaz gráfica simplificada para el cliente. """

    def __init__(self, master, parent_app):
        super().__init__(master)
        self.parent_app = parent_app
        self.config = Config()
        self.captcha_response_queue = queue.Queue()
        self.captcha_window_open = False

        if getattr(sys, 'frozen', False):
            # Running as a bundled exe, the database should be in the same directory
            base_path = os.path.dirname(sys.executable)
        else:
            # Running as a script, go up one level from the client folder
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        
        db_path = os.path.join(base_path, 'courses.db')
        self.sqlite_handler = SQLiteHandler(db_path=db_path)
        self.timer_manager = TimerManager(update_callback=self._update_timer_display)

        self._setup_ui()
        self._load_data_into_ui()
        self._prepopulate_server_listbox()

        global_log_handler = get_global_log_handler()
        if global_log_handler:
            global_log_handler.set_callback(self._log_callback)

    def _update_timer_display(self, time_str):
        self.timer_label.config(text=f"Tiempo: {time_str}")

    def _log_callback(self, log_entry):
        if hasattr(self, 'results_frame'):
            self.results_frame.add_log(log_entry)

    def _setup_ui(self):
        setup_styles()
        self.scraper_notebook = ttk.Notebook(self)
        self.scraper_notebook.pack(fill=tk.BOTH, expand=True)

        self.program_tab = ttk.Frame(self.scraper_notebook)
        self.scraper_notebook.add(self.program_tab, text='Programar Rangos')

        # Configurar grid para 3 columnas de igual peso
        self.program_tab.grid_rowconfigure(0, weight=1)
        self.program_tab.grid_columnconfigure(0, weight=1)
        self.program_tab.grid_columnconfigure(1, weight=2)  # Dar más peso a la columna central
        self.program_tab.grid_columnconfigure(2, weight=1)

        try:
            config = Config()
            self.config_tab = ConfigTab(self.scraper_notebook, config)
        except Exception as e:
            logger.error(f"Error inicializando pestaña de configuración: {e}")

        self.log_tab = ttk.Frame(self.scraper_notebook)
        self.scraper_notebook.add(self.log_tab, text='Log de Resultados')

        self._setup_range_selection_ui()
        self._setup_log_tab()

    def _setup_range_selection_ui(self):
        # Columna 1: Conexión y Configuración de Búsqueda
        left_column_frame = ttk.Frame(self.program_tab)
        left_column_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        left_column_frame.grid_rowconfigure(0, weight=1)
        left_column_frame.grid_rowconfigure(1, weight=1)

        server_input_frame = ttk.LabelFrame(left_column_frame, text="Conexión del Servidor", padding="10")
        server_input_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        
        self.server_listbox = tk.Listbox(server_input_frame, exportselection=False)
        self.server_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        self.refresh_servers_button = ttk.Button(server_input_frame, text="Refrescar Servidores", command=self._discover_servers)
        self.refresh_servers_button.pack(fill=tk.X, pady=5)

        self.discovery_status_label = ttk.Label(server_input_frame, text="")
        self.discovery_status_label.pack(fill=tk.X, pady=2)

        self.configure_firewall_button = ttk.Button(server_input_frame, text="Configurar Firewall (UDP 6000)", command=self._configure_firewall)
        self.configure_firewall_button.pack(fill=tk.X, pady=5)

        # Frame para Configuración de Búsqueda
        search_config_frame = ttk.LabelFrame(left_column_frame, text="Configuración de Búsqueda", padding="10")
        search_config_frame.grid(row=1, column=0, sticky="nsew", pady=(5, 0))

        ttk.Label(search_config_frame, text="Motor de Búsqueda:").pack(fill=tk.X, pady=(0, 2))
        self.search_engine_combo = ttk.Combobox(search_config_frame, values=["Cordis Europa API", "Google", "DuckDuckGo", "Cordis Europa", "Common Crawl", "Wayback Machine"], state="readonly")
        self.search_engine_combo.set("Cordis Europa API")
        self.search_engine_combo.pack(fill=tk.X, pady=(0, 5))
        self.search_engine_combo.bind("<<ComboboxSelected>>", self._on_search_engine_change)

        self.site_domain_label = ttk.Label(search_config_frame, text="Dominio (site:)")
        self.site_domain_label.pack(fill=tk.X, pady=(5, 2))
        self.site_domain_entry = ttk.Entry(search_config_frame, state=tk.DISABLED)
        self.site_domain_entry.insert(0, "usa.gov")
        self.site_domain_entry.pack(fill=tk.X, pady=(0, 5))

        # Trigger the change event to set the initial state of the site_domain entry
        self._on_search_engine_change(None)

        # Columna 2: Selección de Código (Treeview)
        sic_frame = ttk.LabelFrame(self.program_tab, text="Selección de Código", padding=10)
        sic_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self._setup_sic_selection_frame(sic_frame)

        # Columna 3: Controles y Progreso
        controls_main_frame = ttk.LabelFrame(self.program_tab, text="Controles", padding="10")
        controls_main_frame.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)

        self.timer_label = ttk.Label(controls_main_frame, text="Tiempo: 00:00:00", style="Timer.TLabel")
        self.timer_label.pack(side=tk.TOP, anchor=tk.E, padx=10, pady=5)
        
        self.control_frame = ControlFrame(controls_main_frame, on_start=self._on_start_scraping, on_stop=self._on_stop_scraping)
        self.control_frame.pack(fill=tk.X, pady=2)
        
        self.progress_frame = ProgressFrame(controls_main_frame)
        self.progress_frame.pack(fill=tk.X, pady=2)

        self.worker_status_frame = WorkerStatusFrame(controls_main_frame)
        self.worker_status_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    def _on_search_engine_change(self, event):
        selected_engine = self.search_engine_combo.get()
        if selected_engine in ["Google", "DuckDuckGo", "Common Crawl", "Common Crawl (Guiado por Google)", "Wayback Machine"]:
            self.site_domain_entry.config(state=tk.NORMAL)
        else:
            self.site_domain_entry.config(state=tk.DISABLED)

    def _setup_sic_selection_frame(self, parent_frame):
        selection_buttons_frame = ttk.Frame(parent_frame)
        selection_buttons_frame.pack(fill=tk.X, pady=5)

        ttk.Button(selection_buttons_frame, text="Seleccionar 10", command=lambda: self._select_n_items(10)).pack(side=tk.LEFT, padx=5)
        ttk.Button(selection_buttons_frame, text="Seleccionar 25", command=lambda: self._select_n_items(25)).pack(side=tk.LEFT, padx=5)
        ttk.Button(selection_buttons_frame, text="Seleccionar 50", command=lambda: self._select_n_items(50)).pack(side=tk.LEFT, padx=5)

        tree_frame = ttk.Frame(parent_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        self.course_tree = ttk.Treeview(tree_frame, columns=("ID", "Código SIC", "Nombre del Curso", "Estado", "Servidor"), show="headings", selectmode="extended", yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.config(command=self.course_tree.yview)
        hsb.config(command=self.course_tree.xview)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.course_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.course_tree.bind("<<TreeviewSelect>>", self._on_tree_selection_changed)
        self.course_tree.bind("<Button-3>", self._show_context_menu)

        self.course_tree.heading("ID", text="#")
        self.course_tree.heading("Código SIC", text="Código SIC")
        self.course_tree.heading("Nombre del Curso", text="Nombre del Curso")
        self.course_tree.heading("Estado", text="Estado")
        self.course_tree.heading("Servidor", text="Servidor")

        self.course_tree.column("ID", width=50, anchor="center", stretch=False)
        self.course_tree.column("Código SIC", width=120, stretch=True)
        self.course_tree.column("Nombre del Curso", width=400, stretch=True)
        self.course_tree.column("Estado", width=120, stretch=True)
        self.course_tree.column("Servidor", width=180, stretch=True)

        self.course_tree.tag_configure("processing", background="#FFDDC1")
        self.course_tree.tag_configure("completed", background="#D4EDDA", foreground="#666666")

    def _select_n_items(self, n):
        self.course_tree.selection_set()
        all_items = self.course_tree.get_children()
        if not all_items:
            return

        available_items = []
        for item_id in all_items:
            status = self.course_tree.item(item_id, 'values')[3]
            if status.lower() not in ["procesando", "completado"]:
                available_items.append(item_id)

        items_to_select = available_items[:n]
        
        self.course_tree.selection_set(items_to_select)
        if items_to_select:
            self.course_tree.see(items_to_select[-1])

    def _setup_log_tab(self):
        self.results_frame = ResultsFrame(self.log_tab)
        self.results_frame.pack(fill=tk.BOTH, expand=True)

    def _prepopulate_server_listbox(self):
        """Pre-popula el listbox con la URL del servidor configurada en server_config.json."""
        try:
            configured_url = self.parent_app.server_base_url
            if configured_url:
                self.server_listbox.delete(0, tk.END)
                self.server_listbox.insert(tk.END, configured_url)
                self.server_listbox.selection_set(0)
                logger.info(f"Servidor pre-configurado añadido al listbox: {configured_url}")
        except Exception as e:
            logger.error(f"Error pre-populando listbox de servidor: {e}")

    def _load_data_into_ui(self):
        self.detailed_sic_codes_with_courses = self.sqlite_handler.get_detailed_sic_codes_with_courses()
        if not self.detailed_sic_codes_with_courses:
            messagebox.showwarning("Sin Datos", "No se encontraron datos de cursos en la base de datos.")
            return

        for i in self.course_tree.get_children():
            self.course_tree.delete(i)

        for i, item in enumerate(self.detailed_sic_codes_with_courses):
            item_id = str(i + 1)
            sic_code, course_name, status, server = item
            tag = "normal"
            if status and status.lower() == "procesando": tag = "processing"
            elif status and status.lower() == "completado": tag = "completed"
            self.course_tree.insert("", "end", iid=f"item_{item_id}", values=(item_id, sic_code, course_name, status, server), tags=(tag,))

    

    def _discover_servers(self):
        """Descubre servidores en la red local."""
        logger.info("Descubriendo servidores...")
        self.server_listbox.delete(0, tk.END)
        self.refresh_servers_button.config(state=tk.DISABLED)
        self.discovery_status_label.config(text="Buscando servidores...")
        self.master.update_idletasks() # Force UI update

        # Iniciar un hilo para escuchar broadcasts y no bloquear la GUI
        threading.Thread(target=self._listen_for_servers, daemon=True).start()

    def _listen_for_servers(self):
        """Escucha broadcasts de servidores en un hilo separado."""
        BROADCAST_PORT = 6000
        
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', BROADCAST_PORT))
            sock.settimeout(5)  # Esperar 5 segundos por respuestas

            logger.info(f"Escuchando en el puerto {BROADCAST_PORT} por broadcasts de servidores...")

            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    message = data.decode('utf-8')
                    
                    if message.startswith("EUROPA_SCRAPER_SERVER"):
                        parts = message.split(';')
                        if len(parts) == 3:
                            _, server_ip, server_port = parts
                            server_address = f"{server_ip}:{server_port}"
                            # Usar la cola para actualizar la GUI desde el hilo principal
                            self.parent_app.queue.put(('add_server_to_listbox', server_address))
                except socket.timeout:
                    logger.info("Timeout esperando broadcasts de servidores.")
                    break  # Salir del bucle si no se reciben más respuestas
                except Exception as e:
                    logger.error(f"Error escuchando broadcasts: {e}")
                    break
        # After loop finishes (timeout or error), re-enable button and clear status
        self.parent_app.queue.put(('discovery_finished', None))

    def _show_context_menu(self, event):
        """Muestra un menú contextual en el Treeview."""
        selected_items = self.course_tree.selection()
        if not selected_items:
            return

        context_menu = tk.Menu(self, tearoff=0)
        context_menu.add_command(label="Forzar Reseteo de Estado", command=self._force_reset_status)
        context_menu.tk_popup(event.x_root, event.y_root)

    def _force_reset_status(self):
        selected_items = self.course_tree.selection()
        if not selected_items:
            return

        if not messagebox.askyesno("Confirmar Reseteo", "¿Está seguro de que desea resetear el estado de los registros seleccionados? Esta acción debe usarse únicamente si el servidor asignado ya no está procesando estas tareas."):
            return

        courses_to_reset = []
        for item_id in selected_items:
            values = self.course_tree.item(item_id, 'values')
            sic_code = values[1]
            course_name = values[2]
            courses_to_reset.append((sic_code, course_name))

        self.sqlite_handler.update_range_status(courses_to_reset, "pending", "")
        self._update_ui_status(selected_items, "pending", "")

    def _configure_firewall(self):
        if sys.platform != "win32":
            messagebox.showinfo("Información", "La configuración automática del firewall solo está disponible en Windows.")
            return

        response = messagebox.askyesno(
            "Configurar Firewall",
            "Esta acción intentará añadir reglas al Firewall de Windows para permitir la comunicación del servidor.\n"\
            "Se requerirán permisos de administrador y puede aparecer una ventana de Control de Cuentas de Usuario (UAC).\n\n"\
            "¿Desea continuar?"
        )
        if not response:
            return

        try:
            # Regla de entrada
            command_in = "netsh advfirewall firewall add rule name=\"Europa Scraper Server (UDP 6000) IN\" dir=in action=allow protocol=UDP localport=6000"
            # Regla de salida
            command_out = "netsh advfirewall firewall add rule name=\"Europa Scraper Server (UDP 6000) OUT\" dir=out action=allow protocol=UDP localport=6000"

            # Ejecutar comandos con subprocess
            # shell=True es necesario para netsh, pero es un riesgo de seguridad si el comando no es fijo.
            # Aquí es fijo, así que es aceptable.
            result_in = subprocess.run(command_in, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            result_out = subprocess.run(command_out, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)

            if result_in.returncode == 0 and result_out.returncode == 0:
                messagebox.showinfo("Éxito", "Reglas del Firewall añadidas correctamente para el puerto UDP 6000.")
                logger.info("Reglas del Firewall añadidas correctamente.")
            else:
                error_msg = f"Error al añadir reglas de entrada: {result_in.stderr}\nError al añadir reglas de salida: {result_out.stderr}"
                messagebox.showerror("Error", f"No se pudieron añadir todas las reglas del Firewall.\n\n{error_msg}")
                logger.error(f"Error al añadir reglas del Firewall: {error_msg}")

        except Exception as e:
            messagebox.showerror("Error Inesperado", f"Ocurrió un error inesperado al configurar el Firewall: {e}")
            logger.error(f"Error inesperado al configurar el Firewall: {e}")

    def _on_tree_selection_changed(self, event):
        selected_items = self.course_tree.selection()
        if not selected_items:
            self.control_frame.start_button.config(state=tk.NORMAL)
            return

        for item_id in selected_items:
            status = self.course_tree.item(item_id, 'values')[3]
            if status.lower() in ["procesando", "completado"]:
                self.control_frame.start_button.config(state=tk.DISABLED)
                return
        
        self.control_frame.start_button.config(state=tk.NORMAL)

    def _on_start_scraping(self):
        selected_items = self.course_tree.selection()
        if not selected_items:
            messagebox.showwarning("Entrada Faltante", "Por favor seleccione al menos un curso.")
            return

        selected_server_index = self.server_listbox.curselection()
        if not selected_server_index:
            # Fallback: usar la URL configurada por defecto
            server_address = self.parent_app.server_base_url
            if not server_address:
                messagebox.showwarning("Servidor no seleccionado", "No hay servidor configurado. Verifica server_config.json.")
                return
            logger.info(f"Ningún servidor seleccionado en listbox, usando URL configurada: {server_address}")
        else:
            server_address = self.server_listbox.get(selected_server_index[0])

        search_engine = self.search_engine_combo.get()
        site_domain = None

        # Si el motor de búsqueda requiere un dominio, obtenlo
        if search_engine in ["Google", "DuckDuckGo", "Common Crawl", "Common Crawl (Guiado por Google)", "Wayback Machine"]:
            site_domain = self.site_domain_entry.get().strip()
            logger.debug(f"DEBUG: site_domain from GUI entry: '{site_domain}'") # ADDED FOR DEBUGGING

        # Validar que el dominio no esté vacío si es requerido
        if search_engine in ["Google", "Common Crawl", "Common Crawl (Guiado por Google)"] and not site_domain:
            messagebox.showwarning("Entrada Faltante", f"Para buscar en {search_engine}, es obligatorio especificar un dominio.")
            return

        self.control_frame.start_button.config(state=tk.DISABLED)
        self.control_frame.stop_button.config(state=tk.NORMAL)

        from_values = self.course_tree.item(selected_items[0], 'values')
        to_values = self.course_tree.item(selected_items[-1], 'values')

        courses_to_update = [(self.course_tree.item(item_id, 'values')[1], self.course_tree.item(item_id, 'values')[2]) for item_id in selected_items]
        self.sqlite_handler.update_range_status(courses_to_update, "processing", server_address)
        self._update_ui_status(selected_items, "processing", server_address)

        params = {
            'from_sic': from_values[1],
            'to_sic': to_values[1],
            'from_course': from_values[2] if len(from_values) > 2 else '',
            'to_course': to_values[2] if len(to_values) > 2 else '',
            'min_words': self.config.get('min_words', 30),
            'search_engine': search_engine,
            'site_domain': site_domain,
            'is_headless': self.config.get("headless_mode", True)
        }

        self.timer_manager.start()
        self.parent_app.start_scraping_on_server(server_address, params)

    def _on_stop_scraping(self):
        self.parent_app.stop_scraping()

    def _update_ui_status(self, item_ids: List[str], status: str, server: str):
        tag = "normal"
        if status.lower() == "processing": tag = "processing"
        elif status.lower() == "completed": tag = "completed"

        for item_id in item_ids:
            values = list(self.course_tree.item(item_id, 'values'))
            values[3] = status
            values[4] = server
            self.course_tree.item(item_id, values=tuple(values), tags=(tag,))

    def handle_scraping_finished(self):
        self.timer_manager.stop()
        self.control_frame.start_button.config(state=tk.NORMAL)
        self.control_frame.stop_button.config(state=tk.DISABLED)
        self.progress_frame.update_progress(100, "Proceso completado.")

    def handle_scraping_stopped(self, message):
        self.timer_manager.stop()
        self.control_frame.start_button.config(state=tk.NORMAL)
        self.control_frame.stop_button.config(state=tk.DISABLED)
        self.progress_frame.update_progress(0, "Scraping detenido.")
        self.results_frame.add_log(f"[SERVER] {message}")

        server_address = self.parent_app.server_base_url.replace("http://", "")

        items_to_pend = [item_id for item_id in self.course_tree.get_children() if self.course_tree.item(item_id, 'values')[4] == server_address]
        if items_to_pend:
            courses_to_update = [(self.course_tree.item(item_id, 'values')[1], self.course_tree.item(item_id, 'values')[2]) for item_id in items_to_pend]
            self.sqlite_handler.update_range_status(courses_to_update, "pending", "")
            self._update_ui_status(items_to_pend, "pending", "")

    def show_manual_captcha_input(self, challenge_data: dict, submit_callback: callable):
        """
        Muestra una ventana para que el usuario resuelva un CAPTCHA manualmente.
        Soporta CAPTCHAs de imagen y reCAPTCHAs (mostrando HTML).

        Args:
            challenge_data: Diccionario con los detalles del desafío (id, type, data).
            submit_callback: Función a la que se llama con la solución.
        """
        if self.captcha_window_open:
            return  # Ya hay una ventana de captcha abierta
        
        self.captcha_window_open = True

        captcha_id = challenge_data.get("id")
        captcha_type = challenge_data.get("type")
        captcha_data = challenge_data.get("data")

        if not all([captcha_id, captcha_type, captcha_data]):
            logger.error(f"Datos de desafío de CAPTCHA inválidos: {challenge_data}")
            self.captcha_window_open = False
            return

        captcha_window = tk.Toplevel(self.master)
        captcha_window.title("Resolver CAPTCHA Manualmente")
        captcha_window.transient(self.master)
        captcha_window.grab_set()  # Captura todos los eventos de la aplicación

        def on_submit(solution):
            if solution:
                submit_callback(captcha_id, solution)
                self.captcha_window_open = False
                captcha_window.destroy()
            else:
                messagebox.showwarning("Solución Vacía", "La solución no puede estar vacía.", parent=captcha_window)

        if captcha_type == "image":
            self._setup_image_captcha_ui(captcha_window, captcha_data, on_submit)
        elif captcha_type == "recaptcha":
            self._setup_recaptcha_ui(captcha_window, captcha_data, on_submit)
        else:
            logger.error(f"Tipo de CAPTCHA desconocido: {captcha_type}")
            self.captcha_window_open = False
            captcha_window.destroy()
            return

        # Centrar y mostrar la ventana
        captcha_window.update_idletasks()
        width = captcha_window.winfo_reqwidth()
        height = captcha_window.winfo_reqheight()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (width // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (height // 2)
        captcha_window.geometry(f"{width}x{height}+{x}+{y}")

        # Manejar el cierre de la ventana (si el usuario la cierra sin enviar)
        def on_close():
            logger.warning(f"Ventana de CAPTCHA {captcha_id} cerrada por el usuario sin solución.")
            # No enviar solución, dejar que el servidor agote el tiempo de espera
            self.captcha_window_open = False
            captcha_window.destroy()

        captcha_window.protocol("WM_DELETE_WINDOW", on_close)

    def _setup_image_captcha_ui(self, window, image_base64, submit_callback):
        """Configura la UI para un CAPTCHA de imagen."""
        try:
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))
            photo = ImageTk.PhotoImage(image)
            
            ttk.Label(window, image=photo).pack(pady=10)
            window.image = photo  # Mantener referencia

            solution_var = tk.StringVar()
            entry = ttk.Entry(window, textvariable=solution_var, width=30)
            entry.pack(pady=5, padx=10)
            entry.focus_set()

            button = ttk.Button(window, text="Enviar", command=lambda: submit_callback(solution_var.get().strip()))
            button.pack(pady=10)

            entry.bind("<Return>", lambda e: button.invoke())

        except Exception as e:
            logger.error(f"Error al mostrar CAPTCHA de imagen: {e}")
            messagebox.showerror("Error de Imagen", f"No se pudo mostrar la imagen del CAPTCHA: {e}", parent=window)
            window.destroy()

    def _setup_recaptcha_ui(self, window, html_content, submit_callback):
        """Configura la UI para un reCAPTCHA usando un WebView."""
        try:
            # Importar tkwebview2 solo cuando sea necesario
            from tkwebview2.tkwebview2 import WebView2
            import webview

            window.geometry("600x700")

            # Frame para contener el WebView
            webview_frame = ttk.Frame(window)
            webview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Crear el control WebView2
            self.webview = WebView2(webview_frame, 580, 580)
            self.webview.pack(fill=tk.BOTH, expand=True)

            # Cargar el contenido HTML del CAPTCHA
            self.webview.load_html(html_content)

            # Frame para la entrada de la solución y el botón
            solution_frame = ttk.Frame(window)
            solution_frame.pack(fill=tk.X, padx=10, pady=10)

            ttk.Label(solution_frame, text="Token de reCAPTCHA (g-recaptcha-response):").pack(side=tk.LEFT, padx=(0, 5))
            
            solution_var = tk.StringVar()
            entry = ttk.Entry(solution_frame, textvariable=solution_var, width=40)
            entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
            entry.focus_set()

            button = ttk.Button(solution_frame, text="Enviar", command=lambda: submit_callback(solution_var.get().strip()))
            button.pack(side=tk.LEFT, padx=(5, 0))

            entry.bind("<Return>", lambda e: button.invoke())

            # Instrucciones para el usuario
            instructions = ttk.Label(window, 
                text="""1. Resuelva el reCAPTCHA en la ventana superior.
2. Haga clic derecho en la página y seleccione 'Inspeccionar'.
3. En la pestaña 'Elements' o 'Elementos', busque el div con id='g-recaptcha-response'.
4. Copie el contenido de ese elemento y péguelo en el campo de texto de abajo.""",
                justify=tk.LEFT)
            instructions.pack(fill=tk.X, padx=10, pady=5)

        except ImportError:
            logger.error("El paquete 'tk webview2' no está instalado. No se puede mostrar el reCAPTCHA.")
            messagebox.showerror("Dependencia Faltante", "Por favor, instale 'tk webview2' y 'pywebview' para resolver reCAPTCHAs.", parent=window)
            window.destroy()
        except Exception as e:
            logger.error(f"Error al mostrar reCAPTCHA: {e}")
            messagebox.showerror("Error de reCAPTCHA", f"No se pudo mostrar el reCAPTCHA: {e}", parent=window)
            window.destroy()
