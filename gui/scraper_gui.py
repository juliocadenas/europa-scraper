#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GUI Principal del Scraper
========================
Interfaz gráfica principal para el scraper de USA.gov
"""

import hashlib
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import sys
import os
import threading
import asyncio
import queue
import re
import subprocess
from datetime import datetime
import time
from pathlib import Path
import webbrowser
import socket
import requests
import json


# Añadir raíz del proyecto al path para permitir imports absolutos
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui.styles import setup_styles
from gui.timer_manager import TimerManager
from gui.components.gui_components import (
    ProgressFrame, ResultsFrame, ControlFrame
)
from gui.proxy_config import ProxyConfigWindow
from gui.captcha_config import CaptchaConfigWindow
from gui.config_tab import ConfigTab
from utils.logger import setup_logger, get_global_log_handler
from utils.text_sanitizer import sanitize_filename
from utils.proxy_manager import ProxyManager
from utils.config import Config

logger = logging.getLogger(__name__)



class ScraperGUI(ttk.Frame):
    """
    Interfaz gráfica principal para la aplicación de scraping de USA.gov.
    Adaptable a diferentes formatos de datos CSV.
    """

    def __init__(self, master, controller=None):
        """
        Inicializa la GUI del scraper.
        
        Args:
            master: Widget padre
            controller: Instancia del controlador de scraping
        """
        super().__init__(master)
        print("Inicializando ScraperGUI...")
        self.master = master
        self.controller = controller
        print(f"DEBUG: ScraperGUI.__init__, self.controller is {self.controller}")
        self.current_task_id = None
        print("ScraperGUI inicializado")
        
        self.proxy_manager = ProxyManager()
        config_path = os.path.join(project_root, 'client', 'config.json')
        self.config = Config(config_path)
        
        self.queue = queue.Queue()
        self.timer_manager = TimerManager(update_callback=self._update_timer_display)
        
        self.results = None
        self.current_course_info = ""
        self.is_updating = False
        
        setup_styles()
        self._setup_ui()
        
        # Confirmar que el botón de carga está visible
        print("✅ Botón 'CARGAR CURSOS (CSV/XLS)' agregado a la pestaña Principal")
        
        # Conectar al servidor y cargar datos iniciales
        self._connect_and_load_initial_data()
        
        global_log_handler = get_global_log_handler()
        global_log_handler.set_callback(self._log_callback)
        
        self.process_queue()
        self.master.bind("<Configure>", self._on_resize)
        self._show_existing_logs()

    def _show_existing_logs(self):
        """Muestra los logs existentes en el área de resultados."""
        try:
            global_log_handler = get_global_log_handler()
            existing_logs = global_log_handler.get_logs()
            
            if existing_logs and hasattr(self, 'results_frame'):
                for log in existing_logs:
                    self.results_frame.add_log(log)
        except Exception as e:
            logger.error(f"Error mostrando logs existentes: {e}")

    def _setup_ui(self):
        """Configura los componentes de la interfaz de usuario."""
        computer_name = socket.gethostname()
        self.master.title(f"Europa Scraper v3 (CON MONITOR) - {computer_name}")
        self.master.geometry("1200x700")
        self.master.minsize(1000, 600)
        self.master.configure(background="#f0f0f0")
        
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.main_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.main_frame, text="Principal")
        
        self._create_server_config_tab()
        # self._create_task_management_tab() # ELIMINADO
        # self._create_monitor_tab() # ELIMINADO
        
        self.config_tab = ConfigTab(self.notebook, self.config)

        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        self.left_column = ttk.Frame(self.paned_window)
        self.center_column = ttk.Frame(self.paned_window)
        self.right_column = ttk.Frame(self.paned_window)
        
        self.paned_window.add(self.left_column, weight=4)
        self.paned_window.add(self.center_column, weight=4)
        self.paned_window.add(self.right_column, weight=2)
        
        # --- COLUMNA IZQUIERDA ---
        self.sic_frame = ttk.LabelFrame(self.left_column, text="Selección de Código", padding=10)
        self.sic_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.labels_frame = ttk.Frame(self.sic_frame)
        self.labels_frame.pack(fill=tk.X, padx=0, pady=(5, 0))
        ttk.Label(self.labels_frame, text="Curso desde:", font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2.5))
        ttk.Label(self.labels_frame, text="Curso hasta:", font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2.5, 0))

        self.search_frame = ttk.Frame(self.sic_frame)
        self.search_frame.pack(fill=tk.X, padx=0, pady=5)
        self.search_from_entry = ttk.Entry(self.search_frame)
        self.search_from_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2.5))
        self.search_from_entry.bind("<KeyRelease>", self._on_search_from)
        self.search_to_entry = ttk.Entry(self.search_frame)
        self.search_to_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2.5, 0))
        self.search_to_entry.bind("<KeyRelease>", self._on_search_to)
        self.sic_listbox_frame = ttk.Frame(self.sic_frame)
        self.sic_listbox_frame.pack(fill=tk.BOTH, expand=True)
        self.from_sic_listbox = tk.Listbox(self.sic_listbox_frame, exportselection=False, font=("TkDefaultFont", 11)) # Fuente más grande
        self.from_sic_scrollbar = ttk.Scrollbar(self.sic_listbox_frame, orient=tk.VERTICAL, command=self.from_sic_listbox.yview)
        self.from_sic_listbox.configure(yscrollcommand=self.from_sic_scrollbar.set)
        self.from_sic_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.from_sic_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.from_sic_listbox.bind('<<ListboxSelect>>', self._on_from_sic_select)
        self.to_sic_listbox = tk.Listbox(self.sic_listbox_frame, exportselection=False, font=("TkDefaultFont", 11)) # Fuente más grande
        self.to_sic_scrollbar = ttk.Scrollbar(self.sic_listbox_frame, orient=tk.VERTICAL, command=self.to_sic_listbox.yview)
        self.to_sic_listbox.configure(yscrollcommand=self.to_sic_scrollbar.set)
        self.to_sic_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.to_sic_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.to_sic_listbox.bind('<<ListboxSelect>>', self._on_to_sic_select)

        # --- COLUMNA CENTRAL (AHORA MONITOR) ---
        self.header_frame = ttk.Frame(self.center_column)
        self.header_frame.pack(fill=tk.X, pady=(0, 20))
        self.title_label = ttk.Label(self.header_frame, text=f"Europa Scraper - {computer_name}", style="Heading.TLabel")
        self.title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.timer_label = ttk.Label(self.header_frame, text="Tiempo: 00:00:00", style="Timer.TLabel")
        self.timer_label.pack(side=tk.RIGHT, padx=10)
        
        # --- BOTÓN CARGAR CURSOS ---
        self.load_courses_button = ttk.Button(
            self.center_column,
            text="📁 CARGAR CURSOS (CSV/XLS)",
            command=self._upload_courses_file,
            style="Accent.TButton",
            width=50   # Hacer el botón más ancho
        )
        self.load_courses_button.pack(fill=tk.X, pady=10, ipadx=20, ipady=10)  # Más padding para hacerlo más visible
        
        # --- MONITOR DE TAREAS (REEMPLAZA TABLA DE CURSOS) ---
        self.monitor_frame = ttk.LabelFrame(self.center_column, text="Monitor de Progreso en Tiempo Real", padding=10)
        self.monitor_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Botones de control del monitor (Footer) - Se empaquetan PRIMERO con side=BOTTOM
        self.monitor_buttons_frame = ttk.Frame(self.monitor_frame)
        self.monitor_buttons_frame.pack(fill=tk.X, pady=5, side=tk.BOTTOM)
        
        self.details_button = ttk.Button(self.monitor_buttons_frame, text="Ver Detalles de Worker", command=self._show_worker_details)
        self.details_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True) # EXPANDIDO

        self.force_reset_button = ttk.Button(self.monitor_buttons_frame, text="Forzar Reinicio de Estado", command=self._force_reset_client_state)
        self.force_reset_button.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True) # EXPANDIDO
        
        # Treeview para mostrar el estado de los workers (Content)
        self.worker_tree = ttk.Treeview(self.monitor_frame, columns=('ID', 'Status', 'Task', 'Progress'), show='headings')
        self.worker_tree.heading('ID', text='Worker ID')
        self.worker_tree.heading('Status', text='Estado')
        self.worker_tree.heading('Task', text='Tarea Actual')
        self.worker_tree.heading('Progress', text='Progreso')

        self.worker_tree.column('ID', width=60, anchor=tk.CENTER)
        self.worker_tree.column('Status', width=100)
        self.worker_tree.column('Task', width=300) # Ajustado
        self.worker_tree.column('Progress', width=120)
        
        # Scrollbar para el monitor
        self.monitor_scrollbar = ttk.Scrollbar(self.monitor_frame, orient=tk.VERTICAL, command=self.worker_tree.yview)
        self.worker_tree.configure(yscrollcommand=self.monitor_scrollbar.set)
        
        self.monitor_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.worker_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configuración de motor y controles de inicio (se mantienen igual)
        self.engine_frame = ttk.Frame(self.center_column)
        self.engine_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.engine_frame, text="Motor de Búsqueda:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_engine_var = tk.StringVar()
        self.search_engine_combo = ttk.Combobox(self.engine_frame, textvariable=self.search_engine_var, values=["Cordis Europa", "Google", "DuckDuckGo", "Common Crawl", "Wayback Machine"], state="readonly")
        self.search_engine_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_engine_var.set(self.config.get("search_engine", "Cordis Europa"))
        self.control_frame = ControlFrame(self.center_column, on_start=self._on_start_scraping, on_stop=self._on_stop_scraping)
        self.control_frame.pack(fill=tk.X, pady=2)
        self.progress_frame = ProgressFrame(self.center_column)
        self.progress_frame.pack(fill=tk.X, pady=2)
        
        # --- COLUMNA DERECHA ---
        self.results_frame = ResultsFrame(self.right_column)
        self.results_frame.pack(fill=tk.BOTH, expand=True)
        self.results_buttons_frame = ttk.Frame(self.right_column)
        self.results_buttons_frame.pack(fill=tk.X, pady=5)
        self.export_button = ttk.Button(self.results_buttons_frame, text="Exportar Resultados (ZIP)", command=self._on_export_results, state=tk.NORMAL, style="TButton")
        self.export_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        self.open_folder_button = ttk.Button(self.results_buttons_frame, text="Abrir Carpeta de Resultados", command=self._on_open_results_folder, style="TButton")
        self.open_folder_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        self.paned_window.update()
        width = self.paned_window.winfo_width()
        if width > 0:
            sash_pos1 = int(width * 0.40)
            sash_pos2 = int(width * 0.80)
            self.paned_window.sashpos(0, sash_pos1)
            self.paned_window.sashpos(1, sash_pos2)

    def _create_server_config_tab(self):
        """Crea la pestaña de configuración del servidor"""
        self.server_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.server_frame, text="Configuración del Servidor")
        config_frame = ttk.LabelFrame(self.server_frame, text="Configuración", padding=10)
        config_frame.pack(fill=tk.X, pady=10)
        ttk.Label(config_frame, text="URL del Servidor:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.server_url = tk.StringVar(value="http://localhost:8002")
        self.server_url_entry = ttk.Entry(config_frame, textvariable=self.server_url, width=50)
        self.server_url_entry.grid(row=0, column=1, padx=10, pady=5, sticky=tk.EW)
        self.connect_button = ttk.Button(config_frame, text="Conectar", command=self._connect_to_server)
        self.connect_button.grid(row=2, column=1, padx=10, pady=20, sticky=tk.E)
        self.connection_status_label = ttk.Label(config_frame, text="Desconectado", foreground="red")
        self.connection_status_label.grid(row=3, column=1, padx=10, sticky=tk.E)
        config_frame.columnconfigure(1, weight=1)

    # _create_task_management_tab y _create_monitor_tab eliminados por refactorización de accesibilidad

    # _create_monitor_tab eliminado por refactorización de accesibilidad

    def _start_status_polling(self):
        """Este método ya no es necesario aquí, la ClientApp se encarga del polling."""
        pass # La ClientApp gestiona ahora el polling y llama a _render_worker_status

    def _render_worker_status(self, worker_states):
        """Recibe y renderiza el estado detallado de los trabajadores en la GUI."""
        # print(f"DEBUG GUI RENDER: Recibiendo del servidor: {worker_states}")
        
        # Iterar sobre los estados de worker recibidos y actualizar/insertar
        for worker_id, state in worker_states.items():
            worker_id_str = str(worker_id)
            current_task = state.get('current_task', 'N/A')
            
            # --- CORRECCIÓN CRÍTICA PARA EVITAR DUPLICADOS ---
            # El servidor envía actualizaciones con el progreso en el texto (ej: "... | Tabulados 90 de 100").
            # Si usamos todo el string como ID, cada actualización crea una fila nueva.
            # SOLUCIÓN: Usamos solo la parte "Estable" del texto (antes del caracter '|') como identificador.
            if '|' in current_task:
                stable_task_signature = current_task.split('|')[0].strip()
            else:
                stable_task_signature = current_task.strip()
            
            # Generar un ID único basado en el Worker ID Y la Firma Estable
            task_hash = hashlib.md5(f"{worker_id_str}_{stable_task_signature}".encode()).hexdigest()
            row_id = f"{worker_id_str}_{task_hash}"

            values = (
                worker_id_str,
                state.get('status', 'N/A').capitalize(),
                current_task, # Aquí SÍ mostramos el texto completo con el progreso dinámico
                f"{state.get('progress', 0):.2f}%"
            )

            if self.worker_tree.exists(row_id):
                # Actualizar item existente (misma tarea, nuevo progreso)
                self.worker_tree.item(row_id, values=values)
            else:
                # Insertar nuevo item (nueva tarea real)
                self.worker_tree.insert("", tk.END, iid=row_id, values=values)
                # Auto-scroll al final para ver lo nuevo
                self.worker_tree.yview_moveto(1)
            
        # NOTA: Hemos eliminado el bucle de "limpieza" que borraba filas antiguas (History Log).
        
        self.current_worker_states = worker_states # Actualizar el estado interno de la GUI

        # Calcular progreso general promedio
        if worker_states:
            total_progress = sum(state.get('progress', 0) for state in worker_states.values())
            avg_progress = total_progress / len(worker_states)
            self.progress_frame.update_progress(avg_progress, f"Progreso General: {avg_progress:.1f}%")
        else:
            self.progress_frame.update_progress(0, "Esperando inicio...")

    def _upload_courses_file(self):
        """Abre el diálogo para seleccionar un archivo y lo sube al servidor."""
        print("DEBUG GUI: _upload_courses_file llamada")
        if self.connection_status_label.cget("text") != "Conectado":
            print("DEBUG GUI: No conectado")
            messagebox.showerror("No Conectado", "Por favor, conéctese a un servidor primero.")
            return

        filepath = filedialog.askopenfilename(
            title="Seleccione un archivo de cursos",
            filetypes=[("Archivos Excel", "*.xlsx"), ("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        print(f"DEBUG GUI: Archivo seleccionado: {filepath}")
        if not filepath:
            print("DEBUG GUI: Selección cancelada")
            return

        server_url = self.server_url.get().rstrip('/')
        print(f"DEBUG GUI: URL del servidor: {server_url}")
        self.results_frame.add_log(f"Subiendo archivo {os.path.basename(filepath)} al servidor...")

        try:
            print("DEBUG GUI: Iniciando request POST...")
            with open(filepath, 'rb') as f:
                files = {'file': (os.path.basename(filepath), f)}
                response = requests.post(f"{server_url}/upload_courses", files=files, timeout=30)
            
            print(f"DEBUG GUI: Respuesta recibida. Status: {response.status_code}")
            print(f"DEBUG GUI: Body: {response.text}")

            if response.status_code == 200:
                message = response.json().get("message", "Carga exitosa.")
                messagebox.showinfo("Éxito", message)
                self.results_frame.add_log(message)
                # Refrescar la lista de cursos en la GUI
                self._refresh_courses_from_server()
            else:
                error_detail = response.json().get("detail", response.text)
                messagebox.showerror("Error de Subida", f"El servidor devolvió un error:\n{error_detail}")
                self.results_frame.add_log(f"Error en la subida: {error_detail}")

        except requests.exceptions.RequestException as e:
            print(f"DEBUG GUI: Excepción de request: {e}")
            messagebox.showerror("Error de Red", f"No se pudo comunicar con el servidor: {e}")
            self.results_frame.add_log(f"Error de red: {e}")
        except Exception as e:
            print(f"DEBUG GUI: Excepción general: {e}")
            messagebox.showerror("Error Inesperado", f"Ocurrió un error: {e}")
            self.results_frame.add_log(f"Error inesperado: {e}")

    def _refresh_courses_from_server(self):
        """Obtiene la lista de cursos del servidor y refresca la UI."""
        if self.connection_status_label.cget("text") != "Conectado":
            messagebox.showerror("No Conectado", "Por favor, conéctese a un servidor para refrescar los cursos.")
            return

        server_url = self.server_url.get().rstrip('/')
        self.results_frame.add_log("Refrescando lista de cursos desde el servidor...")

        try:
            response = requests.get(f"{server_url}/get_all_courses", timeout=10)
            if response.status_code == 200:
                courses_data = response.json()
                self._populate_ui_with_course_data(courses_data)
                self.results_frame.add_log(f"Lista de cursos actualizada. {len(courses_data)} cursos cargados.")
            else:
                error_detail = response.json().get("detail", response.text)
                messagebox.showerror("Error de Servidor", f"No se pudo obtener la lista de cursos:\n{error_detail}")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error de Red", f"No se pudo comunicar con el servidor: {e}")

    def _populate_ui_with_course_data(self, courses_data):
        """Puebla los widgets de la UI con la lista de cursos."""
        try:
            self.detailed_sic_codes_with_courses = courses_data
            logger.info(f"Cargados {len(self.detailed_sic_codes_with_courses)} cursos para la tabla")

            if not self.detailed_sic_codes_with_courses:
                logger.warning("El servidor no devolvió cursos.")
                messagebox.showwarning("Advertencia", "No se encontraron cursos en el servidor.")
                return
          
            # Limpiar widgets antes de cargar nuevos datos
            # self.course_tree.delete(*self.course_tree.get_children()) # ELIMINADO
            self.from_sic_listbox.delete(0, tk.END)
            self.to_sic_listbox.delete(0, tk.END)

            # Poblar la tabla (Treeview) y los Listbox
            for item in self.detailed_sic_codes_with_courses:
                # Manejar tanto diccionarios (nuevo formato) como tuplas (viejo formato local)
                if isinstance(item, dict):
                    sic_code = item.get('sic_code', '')
                    course_name = item.get('course_name', '')
                else:
                    sic_code = item[0]
                    course_name = item[1]
                
                # self.course_tree.insert("", tk.END, values=(sic_code, course_name)) # ELIMINADO
                display_text = f"{sic_code} - {course_name}"
                self.from_sic_listbox.insert(tk.END, display_text)
                self.to_sic_listbox.insert(tk.END, display_text)
          
            logger.info("Datos cargados exitosamente en la tabla y listboxes")
          
        except Exception as e:
            logger.error(f"Error poblando la UI con datos: {str(e)}")
            messagebox.showerror("Error", f"Error mostrando los datos: {str(e)}")

    def _connect_and_load_initial_data(self):
        """Intenta conectar y cargar datos al inicio."""
        self._connect_to_server(show_popups=False)
    
    def _assign_task_to_server(self):
        """Asigna una tarea de scraping al servidor conectado."""
        if self.connection_status_label.cget("text") != "Conectado":
            messagebox.showerror("No Conectado", "Por favor, conéctese a un servidor primero.")
            return

        from_sic = self.from_sic_entry_task.get()
        to_sic = self.to_sic_entry_task.get()

        if not from_sic or not to_sic:
            messagebox.showwarning("Rango no especificado", "Por favor, ingrese los códigos SIC de inicio y fin del trabajo.")
            return

        logger.info(f"Asignando trabajo al servidor: Rango SIC de {from_sic} a {to_sic}")

        try:
            server_url = self.server_url.get().rstrip('/')

            scraping_job_config = {
                'from_sic': from_sic,
                'to_sic': to_sic,
                'min_words': self.config.get('min_words', 30),
                'search_engine': self.search_engine_var.get()
            }

            response = requests.post(f"{server_url}/start_scraping", json=scraping_job_config, timeout=10)

            if response.status_code == 202:
                result = response.json()
                message = result.get('message', 'Trabajo asignado.')
                messagebox.showinfo("Trabajo Asignado", message)
                logger.info(message)
                self.notebook.select(self.monitor_frame) # Cambiar a la pestaña de monitor
            else:
                error_detail = response.json().get("detail", response.text)
                messagebox.showerror("Error de Comunicación", f"Error al asignar trabajo: {error_detail}")

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error de Red", f"No se pudo conectar con el servidor: {e}")
        except Exception as e:
            messagebox.showerror("Error Inesperado", f"Ocurrió un error inesperado: {e}")


    def _connect_to_server(self, show_popups=True):
        """Conecta al servidor y refresca los datos."""
        try:
            server_url = self.server_url.get().rstrip('/')
            response = requests.get(f"{server_url}/", timeout=5)
            
            if response.status_code == 200:
                self.connection_status_label.config(text="Conectado", foreground="green")
                self.connect_button.config(text="Desconectar", command=self._disconnect_from_server)
                if show_popups:
                    messagebox.showinfo("Conexión Exitosa", "Conectado al servidor correctamente")
                logger.info(f"Conectado al servidor: {server_url}")
                # Cargar datos después de conectar
                self._refresh_courses_from_server()
            else:
                raise Exception(f"Error de conexión: {response.status_code}")
                
        except Exception as e:
            self.connection_status_label.config(text="Desconectado", foreground="red")
            self.connect_button.config(text="Conectar", command=self._connect_to_server)
            if show_popups:
                messagebox.showerror("Error de Conexión", f"No se pudo conectar al servidor:\n{str(e)}")
            logger.error(f"Error conectando al servidor: {str(e)}")

    def _disconnect_from_server(self):
        """Desconecta del servidor"""
        self.connection_status_label.config(text="Desconectado", foreground="red")
        self.connect_button.config(text="Conectar", command=self._connect_to_server)
        messagebox.showinfo("Desconexión", "Desconectado del servidor")
        logger.info("Desconectado del servidor")

    # --- Métodos de Ayuda y Callbacks (sin cambios significativos) ---
    
    def _on_resize(self, event):
        if not self.is_updating:
            self.is_updating = True
            self.is_updating = False

    def _on_from_sic_select(self, event):
        selection = self.from_sic_listbox.curselection()
        if selection:
            selected_text = self.from_sic_listbox.get(selection[0])
            sic_code = selected_text.split(' - ')[0]
            # Actualizar solo si es necesario, por ahora no hay entry que actualizar
            pass

    def _on_to_sic_select(self, event):
        selection = self.to_sic_listbox.curselection()
        if selection:
            selected_text = self.to_sic_listbox.get(selection[0])
            sic_code = selected_text.split(' - ')[0]
            # Actualizar solo si es necesario, por ahora no hay entry que actualizar
            pass

    def _on_search_from(self, event):
        search_term = self.search_from_entry.get().lower()
        self.from_sic_listbox.delete(0, tk.END)
        # Verificar si hay cursos cargados antes de intentar buscar
        if hasattr(self, 'detailed_sic_codes_with_courses') and self.detailed_sic_codes_with_courses:
            for sic_code, course_name in self.detailed_sic_codes_with_courses:
                display_text = f"{sic_code} - {course_name}"
                if search_term in display_text.lower():
                    self.from_sic_listbox.insert(tk.END, display_text)

    def _on_search_to(self, event):
        search_term = self.search_to_entry.get().lower()
        self.to_sic_listbox.delete(0, tk.END)
        # Verificar si hay cursos cargados antes de intentar buscar
        if hasattr(self, 'detailed_sic_codes_with_courses') and self.detailed_sic_codes_with_courses:
            for sic_code, course_name in self.detailed_sic_codes_with_courses:
                display_text = f"{sic_code} - {course_name}"
                if search_term in display_text.lower():
                    self.to_sic_listbox.insert(tk.END, display_text)

    def _update_timer_display(self, time_str):
        self.queue.put(('update_timer', time_str))

    def _on_start_scraping(self):
        """Maneja el clic del botón de inicio de scraping desde la pestaña Principal."""
        # Obtener configuración de todas las pestañas
        try:

            # PRIORIDAD ÚNICA: Usar listas laterales (Accesibilidad)
            from_selection = self.from_sic_listbox.curselection()
            to_selection = self.to_sic_listbox.curselection()
            
            if not from_selection or not to_selection:
                # Si no hay selección, usar cursos cargados o valores por defecto
                if hasattr(self, 'detailed_sic_codes_with_courses') and self.detailed_sic_codes_with_courses:
                    from_sic = self.detailed_sic_codes_with_courses[0][0]  # Primer código
                    to_sic = self.detailed_sic_codes_with_courses[-1][0]  # Último código
                    print(f"🔍 DEPURACIÓN: Usando cursos cargados desde archivo - from_sic='{from_sic}', to_sic='{to_sic}'")
                else:
                    # Último recurso - valores por defecto
                    from_sic = "01.0"
                    to_sic = "011903.0"
                    print(f"🔍 DEPURACIÓN: Usando valores por defecto - from_sic='{from_sic}', to_sic='{to_sic}'")
                    messagebox.showinfo("Selección Automática", f"No se encontraron cursos cargados. Usando rango por defecto:\nDesde: {from_sic}\nHasta: {to_sic}")
            else:
                # Extraer códigos SIC de las listas laterales
                from_sic = self.from_sic_listbox.get(from_selection[0]).split(' - ')[0]
                to_sic = self.to_sic_listbox.get(to_selection[0]).split(' - ')[0]
                
                # DEPURACIÓN: Mostrar los valores extraídos
                print(f"🔍 DEPURACIÓN: from_sic='{from_sic}', to_sic='{to_sic}'")
            
            # Obtener configuración de la pestaña de configuración
            scraping_config = {
                'query': f"{from_sic} a {to_sic}",  # Para compatibilidad con el servidor
                'job_params': {
                    'from_sic': from_sic,
                    'to_sic': to_sic,
                    'min_words': self.config.get('min_words', 30),
                    'num_workers': int(self.config.get('num_workers', 4)), # Enviar número de workers
                    'search_engine': self.search_engine_var.get(),
                    'proxy_enabled': self.config.get('proxy_enabled', False),
                    'proxy_rotation': self.config.get('proxy_rotation', False),
                    'captcha_solving_enabled': self.config.get('captcha_solving_enabled', False),
                    'captcha_service': self.config.get('captcha_service', 'manual'),
                    'request_delay': self.config.get('request_delay', 1.0),
                    'page_timeout': self.config.get('page_timeout', 30),
                    'output_format': self.config.get('output_format', 'CSV'),
                    'headless_mode': self.config.get('headless_mode', True)
                }
            }
            
            # Enviar tarea al servidor
            print(f"🔍 DEPURACIÓN FINAL: Enviando configuración: {scraping_config}")
            self._send_scraping_task_to_server(scraping_config)
            
        except Exception as e:
            error_msg = f"Error al iniciar el scraping: {str(e)}"
            messagebox.showerror("Error", error_msg)
            logger.error(f"Error iniciando scraping desde Principal: {str(e)}")
            print(f"❌ ERROR FINAL: {error_msg}")
            # Mostrar el error exacto para depuración
            print(f"❌ ERROR DETALLADO: {error_msg}")
            print(f"🔍 CONFIGURACIÓN ENVIADA: {scraping_config}")
    
    def _send_scraping_task_to_server(self, config):
        """Envía la tarea de scraping al controlador principal (ClientApp)."""
        print(f"DEBUG: _send_scraping_task_to_server, self.controller is {self.controller}")
        if self.connection_status_label.cget("text") != "Conectado":
            messagebox.showerror("No Conectado", "Por favor, conéctese al servidor primero desde la pestaña 'Configuración del Servidor'.")
            return
        
        if not self.controller:
            messagebox.showerror("Error de Arquitectura", "El controlador del cliente no está disponible. La GUI no puede enviar tareas.")
            logger.error("Se intentó enviar una tarea pero self.controller es None.")
            return

        server_url_with_http = self.server_url.get().rstrip('/')
        # El controlador espera la dirección en formato 'host:port' o similar, no la URL completa.
        server_address = server_url_with_http.replace("http://", "").replace("https://", "")
        
        job_params = config.get('job_params', {})
        
        # El controlador se encargará de la lógica de 'is_scraping', logging y el hilo.
        # Ya no se maneja aquí.
        self.controller.start_scraping_on_server(server_address, job_params)
        
        # Cambiamos a la pestaña de monitor para ver el progreso que reportará el controlador.
        # self.notebook.select(self.monitor_frame) # ELIMINADO: Ya está en la pantalla principal

    def _on_stop_scraping(self):
        """Maneja el clic del botón de detención de scraping."""
        server_url = self.server_url.get().rstrip('/')
        try:
            requests.post(f"{server_url}/stop_scraping", timeout=5)
            messagebox.showinfo("Detención Solicitada", "Se ha enviado una solicitud para detener el trabajo al servidor.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error de Red", f"No se pudo enviar la solicitud de detención: {e}")

    def _show_worker_details(self):
        """Muestra una ventana con los detalles de la tarea de un worker seleccionado."""
        selected_item = self.worker_tree.focus() # Obtiene el ID del item seleccionado
        if not selected_item:
            messagebox.showwarning("Selección", "Por favor, seleccione un worker de la lista para ver sus detalles.")
            return

        worker_id = selected_item # 'selected_item' es directamente el iid del item del treeview
        
        if not hasattr(self, 'current_worker_states') or worker_id not in self.current_worker_states:
            messagebox.showerror("Error", f"No se encontraron detalles para el worker ID: {worker_id}")
            return

        details = self.current_worker_states[worker_id]

        detail_window = tk.Toplevel(self.master)
        detail_window.title(f"Detalles del Worker {worker_id}")
        detail_window.transient(self.master) # Hace que la ventana de detalles sea hija de la principal
        detail_window.grab_set() # Captura todos los eventos hasta que se cierre

        ttk.Label(detail_window, text=f"Worker ID: {worker_id}", font=("TkDefaultFont", 10, "bold")).pack(pady=5)
        ttk.Label(detail_window, text=f"Estado: {details.get('status', 'N/A').capitalize()}").pack()
        ttk.Label(detail_window, text=f"Tarea Actual: {details.get('current_task', 'N/A')}").pack()
        ttk.Label(detail_window, text=f"Progreso: {details.get('progress', 0):.2f}%").pack()
        ttk.Label(detail_window, text=f"--- Estadísticas Finales ---", font=("TkDefaultFont", 9, "bold")).pack(pady=5)
        ttk.Label(detail_window, text=f"Procesados: {details.get('processed_count', 0)}").pack()
        ttk.Label(detail_window, text=f"Omitidos: {details.get('omitted_count', 0)}").pack()
        ttk.Label(detail_window, text=f"Errores: {details.get('error_count', 0)}").pack()
        
        ttk.Button(detail_window, text="Cerrar", command=detail_window.destroy).pack(pady=10)

        # Centrar la ventana
        detail_window.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (detail_window.winfo_width() // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (detail_window.winfo_height() // 2)
        detail_window.geometry(f"+{x}+{y}")

    def _force_reset_client_state(self):
        """Llama al controlador para forzar el reseteo del estado del cliente."""
        if messagebox.askyesno("Confirmar", "¿Está seguro de que desea forzar el reinicio del estado del cliente? Esto debería usarse solo si el cliente se ha quedado atascado en el estado 'en progreso'."):
            if self.controller:
                self.controller.force_reset_state()
            else:
                messagebox.showerror("Error", "El controlador no está disponible para reiniciar el estado.")

    def handle_scraping_finished(self):
        """Maneja el evento de finalización de scraping, actualizando la GUI."""
        self.timer_manager.stop()
        self.control_frame.start_button.config(state=tk.NORMAL)
        self.control_frame.stop_button.config(state=tk.DISABLED)
        self.progress_frame.update_progress(100, "Proceso completado.")

    def _on_export_results(self):
        """Descarga los resultados en un archivo ZIP desde el servidor."""
        if self.connection_status_label.cget("text") != "Conectado":
            messagebox.showerror("No Conectado", "Por favor, conéctese al servidor primero.")
            return

        server_url = self.server_url.get().rstrip('/')
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("Archivos ZIP", "*.zip"), ("Todos los archivos", "*.*")],
            title="Guardar Resultados (ZIP)"
        )
        
        if not filepath:
            return

        self.results_frame.add_log(f"Descargando resultados a: {filepath}...")
        
        try:
            # Petición GET al endpoint de descarga. Usar stream=True para descargas grandes.
            with requests.get(f"{server_url}/download_results", stream=True, timeout=120) as r:
                if r.status_code == 200:
                    with open(filepath, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    messagebox.showinfo("Descarga Exitosa", f"Archivo guardado correctamente en:\n{filepath}")
                    self.results_frame.add_log(f"✅ Descarga completada: {filepath}")
                elif r.status_code == 404:
                     messagebox.showwarning("Sin Resultados", "El servidor indica que no hay resultados para descargar.")
                     self.results_frame.add_log("⚠️ El servidor no tiene resultados.")
                else:
                    error_detail = r.json().get("detail", r.text) if r.headers.get('content-type') == 'application/json' else r.text
                    messagebox.showerror("Error de Descarga", f"El servidor devolvió un error:\n{error_detail}")
                    self.results_frame.add_log(f"❌ Error en la descarga: {error_detail}")

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error de Red", f"No se pudo descargar el archivo: {e}")
            self.results_frame.add_log(f"❌ Error de red durante descarga: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error inesperado: {e}")
            self.results_frame.add_log(f"❌ Error inesperado: {e}")


    def _on_open_results_folder(self):
        results_dir = os.path.abspath("results")
        if not os.path.exists(results_dir):
            os.makedirs(results_dir, exist_ok=True)
        try:
            if os.name == 'nt': os.startfile(results_dir)
            elif os.name == 'posix': subprocess.run(['xdg-open', results_dir])
        except Exception as e:
            logger.error(f"Error abriendo carpeta de resultados: {str(e)}")

    def _load_courses_from_file(self):
        """Carga cursos desde un archivo CSV o XLS con 2 columnas"""
        try:
            filepath = filedialog.askopenfilename(
                title="Seleccionar archivo de cursos",
                filetypes=[
                    ("Archivos Excel", "*.xlsx *.xls"),
                    ("Archivos CSV", "*.csv"),
                    ("Todos los archivos", "*.*")
                ]
            )
            
            if not filepath:
                return
            
            self.results_frame.add_log(f"Cargando cursos desde: {os.path.basename(filepath)}")
            
            # Procesar según el tipo de archivo
            if filepath.endswith(('.xlsx', '.xls')):
                import pandas as pd
                df = pd.read_excel(filepath, header=None)
                courses_data = [(str(row[0]), str(row[1])) for index, row in df.iterrows() if pd.notna(row[0]) and pd.notna(row[1])]
            else:
                # CSV
                import csv
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    courses_data = [(str(row[0]), str(row[1])) for row in reader if len(row) >= 2 and row[0] and row[1]]
            
            if not courses_data:
                messagebox.showwarning("Archivo Vacío", "No se encontraron cursos válidos en el archivo.")
                return
            
            # Actualizar la interfaz con los nuevos cursos
            self._update_ui_with_loaded_courses(courses_data)
            
            self.results_frame.add_log(f"✅ Cargados {len(courses_data)} cursos exitosamente")
            messagebox.showinfo("Éxito", f"Se cargaron {len(courses_data)} cursos desde el archivo.")
            
        except ImportError as e:
            if 'pandas' in str(e):
                messagebox.showerror("Error", "Para archivos Excel necesita instalar pandas:\npip install pandas openpyxl")
            else:
                messagebox.showerror("Error", f"Falta una librería: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar el archivo: {str(e)}")
            self.results_frame.add_log(f"❌ Error cargando archivo: {str(e)}")
    
    def _update_ui_with_loaded_courses(self, courses_data):
        """Actualiza la UI con los cursos cargados desde archivo"""
        try:
            # Limpiar widgets existentes
            self.course_tree.delete(*self.course_tree.get_children())
            self.from_sic_listbox.delete(0, tk.END)
            self.to_sic_listbox.delete(0, tk.END)
            
            # Guardar datos para búsquedas
            self.detailed_sic_codes_with_courses = courses_data
            
            # Poblar la tabla y listas
            for sic_code, course_name in courses_data:
                self.course_tree.insert("", tk.END, values=(sic_code, course_name))
                display_text = f"{sic_code} - {course_name}"
                self.from_sic_listbox.insert(tk.END, display_text)
                self.to_sic_listbox.insert(tk.END, display_text)
            
            logger.info(f"UI actualizada con {len(courses_data)} cursos desde archivo")
            
        except Exception as e:
            logger.error(f"Error actualizando UI con cursos cargados: {e}")
            messagebox.showerror("Error", f"Error actualizando la interfaz: {str(e)}")

    def _log_callback(self, log_entry):
        self.queue.put(('log', log_entry))

    def process_queue(self):
        try:
            while not self.queue.empty():
                message_type, message = self.queue.get_nowait()
                if message_type == 'update_timer':
                    if hasattr(self, 'timer_label'): self.timer_label.config(text=message)
                elif message_type == 'log':
                    if hasattr(self, 'results_frame'): self.results_frame.add_log(message)
        except queue.Empty:
            pass
        finally:
            self.master.after(200, self.process_queue)

if __name__ == "__main__":
    # Este bloque ahora asegura que la aplicación se inicie correctamente,
    # incluso si este script se ejecuta directamente.
    try:
        # Importar aquí para evitar dependencias circulares en el ámbito global
        from client.main import ClientApp
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        app = ClientApp()
        app.run()
    except Exception as e:
        try:
            messagebox.showerror("Error Crítico", f"Error al iniciar la aplicación:\n{str(e)}")
        except:
            print(f"Error crítico: {e}")
