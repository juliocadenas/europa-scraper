#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GUI Principal del Scraper
========================
Interfaz gráfica principal para el scraper de USA.gov
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
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
        self.controller = None # En modo cliente/servidor, siempre es None
        self.current_task_id = None
        print("ScraperGUI inicializado")
        
        self.proxy_manager = ProxyManager()
        self.config = Config()
        
        self.queue = queue.Queue()
        self.timer_manager = TimerManager(update_callback=self._update_timer_display)
        
        self.results = None
        self.current_course_info = ""
        self.is_updating = False
        
        setup_styles()
        self._setup_ui()
        
        # Conectar al servidor y cargar datos iniciales
        self._connect_and_load_initial_data()
        
        global_log_handler = get_global_log_handler()
        global_log_handler.set_callback(self._log_callback)
        
        self.process_queue()
        self.master.bind("<Configure>", self._on_resize)
        self._show_existing_logs()
        self._start_status_polling()

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
        self.master.title(f"Europa Scraper - {computer_name}")
        self.master.geometry("1200x700")
        self.master.minsize(1000, 600)
        self.master.configure(background="#f0f0f0")
        
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.main_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.main_frame, text="Principal")
        
        self._create_server_config_tab()
        self._create_task_management_tab() # Anteriormente 'Programar Rangos'
        self._create_monitor_tab() # Nueva pestaña de monitorización
        
        self.config_tab = ConfigTab(self.notebook, self.config)

        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        self.left_column = ttk.Frame(self.paned_window)
        self.center_column = ttk.Frame(self.paned_window)
        self.right_column = ttk.Frame(self.paned_window)
        
        self.paned_window.add(self.left_column, weight=2)
        self.paned_window.add(self.center_column, weight=6)
        self.paned_window.add(self.right_column, weight=2)
        
        # --- COLUMNA IZQUIERDA ---
        self.sic_frame = ttk.LabelFrame(self.left_column, text="Selección de Código", padding=10)
        self.sic_frame.pack(fill=tk.BOTH, expand=True, pady=10)
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
        self.from_sic_listbox = tk.Listbox(self.sic_listbox_frame, exportselection=False)
        self.from_sic_scrollbar = ttk.Scrollbar(self.sic_listbox_frame, orient=tk.VERTICAL, command=self.from_sic_listbox.yview)
        self.from_sic_listbox.configure(yscrollcommand=self.from_sic_scrollbar.set)
        self.from_sic_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.from_sic_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.from_sic_listbox.bind('<<ListboxSelect>>', self._on_from_sic_select)
        self.to_sic_listbox = tk.Listbox(self.sic_listbox_frame, exportselection=False)
        self.to_sic_scrollbar = ttk.Scrollbar(self.sic_listbox_frame, orient=tk.VERTICAL, command=self.to_sic_listbox.yview)
        self.to_sic_listbox.configure(yscrollcommand=self.to_sic_scrollbar.set)
        self.to_sic_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.to_sic_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.to_sic_listbox.bind('<<ListboxSelect>>', self._on_to_sic_select)

        # --- COLUMNA CENTRAL ---
        self.header_frame = ttk.Frame(self.center_column)
        self.header_frame.pack(fill=tk.X, pady=(0, 20))
        self.title_label = ttk.Label(self.header_frame, text=f"Europa Scraper - {computer_name}", style="Heading.TLabel")
        self.title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.timer_label = ttk.Label(self.header_frame, text="Tiempo: 00:00:00", style="Timer.TLabel")
        self.timer_label.pack(side=tk.RIGHT, padx=10)
        self.course_tree_frame = ttk.LabelFrame(self.center_column, text="Cursos Disponibles", padding=10)
        self.course_tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.course_tree = ttk.Treeview(self.course_tree_frame, columns=("sic_code", "course_name"), show="headings")
        self.course_tree.heading("sic_code", text="Código")
        self.course_tree.heading("course_name", text="Nombre del Curso")
        self.course_tree.column("sic_code", width=100, anchor=tk.W)
        self.course_tree.column("course_name", width=300, anchor=tk.W)
        self.course_tree_scrollbar = ttk.Scrollbar(self.course_tree_frame, orient=tk.VERTICAL, command=self.course_tree.yview)
        self.course_tree.configure(yscrollcommand=self.course_tree_scrollbar.set)
        self.course_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.course_tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.engine_frame = ttk.Frame(self.center_column)
        self.engine_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.engine_frame, text="Motor de Búsqueda:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_engine_var = tk.StringVar()
        self.search_engine_combo = ttk.Combobox(self.engine_frame, textvariable=self.search_engine_var, values=["Google", "DuckDuckGo", "Cordis Europa", "Common Crawl", "Wayback Machine"], state="readonly")
        self.search_engine_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_engine_var.set(self.config.get("search_engine", "DuckDuckGo"))
        self.control_frame = ControlFrame(self.center_column, on_start=self._on_start_scraping, on_stop=self._on_stop_scraping)
        self.control_frame.pack(fill=tk.X, pady=2)
        self.progress_frame = ProgressFrame(self.center_column)
        self.progress_frame.pack(fill=tk.X, pady=2)
        
        # --- COLUMNA DERECHA ---
        self.results_frame = ResultsFrame(self.right_column)
        self.results_frame.pack(fill=tk.BOTH, expand=True)
        self.results_buttons_frame = ttk.Frame(self.right_column)
        self.results_buttons_frame.pack(fill=tk.X, pady=5)
        self.export_button = ttk.Button(self.results_buttons_frame, text="Exportar Resultados", command=self._on_export_results, state=tk.DISABLED, style="TButton")
        self.export_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        self.open_folder_button = ttk.Button(self.results_buttons_frame, text="Abrir Carpeta de Resultados", command=self._on_open_results_folder, style="TButton")
        self.open_folder_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        self.paned_window.update()
        width = self.paned_window.winfo_width()
        if width > 0:
            sash_pos1 = int(width * 0.2)
            sash_pos2 = int(width * 0.8)
            self.paned_window.sash_place(0, sash_pos1, 0)
            self.paned_window.sash_place(1, sash_pos2, 0)

    def _create_server_config_tab(self):
        """Crea la pestaña de configuración del servidor"""
        self.server_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.server_frame, text="Configuración del Servidor")
        config_frame = ttk.LabelFrame(self.server_frame, text="Configuración", padding=10)
        config_frame.pack(fill=tk.X, pady=10)
        ttk.Label(config_frame, text="URL del Servidor:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.server_url = tk.StringVar(value="http://localhost:8001")
        self.server_url_entry = ttk.Entry(config_frame, textvariable=self.server_url, width=50)
        self.server_url_entry.grid(row=0, column=1, padx=10, pady=5, sticky=tk.EW)
        self.connect_button = ttk.Button(config_frame, text="Conectar", command=self._connect_to_server)
        self.connect_button.grid(row=2, column=1, padx=10, pady=20, sticky=tk.E)
        self.connection_status_label = ttk.Label(config_frame, text="Desconectado", foreground="red")
        self.connection_status_label.grid(row=3, column=1, padx=10, sticky=tk.E)
        config_frame.columnconfigure(1, weight=1)

    def _create_task_management_tab(self):
        """Crea la pestaña de gestión de tareas y datos."""
        self.task_management_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.task_management_frame, text="Gestión de Tareas")

        # --- Frame para carga de datos ---
        data_load_frame = ttk.LabelFrame(self.task_management_frame, text="Gestión de Datos de Cursos", padding="10")
        data_load_frame.pack(fill=tk.X, pady=10, padx=5)

        self.upload_button = ttk.Button(data_load_frame, text="Cargar Cursos desde Archivo (CSV/Excel)...", command=self._upload_courses_file)
        self.upload_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.refresh_courses_button = ttk.Button(data_load_frame, text="Refrescar Lista de Cursos", command=self._refresh_courses_from_server)
        self.refresh_courses_button.pack(side=tk.LEFT, padx=5, pady=5)

        # --- Frame para asignación de rangos ---
        range_assignment_frame = ttk.LabelFrame(self.task_management_frame, text="Asignar Nuevo Trabajo de Scraping", padding="10")
        range_assignment_frame.pack(fill=tk.X, pady=10, padx=5)

        ttk.Label(range_assignment_frame, text="Desde SIC:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.from_sic_entry_task = ttk.Entry(range_assignment_frame)
        self.from_sic_entry_task.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        ttk.Label(range_assignment_frame, text="Hasta SIC:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.to_sic_entry_task = ttk.Entry(range_assignment_frame)
        self.to_sic_entry_task.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

        self.assign_button = ttk.Button(range_assignment_frame, text="Asignar Trabajo al Servidor", command=self._assign_task_to_server)
        self.assign_button.grid(row=3, column=0, columnspan=2, padx=5, pady=10)
        range_assignment_frame.columnconfigure(1, weight=1)

    def _create_monitor_tab(self):
        """Crea la nueva pestaña para monitorizar los trabajadores."""
        self.monitor_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.monitor_frame, text="Monitor de Tareas")

        # Treeview para mostrar el estado de los workers
        self.worker_tree = ttk.Treeview(self.monitor_frame, columns=('ID', 'Status', 'Task', 'Progress'), show='headings')
        self.worker_tree.heading('ID', text='Worker ID')
        self.worker_tree.heading('Status', text='Estado')
        self.worker_tree.heading('Task', text='Tarea Actual')
        self.worker_tree.heading('Progress', text='Progreso')

        self.worker_tree.column('ID', width=80, anchor=tk.CENTER)
        self.worker_tree.column('Status', width=120)
        self.worker_tree.column('Task', width=250)
        self.worker_tree.column('Progress', width=200)

        # Crear un estilo para la barra de progreso dentro del Treeview
        s = ttk.Style()
        s.layout("LabeledProgressbar",
                 [('LabeledProgressbar.trough',
                   {'children': [('LabeledProgressbar.pbar',
                                 {'side': 'left', 'sticky': 'ns'}),
                                ("LabeledProgressbar.label",
                                 {"sticky": ""})],
                    'sticky': 'nswe'})])
        s.configure("LabeledProgressbar", text="0 %")

        self.worker_tree.pack(fill=tk.BOTH, expand=True)

    def _start_status_polling(self):
        """Inicia el sondeo periódico para obtener el estado detallado de los trabajadores."""
        self._update_worker_status()
        self.master.after(2000, self._start_status_polling) # Polling cada 2 segundos

    def _update_worker_status(self):
        """Obtiene y renderiza el estado detallado de los trabajadores."""
        if not hasattr(self, 'server_url'): # Asegurarse de que la GUI está lista
            return

        server_url = self.server_url.get().rstrip('/')
        if not server_url or self.connection_status_label.cget("text") != "Conectado":
            return # No hacer polling si no estamos conectados

        try:
            response = requests.get(f"{server_url}/detailed_status", timeout=1.5)
            if response.status_code == 200:
                worker_states = response.json()

                # Limpiar el treeview
                current_items = {self.worker_tree.item(i, "values")[0]: i for i in self.worker_tree.get_children()}

                for worker_id, state in worker_states.items():
                    worker_id_str = str(worker_id)
                    values = (
                        worker_id_str,
                        state.get('status', 'N/A'),
                        state.get('current_task', 'N/A'),
                        f"{state.get('progress', 0):.2f}%"
                    )

                    if worker_id_str in current_items:
                        # Actualizar item existente
                        self.worker_tree.item(current_items[worker_id_str], values=values)
                    else:
                        # Insertar nuevo item
                        self.worker_tree.insert("", tk.END, iid=worker_id_str, values=values)

        except requests.exceptions.RequestException as e:
            # Silencioso para no molestar con popups si el servidor cae temporalmente
            logger.debug(f"Error en polling de estado: {e}")
        except Exception as e:
            logger.error(f"Error inesperado actualizando estado de workers: {e}")

    def _upload_courses_file(self):
        """Abre el diálogo para seleccionar un archivo y lo sube al servidor."""
        if self.connection_status_label.cget("text") != "Conectado":
            messagebox.showerror("No Conectado", "Por favor, conéctese a un servidor primero.")
            return

        filepath = filedialog.askopenfilename(
            title="Seleccione un archivo de cursos",
            filetypes=[("Archivos Excel", "*.xlsx"), ("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if not filepath:
            return

        server_url = self.server_url.get().rstrip('/')
        self.results_frame.add_log(f"Subiendo archivo {os.path.basename(filepath)} al servidor...")

        try:
            with open(filepath, 'rb') as f:
                files = {'file': (os.path.basename(filepath), f)}
                response = requests.post(f"{server_url}/upload_courses", files=files, timeout=30)

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
            messagebox.showerror("Error de Red", f"No se pudo comunicar con el servidor: {e}")
            self.results_frame.add_log(f"Error de red: {e}")
        except Exception as e:
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
            self.course_tree.delete(*self.course_tree.get_children())
            self.from_sic_listbox.delete(0, tk.END)
            self.to_sic_listbox.delete(0, tk.END)

            # Poblar la tabla (Treeview) y los Listbox
            for sic_code, course_name in self.detailed_sic_codes_with_courses:
                self.course_tree.insert("", tk.END, values=(sic_code, course_name))
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
            self.from_sic_entry.delete(0, tk.END)
            self.from_sic_entry.insert(0, sic_code)
            self.from_sic_entry_task.delete(0, tk.END)
            self.from_sic_entry_task.insert(0, sic_code)

    def _on_to_sic_select(self, event):
        selection = self.to_sic_listbox.curselection()
        if selection:
            selected_text = self.to_sic_listbox.get(selection[0])
            sic_code = selected_text.split(' - ')[0]
            self.to_sic_entry.delete(0, tk.END)
            self.to_sic_entry.insert(0, sic_code)
            self.to_sic_entry_task.delete(0, tk.END)
            self.to_sic_entry_task.insert(0, sic_code)

    def _on_search_from(self, event):
        search_term = self.search_from_entry.get().lower()
        self.from_sic_listbox.delete(0, tk.END)
        for sic_code, course_name in self.detailed_sic_codes_with_courses:
            display_text = f"{sic_code} - {course_name}"
            if search_term in display_text.lower():
                self.from_sic_listbox.insert(tk.END, display_text)

    def _on_search_to(self, event):
        search_term = self.to_sic_entry.get().lower()
        self.to_sic_listbox.delete(0, tk.END)
        for sic_code, course_name in self.detailed_sic_codes_with_courses:
            display_text = f"{sic_code} - {course_name}"
            if search_term in display_text.lower():
                self.to_sic_listbox.insert(tk.END, display_text)

    def _update_timer_display(self, time_str):
        self.queue.put(('update_timer', time_str))

    def _on_start_scraping(self):
        """Maneja el clic del botón de inicio de scraping (OBSOLETO)."""
        messagebox.showinfo("Acción no disponible", "Esta función ha sido reemplazada por el sistema de 'Gestión de Tareas'.\n\nPor favor, use la pestaña 'Gestión de Tareas' para asignar un trabajo al servidor.")

    def _on_stop_scraping(self):
        """Maneja el clic del botón de detención de scraping."""
        server_url = self.server_url.get().rstrip('/')
        try:
            requests.post(f"{server_url}/stop_scraping", timeout=5)
            messagebox.showinfo("Detención Solicitada", "Se ha enviado una solicitud para detener el trabajo al servidor.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error de Red", f"No se pudo enviar la solicitud de detención: {e}")

    def _on_export_results(self):
        pass # La lógica de exportación podría requerir un nuevo enfoque

    def _on_open_results_folder(self):
        results_dir = os.path.abspath("results")
        if not os.path.exists(results_dir):
            os.makedirs(results_dir, exist_ok=True)
        try:
            if os.name == 'nt': os.startfile(results_dir)
            elif os.name == 'posix': subprocess.run(['xdg-open', results_dir])
        except Exception as e:
            logger.error(f"Error abriendo carpeta de resultados: {str(e)}")

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
