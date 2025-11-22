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

from gui.styles import setup_styles
from gui.timer_manager import TimerManager
from gui.components.gui_components import (
    ProgressFrame, ResultsFrame, ControlFrame
)
from gui.proxy_config import ProxyConfigWindow
from gui.captcha_config import CaptchaConfigWindow
from gui.config_tab import ConfigTab
from utils.csv_handler import CSVHandler
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
        # Para cliente/server, el controller será None y usaremos llamadas al servidor
        self.controller = None
        self.current_task_id = None
        print("ScraperGUI inicializado")
        
        # Configurar el manejador CSV
        self.csv_handler = CSVHandler()
        
        # Inicializar el gestor de proxies
        self.proxy_manager = ProxyManager()
        
        # Inicializar configuración
        self.config = Config()
        
        # Verificar el archivo CSV
        self._check_csv_file()
        
        # Cola para comunicación entre hilos
        self.queue = queue.Queue()
        
        # Inicializar el gestor de temporizador
        self.timer_manager = TimerManager(update_callback=self._update_timer_display)
        
        # Variables para el estado de la aplicación
        self.results = None
        self.current_course_info = ""
        self.is_updating = False
        
        # Configurar estilos para accesibilidad
        setup_styles()
        
        # Configurar la interfaz de usuario
        self._setup_ui()
        
        # Cargar datos
        self._load_data()
        
        # Configurar el handler global para recibir logs
        global_log_handler = get_global_log_handler()
        global_log_handler.set_callback(self._log_callback)
        
        # Iniciar procesamiento de cola
        self.process_queue()
        
        # Configurar eventos de redimensionamiento
        self.master.bind("<Configure>", self._on_resize)
        
        # Mostrar logs existentes
        self._show_existing_logs()

        # Iniciar descubrimiento de servidores
        self._discover_servers()

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
        # Obtener el nombre del equipo
        computer_name = socket.gethostname()
        self.master.title(f"Europa Scraper - {computer_name}")
        self.master.geometry("1200x700")
        self.master.minsize(1000, 600)
        
        # Configurar el color de fondo de la ventana principal
        self.master.configure(background="#f0f0f0")
        
        # Crear un notebook para las pestañas
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Crear un frame principal sin scroll para la pestaña principal
        self.main_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.main_frame, text="Principal")
        
        # Pestaña de Configuración del Servidor
        self._create_server_config_tab()

        # Pestaña de Descubrimiento de Servidores
        self._create_server_discovery_tab()
        
        # Pestaña de Configuración (después de "Programar Rangos")
        self.config_tab = ConfigTab(self.notebook, self.config)

        
        # Crear un PanedWindow para permitir al usuario redimensionar las columnas
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Crear las tres columnas como paneles del PanedWindow
        self.left_column = ttk.Frame(self.paned_window)
        self.center_column = ttk.Frame(self.paned_window)
        self.right_column = ttk.Frame(self.paned_window)
        
        # Añadir las columnas al PanedWindow
        self.paned_window.add(self.left_column, weight=2)
        self.paned_window.add(self.center_column, weight=6)  # Columna central más ancha
        self.paned_window.add(self.right_column, weight=2)
        
        # COLUMNA IZQUIERDA - Selección de Código
        
        # Crear marco para selección de código SIC
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

        # COLUMNA CENTRAL - Treeview y Controles
        
        # Crear un frame para el título y el timer
        self.header_frame = ttk.Frame(self.center_column)
        self.header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Título de la aplicación
        self.title_label = ttk.Label(
            self.header_frame, 
            text=f"Europa Scraper - {computer_name}",
            style="Heading.TLabel"
        )
        self.title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Timer en la parte superior derecha
        self.timer_label = ttk.Label(
            self.header_frame, 
            text="Tiempo: 00:00:00",
            style="Timer.TLabel"
        )
        self.timer_label.pack(side=tk.RIGHT, padx=10)

        # Treeview para mostrar los cursos
        self.course_tree_frame = ttk.LabelFrame(self.center_column, text="Cursos Disponibles", padding=10)
        self.course_tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.course_tree = ttk.Treeview(self.course_tree_frame, columns=("sic_code", "course_name", "status", "server"), show="headings")
        self.course_tree.heading("sic_code", text="Código SIC")
        self.course_tree.heading("course_name", text="Nombre del Curso")
        self.course_tree.heading("status", text="Estado")
        self.course_tree.heading("server", text="Servidor")

        self.course_tree.column("sic_code", width=100, anchor=tk.W)
        self.course_tree.column("course_name", width=300, anchor=tk.W)
        self.course_tree.column("status", width=80, anchor=tk.CENTER)
        self.course_tree.column("server", width=100, anchor=tk.W)

        self.course_tree_scrollbar = ttk.Scrollbar(self.course_tree_frame, orient=tk.VERTICAL, command=self.course_tree.yview)
        self.course_tree.configure(yscrollcommand=self.course_tree_scrollbar.set)

        self.course_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.course_tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.course_tree.bind('<<TreeviewSelect>>', self._on_course_select)

        # Crear marco para el motor de búsqueda
        self.engine_frame = ttk.Frame(self.center_column)
        self.engine_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.engine_frame, text="Motor de Búsqueda:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_engine_var = tk.StringVar()
        self.search_engine_combo = ttk.Combobox(
            self.engine_frame,
            textvariable=self.search_engine_var,
            values=["Google", "DuckDuckGo", "Cordis Europa", "Common Crawl", "Wayback Machine"],
            state="readonly"
        )
        self.search_engine_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_engine_var.set(self.config.get("search_engine", "DuckDuckGo"))
        self.search_engine_combo.bind("<<ComboboxSelected>>", self._on_search_engine_select)

        # Crear marco para el dominio del sitio (inicialmente oculto)
        self.site_domain_frame = ttk.Frame(self.center_column)
        self.site_domain_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.site_domain_frame, text="Dominio Site:").pack(side=tk.LEFT, padx=(0, 5))
        self.site_domain_var = tk.StringVar(value="usa.gov")
        self.site_domain_entry = ttk.Entry(self.site_domain_frame, textvariable=self.site_domain_var)
        self.site_domain_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Ocultar el marco de dominio inicialmente
        # Checkbox to restrict to .gov pages when using Wayback
        self.gov_only_var = tk.BooleanVar(value=True)
        self.gov_only_check = ttk.Checkbutton(search_config_frame, text="Solo páginas .gov", variable=self.gov_only_var)
        self.gov_only_check.pack(fill=tk.X, pady=(0,5))
        self.control_frame = ControlFrame(
            self.center_column,
            on_start=self._on_start_scraping,
            on_stop=self._on_stop_scraping
        )
        self.control_frame.pack(fill=tk.X, pady=2)
        
        # Crear marco de progreso
        self.progress_frame = ProgressFrame(self.center_column)
        self.progress_frame.pack(fill=tk.X, pady=2)
        
        # COLUMNA DERECHA - Resultados
        
        # Crear marco de resultados
        self.results_frame = ResultsFrame(self.right_column)
        self.results_frame.pack(fill=tk.BOTH, expand=True)

        # Crear marco para los botones de resultados
        self.results_buttons_frame = ttk.Frame(self.right_column)
        self.results_buttons_frame.pack(fill=tk.X, pady=5)

        # Botón de exportar resultados
        self.export_button = ttk.Button(
            self.results_buttons_frame,
            text="Exportar Resultados",
            command=self._on_export_results,
            state=tk.DISABLED,
            style="TButton"
        )
        self.export_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        # Botón de abrir carpeta de resultados
        self.open_folder_button = ttk.Button(
            self.results_buttons_frame,
            text="Abrir Carpeta de Resultados",
            command=self._on_open_results_folder,
            style="TButton"
        )
        self.open_folder_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        # Configurar el PanedWindow para que se ajuste inicialmente
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

        # Título
        title_label = ttk.Label(
            self.server_frame,
            text="Configuración del Servidor",
            style="Heading.TLabel"
        )
        title_label.pack(pady=10)

        # Marco de configuración
        config_frame = ttk.LabelFrame(self.server_frame, text="Configuración", padding=10)
        config_frame.pack(fill=tk.X, pady=10)

        # URL del servidor
        ttk.Label(config_frame, text="URL del Servidor:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.server_url = tk.StringVar(value="http://localhost:8001")
        self.server_url_entry = ttk.Entry(config_frame, textvariable=self.server_url, width=50)
        self.server_url_entry.grid(row=0, column=1, padx=10, pady=5, sticky=tk.EW)

        # API Key (opcional)
        ttk.Label(config_frame, text="API Key (opcional):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.api_key = tk.StringVar(value="")
        self.api_key_entry = ttk.Entry(config_frame, textvariable=self.api_key, width=50, show="*")
        self.api_key_entry.grid(row=1, column=1, padx=10, pady=5, sticky=tk.EW)

        # Botón de conexión
        self.connect_button = ttk.Button(
            config_frame, 
            text="Conectar", 
            command=self._connect_to_server
        )
        self.connect_button.grid(row=2, column=1, padx=10, pady=20, sticky=tk.E)

        # Estado de conexión
        self.connection_status_label = ttk.Label(
            config_frame, 
            text="Desconectado", 
            foreground="red"
        )
        self.connection_status_label.grid(row=3, column=1, padx=10, sticky=tk.E)

        # Configurar pesos de las columnas
        config_frame.columnconfigure(1, weight=1)

    def _create_server_discovery_tab(self):
        """Crea la pestaña de descubrimiento de servidores."""
        self.discovery_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.discovery_frame, text="Programar Rangos")

        # Crear un PanedWindow para dividir la pestaña en dos
        self.discovery_paned_window = ttk.PanedWindow(self.discovery_frame, orient=tk.HORIZONTAL)
        self.discovery_paned_window.pack(fill=tk.BOTH, expand=True)

        # Panel izquierdo para la tabla de servidores
        self.server_list_frame = ttk.LabelFrame(self.discovery_paned_window, text="Servidores y Tareas", padding="10")
        self.discovery_paned_window.add(self.server_list_frame, weight=1)

        # Crear treeview con columnas para servidor, estado y status
        self.server_tree = ttk.Treeview(self.server_list_frame, columns=('Server', 'Status', 'Tasks'), show='tree headings', height=12)
        self.server_tree.heading('#0', text='ID')
        self.server_tree.heading('Server', text='Servidor')
        self.server_tree.heading('Status', text='Estado')
        self.server_tree.heading('Tasks', text='Estado de Tareas')
        
        self.server_tree.column('#0', width=40, minwidth=40, stretch=False)
        self.server_tree.column('Server', width=300, stretch=True)
        self.server_tree.column('Status', width=100, stretch=False)
        self.server_tree.column('Tasks', width=200, stretch=True)
        
        self.server_scrollbar = ttk.Scrollbar(self.server_list_frame, orient=tk.VERTICAL, command=self.server_tree.yview)
        self.server_tree.configure(yscrollcommand=self.server_scrollbar.set)
        self.server_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.server_scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        # Frame de controles
        self.server_controls_frame = ttk.Frame(self.server_list_frame)
        self.server_controls_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Botón para refrescar
        self.refresh_servers_button = ttk.Button(
            self.server_controls_frame,
            text="Refrescar Servidores",
            command=self._discover_servers
        )
        self.refresh_servers_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Botón para ver estado
        self.check_status_button = ttk.Button(
            self.server_controls_frame,
            text="Ver Estado",
            command=self._check_server_status
        )
        self.check_status_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Panel derecho para la asignación de rangos
        self.range_assignment_frame = ttk.LabelFrame(self.discovery_paned_window, text="Asignar Rango", padding="10")
        self.discovery_paned_window.add(self.range_assignment_frame, weight=3)

        # Controles de asignación de rango
        self.from_sic_label = ttk.Label(self.range_assignment_frame, text="Desde SIC:")
        self.from_sic_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.from_sic_entry = ttk.Entry(self.range_assignment_frame)
        self.from_sic_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        self.to_sic_label = ttk.Label(self.range_assignment_frame, text="Hasta SIC:")
        self.to_sic_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.to_sic_entry = ttk.Entry(self.range_assignment_frame)
        self.to_sic_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

        # Motor de búsqueda
        self.engine_label = ttk.Label(self.range_assignment_frame, text="Motor de Búsqueda:")
        self.engine_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.search_engine_var_discovery = tk.StringVar()
        self.search_engine_combo_discovery = ttk.Combobox(
            self.range_assignment_frame,
            textvariable=self.search_engine_var_discovery,
            values=["Google", "DuckDuckGo", "Cordis Europa"],
            state="readonly"
        )
        self.search_engine_combo_discovery.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        self.search_engine_var_discovery.set(self.config.get("search_engine", "DuckDuckGo"))

        self.assign_button = ttk.Button(
            self.range_assignment_frame,
            text="Asignar Tarea",
            command=self._assign_task_to_server
        )
        self.assign_button.grid(row=3, column=0, columnspan=2, padx=5, pady=10)

        self.range_assignment_frame.columnconfigure(1, weight=1)


    def _discover_servers(self):
        """Descubre servidores en la red local."""
        logger.info("Descubriendo servidores...")
        self.server_listbox.delete(0, tk.END)

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
                            self.queue.put(('add_server', server_address))
                except socket.timeout:
                    logger.info("Timeout esperando broadcasts de servidores.")
                    break  # Salir del bucle si no se reciben más respuestas
                except Exception as e:
                    logger.error(f"Error escuchando broadcasts: {e}")
                    break

    def _assign_task_to_server(self):
        """Asigna una tarea de scraping al servidor seleccionado."""
        selected_items = self.server_tree.selection()
        if not selected_items:
            messagebox.showwarning("Servidor no seleccionado", "Por favor, seleccione un servidor de la lista.")
            return

        # Obtener la dirección del servidor desde el Treeview
        server_id = selected_items[0]
        server_address = self.server_tree.item(server_id, 'values')[0]

        from_sic = self.from_sic_entry.get()
        to_sic = self.to_sic_entry.get()

        if not from_sic or not to_sic:
            messagebox.showwarning("Rango no especificado", "Por favor, ingrese los códigos SIC de inicio y fin.")
            return

        logger.info(f"Asignando tarea al servidor {server_address}: Rango SIC de {from_sic} a {to_sic}")

        try:
            import requests
            import json

            server_url = f"http://{server_address}"

            # Preparar datos para enviar al servidor
            scraping_config = {
                'from_sic': from_sic,
                'to_sic': to_sic,
                'from_course': "",  # Estos campos pueden ser opcionales en el servidor
                'to_course': "",
                'min_words': self.config.get('min_words', 30),
                'search_engine': self.search_engine_var_discovery.get()
            }

            # Enviar solicitud al servidor
            response = requests.post(
                f"{server_url}/start_scraping",
                json=scraping_config,
                timeout=10
            )

            if response.status_code == 202:
                result = response.json()
                task_id = result.get('task_id')
                if task_id:
                    messagebox.showinfo("Tarea Asignada", f"La tarea ha sido asignada al servidor {server_address} con el ID: {task_id}")
                    logger.info(f"Tarea {task_id} asignada a {server_address}")
                else:
                    messagebox.showerror("Error del Servidor", f"El servidor devolvió una respuesta inesperada: {result.get('message', 'Error desconocido')}")
            else:
                messagebox.showerror("Error de Comunicación", f"Error al comunicarse con el servidor: {response.status_code} - {response.text}")

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error de Red", f"No se pudo conectar con el servidor: {e}")
            logger.error(f"Error de red al asignar tarea: {e}")
        except Exception as e:
            messagebox.showerror("Error Inesperado", f"Ocurrió un error inesperado: {e}")
            logger.error(f"Error inesperado al asignar tarea: {e}")

    def _open_proxy_config(self):
        """Abre la ventana de configuración de proxies."""
        ProxyConfigWindow(self.master, self.proxy_manager, self._on_proxy_config_saved)
    
    def _on_proxy_config_saved(self, proxies):
        """
        Callback para cuando se guardan los proxies.
        
        Args:
            proxies: Lista de proxies configurados
        """
        logger.info(f"Configuración de proxies actualizada. {len(proxies)} proxies configurados.")
        
        # Si el controlador tiene un browser_manager, actualizar sus proxies
        if self.controller and hasattr(self.controller, 'browser_manager'):
            # Pasar los proxies al browser_manager si tiene un método para ello
            if hasattr(self.controller.browser_manager, 'set_proxies'):
                self.controller.browser_manager.set_proxies(proxies)
        
        # Mostrar mensaje en el área de logs
        if hasattr(self, 'results_frame'):
            self.results_frame.add_log(f"Configuración de proxies actualizada. {len(proxies)} proxies configurados.")

    def _open_captcha_config(self):
        """Abre la ventana de configuración de CAPTCHAs."""
        # Obtener el solucionador de CAPTCHAs del controlador
        captcha_solver = None
        if self.controller and hasattr(self.controller, 'browser_manager'):
            captcha_solver = getattr(self.controller.browser_manager, 'captcha_solver', None)
    
        CaptchaConfigWindow(self.master, captcha_solver, self._on_captcha_config_saved)

    def _connect_to_server(self):
        """Conecta al servidor"""
        try:
            import requests
            
            server_url = self.server_url.get().rstrip('/')
            
            # Verificar conexión con el servidor
            response = requests.get(f"{server_url}/", timeout=5)
            
            if response.status_code == 200:
                server_info = response.json()
                if server_info.get("status") == "running":
                    # Actualizar estado de conexión
                    self.connection_status_label.config(text="Conectado", foreground="green")
                    self.connect_button.config(text="Desconectar", command=self._disconnect_from_server)
                    
                    # Actualizar estado en la interfaz principal
                    if hasattr(self, 'control_frame'):
                        self.control_frame.server_connected = True
                    
                    messagebox.showinfo("Conexión Exitosa", "Conectado al servidor correctamente")
                    logger.info(f"Conectado al servidor: {server_url}")
                else:
                    raise Exception("Servidor no disponible")
            else:
                raise Exception(f"Error de conexión: {response.status_code}")
                
        except Exception as e:
            # Actualizar estado de conexión
            self.connection_status_label.config(text="Desconectado", foreground="red")
            self.connect_button.config(text="Conectar", command=self._connect_to_server)
            
            # Actualizar estado en la interfaz principal
            if hasattr(self, 'control_frame'):
                self.control_frame.server_connected = False
                
            messagebox.showerror("Error de Conexión", f"No se pudo conectar al servidor:\n{str(e)}")
            logger.error(f"Error conectando al servidor: {str(e)}")

    def _disconnect_from_server(self):
        """Desconecta del servidor"""
        # Actualizar estado de conexión
        self.connection_status_label.config(text="Desconectado", foreground="red")
        self.connect_button.config(text="Conectar", command=self._connect_to_server)
        
        # Actualizar estado en la interfaz principal
        if hasattr(self, 'control_frame'):
            self.control_frame.server_connected = False
            
        messagebox.showinfo("Desconexión", "Desconectado del servidor")
        logger.info("Desconectado del servidor")

    def _disconnect_from_server(self):
        """Desconecta del servidor"""
        # Actualizar estado de conexión
        self.connection_status_label.config(text="Desconectado", foreground="red")
        self.connect_button.config(text="Conectar", command=self._connect_to_server)
        
        # Actualizar estado en la interfaz principal
        if hasattr(self, 'control_frame'):
            self.control_frame.server_connected = False
            
        messagebox.showinfo("Desconexión", "Desconectado del servidor")
        logger.info("Desconectado del servidor")

    def _on_resize(self, event):
        """
        Maneja el evento de redimensionamiento de la ventana.
        Ajusta los elementos para que sean responsivos.
        
        Args:
            event: Evento de redimensionamiento
        """
        # Evitar múltiples actualizaciones durante el redimensionamiento
        if not self.is_updating:
            self.is_updating = True
            
            # Ajustar el ancho de wraplength para las etiquetas según el ancho de la columna izquierda
            try:
                if hasattr(self, 'left_column') and hasattr(self, 'progress_frame'):
                    left_width = self.left_column.winfo_width()
                    if left_width > 100:  # Evitar valores negativos o muy pequeños
                        wrap_width = left_width - 50  # Dejar margen
                        if hasattr(self.progress_frame, 'processing_label'):
                            self.progress_frame.processing_label.configure(wraplength=wrap_width)
                        if hasattr(self.progress_frame, 'searching_label'):
                            self.progress_frame.searching_label.configure(wraplength=wrap_width)
            except Exception as e:
                logger.debug(f"Error en redimensionamiento: {e}")
            
            self.is_updating = False

    def _on_course_select(self, event):
        """Maneja la selección de un curso en la tabla."""
        selected_items = self.course_tree.selection()
        if selected_items:
            # Solo para depuración, podrías querer hacer algo más aquí
            logger.info(f"{len(selected_items)} filas seleccionadas.")

    def _load_data(self):
        """Carga datos del archivo CSV y puebla la tabla."""
        try:
            # Cargar datos del curso
            self.csv_handler.load_course_data()
          
            # Obtener códigos SIC detallados con toda la información
            self.detailed_sic_codes_with_courses = self.csv_handler.get_detailed_sic_codes_with_courses()
          
            logger.info(f"Cargados {len(self.detailed_sic_codes_with_courses)} cursos para la tabla")
            logger.debug(f"Primeros 5 cursos cargados: {self.detailed_sic_codes_with_courses[:5]}")
          
            if not self.detailed_sic_codes_with_courses:
                logger.warning("No se encontraron cursos en el archivo CSV.")
                messagebox.showwarning("Advertencia", "No se encontraron cursos en el archivo CSV. Verifique que el archivo data/class5_course_list.csv existe y tiene datos.")
                return
          
            # Limpiar la tabla antes de cargar nuevos datos
            for i in self.course_tree.get_children():
                self.course_tree.delete(i)

            # Poblar la tabla (Treeview)
            for sic_code, course_name, status, server, codigo in self.detailed_sic_codes_with_courses:
                self.course_tree.insert("", tk.END, values=(sic_code, course_name, status, server))
            
            # Limpiar y poblar los Listbox de selección de SIC
            self.from_sic_listbox.delete(0, tk.END)
            self.to_sic_listbox.delete(0, tk.END)

            for sic_code, course_name, status, server, codigo in self.detailed_sic_codes_with_courses:
                display_text = f"{sic_code} - {course_name}"
                self.from_sic_listbox.insert(tk.END, display_text)
                self.to_sic_listbox.insert(tk.END, display_text)
          
            logger.info("Datos cargados exitosamente en la tabla y listboxes")
          
        except Exception as e:
            logger.error(f"Error cargando datos: {str(e)}")
            messagebox.showerror("Error", f"Error cargando datos: {str(e)}")

    def _check_csv_file(self):
        """Verifica si el archivo CSV existe y tiene el formato correcto."""
        csv_file = os.path.join("data", "class5_course_list.csv")
        if not os.path.exists(csv_file):
            logger.error(f"Archivo CSV no encontrado: {csv_file}")
            messagebox.showerror("Error", f"Archivo CSV no encontrado: {csv_file}")
            return False
      
        try:
            # Intentar leer el archivo CSV
            import pandas as pd
            df = pd.read_csv(csv_file)
          
            # Verificar si tiene las columnas necesarias (sic_code y course)
            required_columns = ['sic_code', 'course']
            missing_columns = [col for col in required_columns if col not in df.columns]
          
            # Si no tiene las columnas exactas, verificar si tiene columnas compatibles
            if missing_columns:
                # Verificar compatibilidad hacia atrás con course_name
                if 'sic_code' in df.columns and 'course_name' in df.columns:
                    logger.info("Archivo CSV tiene formato legacy (sic_code, course_name) - compatible")
                    return True
                elif 'code' in df.columns and 'course' in df.columns:
                    logger.info("Archivo CSV tiene formato alternativo (code, course) - compatible")
                    return True
                elif 'code' in df.columns and 'course_name' in df.columns:
                    logger.info("Archivo CSV tiene formato alternativo (code, course_name) - compatible")
                    return True
                else:
                    logger.error(f"Columnas faltantes en el archivo CSV: {missing_columns}")
                    messagebox.showerror("Error", f"El archivo CSV no tiene las columnas necesarias. Se requiere 'sic_code' y 'course' (o columnas compatibles como 'code' y 'course_name')")
                    return False
          
            # Verificar si tiene datos
            if df.empty:
                logger.error("El archivo CSV está vacío")
                messagebox.showerror("Error", "El archivo CSV está vacío")
                return False
          
            return True
      
        except Exception as e:
            logger.error(f"Error verificando archivo CSV: {str(e)}")
            messagebox.showerror("Error", f"Error verificando archivo CSV: {str(e)}")
            return False

    def _on_from_sic_select(self, event):
        """
        Maneja la selección del código SIC 'desde'.
        
        Args:
            event: Evento de selección
        """
        selection = self.from_sic_listbox.curselection()
        if selection:
            selected_text = self.from_sic_listbox.get(selection[0])
            # Extraer solo el sic_code (la parte antes del " - ")
            sic_code = selected_text.split(' - ')[0]
            self.from_sic_entry.delete(0, tk.END)
            self.from_sic_entry.insert(0, sic_code)
            logger.info(f"Seleccionado 'desde' SIC: {sic_code}")

    def _on_to_sic_select(self, event):
        """
        Maneja la selección del código SIC 'hasta'.
        
        Args:
            event: Evento de selección
        """
        selection = self.to_sic_listbox.curselection()
        if selection:
            selected_text = self.to_sic_listbox.get(selection[0])
            # Extraer solo el sic_code (la parte antes del " - ")
            sic_code = selected_text.split(' - ')[0]
            self.to_sic_entry.delete(0, tk.END)
            self.to_sic_entry.insert(0, sic_code)
            logger.info(f"Seleccionado 'hasta' SIC: {sic_code}")

    def _on_search_from(self, event):
        """Filtra la lista 'desde' según el texto de búsqueda."""
        search_term = self.search_from_entry.get().lower()
        self.from_sic_listbox.delete(0, tk.END)
        for sic_code, course_name, status, server in self.detailed_sic_codes_with_courses:
            display_text = f"{sic_code} - {course_name}"
            if search_term in display_text.lower():
                self.from_sic_listbox.insert(tk.END, display_text)

    def _on_search_to(self, event):
        """Filtra la lista 'hasta' según el texto de búsqueda."""
        search_term = self.search_to_entry.get().lower()
        self.to_sic_listbox.delete(0, tk.END)
        for sic_code, course_name, status, server in self.detailed_sic_codes_with_courses:
            display_text = f"{sic_code} - {course_name}"
            if search_term in display_text.lower():
                self.to_sic_listbox.insert(tk.END, display_text)

    def _update_timer_display(self, time_str):
        """
        Actualiza la etiqueta del temporizador.
        
        Args:
            time_str: Cadena de tiempo formateada
        """
        # Usar queue para actualizar la UI desde el hilo
        self.queue.put(('update_timer', time_str))

    def _on_start_scraping(self):
        """Maneja el clic del botón de inicio de scraping."""
        selected_items = self.course_tree.selection()
        if not selected_items:
            messagebox.showwarning("Entrada Faltante", "Por favor seleccione al menos un curso de la tabla.")
            return

        # Obtener el primer y último elemento seleccionado para definir el rango
        first_item_id = selected_items[0]
        last_item_id = selected_items[-1]

        from_values = self.course_tree.item(first_item_id, 'values')
        to_values = self.course_tree.item(last_item_id, 'values')

        from_sic = from_values[0]
        from_course = from_values[1]
        to_sic = to_values[0]
        to_course = to_values[1]
        
        # Actualizar estado de la interfaz
        if hasattr(self, 'control_frame'):
            self.control_frame.set_scraping_started()
        self.export_button.config(state=tk.DISABLED)
        
        # IMPORTANTE: Establecer explícitamente la barra de progreso a 0%
        if hasattr(self, 'progress_frame'):
            self.progress_frame.update_progress(0)
        
        if hasattr(self, 'results_frame'):
            self.results_frame.clear()
        
        # Reiniciar estadísticas
        if hasattr(self, 'progress_frame'):
            self.progress_frame.update_stats(0, 0, 0)
        
        # Reiniciar información del curso
        self.current_course_info = ""
        
        # Reiniciar información de procesamiento y búsqueda
        if hasattr(self, 'progress_frame'):
            self.progress_frame.update_processing_text("")
            self.progress_frame.update_searching_text("")
        
        # Iniciar el timer
        self.timer_manager.start()
        
        # Preparar parámetros de scraping
        params = {
            'from_sic': from_sic,
            'to_sic': to_sic,
            'from_course': from_course,
            'to_course': to_course,
            'site_domain': self.site_domain_var.get(),
            'gov_only': getattr(self, 'gov_only_var', tk.BooleanVar(value=False)).get()
        }

        # Registrar los valores seleccionados para depuración
        logger.info(f"Rango seleccionado: Desde Código {params['from_sic']} hasta {params['to_sic']}")
        logger.info(f"Cursos seleccionados: Desde '{params['from_course']}' hasta '{params['to_course']}'")

        # Añadir dominio si es Common Crawl
        if self.search_engine_var.get() == "Common Crawl":
            params['site_domain'] = self.site_domain_var.get()
            logger.info(f"Dominio para Common Crawl: {params['site_domain']}")
        
        # Iniciar scraping en un hilo separado
        threading.Thread(target=self._run_scraping, args=(params,), daemon=True).start()

    def _on_search_engine_select(self, event):
        """Maneja la selección en el combobox del motor de búsqueda."""
        if self.search_engine_var.get() == "Common Crawl":
            self.site_domain_frame.pack(fill=tk.X, pady=5)
        else:
            self.site_domain_frame.pack_forget()

    def _on_stop_scraping(self):
        """Maneja el clic del botón de detención de scraping."""
        if self.controller:
            self.controller.stop_scraping()
            logger.info("Deteniendo scraping...")
            # No detenemos el timer aquí, se detendrá cuando se reciba el mensaje 'scraping_done'

    def _on_export_results(self):
        """Maneja el clic del botón de exportar resultados."""
        if not self.results:
            messagebox.showwarning("Sin Resultados", "No hay resultados para exportar.")
            return
        
        # Preguntar qué tipo de resultados exportar
        export_type = messagebox.askyesnocancel(
            "Exportar Resultados",
            "¿Desea exportar los resultados guardados?\n\n"
            "Sí: Exportar resultados guardados\n"
            "No: Exportar resultados omitidos\n"
            "Cancelar: Cancelar operación"
        )
        
        if export_type is None:  # Cancelar
            return
        
        if export_type:  # Sí - Exportar resultados guardados
            # Solicitar ubicación para guardar el archivo
            output_file = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                title="Guardar Resultados Como"
            )
            
            if not output_file:
                return  # Usuario canceló la operación
            
            try:
                # Guardar resultados en el archivo CSV
                self.csv_handler.save_results_to_csv(self.results, output_file)
                
                messagebox.showinfo("Exportación Exitosa", f"Resultados exportados a:\n{output_file}")
                logger.info(f"Resultados exportados a: {output_file}")
                
            except Exception as e:
                logger.error(f"Error exportando resultados: {str(e)}")
                messagebox.showerror("Error", f"Error exportando resultados: {str(e)}")
        else:  # No - Exportar resultados omitidos
            # Solicitar ubicación para guardar el archivo
            output_file = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
                title="Guardar Resultados Omitidos Como"
            )
            
            if not output_file:
                return  # Usuario canceló la operación
            
            try:
                # Verificar si el controlador tiene resultados omitidos
                if hasattr(self.controller, 'omitted_results') and self.controller.omitted_results:
                    # Guardar resultados omitidos en el archivo Excel
                    saved_file = self.controller._save_omitted_to_excel(output_file)
                    
                    if saved_file:
                        messagebox.showinfo("Exportación Exitosa", f"Resultados omitidos exportados a:\n{saved_file}")
                        logger.info(f"Resultados omitidos exportados a: {saved_file}")
                    else:
                        messagebox.showwarning("Sin Resultados", "No hay resultados omitidos para exportar.")
                else:
                    messagebox.showwarning("Sin Resultados", "No hay resultados omitidos para exportar.")
            except Exception as e:
                logger.error(f"Error exportando resultados omitidos: {str(e)}")
                messagebox.showerror("Error", f"Error exportando resultados omitidos: {str(e)}")

    def _on_open_results_folder(self):
        """Maneja el clic del botón de abrir carpeta de resultados."""
        results_dir = os.path.abspath("results")
        
        # Verificar si la carpeta existe
        if not os.path.exists(results_dir):
            os.makedirs(results_dir, exist_ok=True)
            logger.info(f"Carpeta de resultados creada: {results_dir}")
        
        # Abrir la carpeta en el explorador de archivos
        try:
            if os.name == 'nt':  # Windows
                os.startfile(results_dir)
            elif os.name == 'posix':  # macOS, Linux
                subprocess.run(['xdg-open', results_dir])
            else:
                logger.warning(f"No se pudo abrir la carpeta en el sistema operativo: {os.name}")
                messagebox.showinfo("Información", f"La carpeta de resultados está en: {results_dir}")
        except Exception as e:
            logger.error(f"Error abriendo carpeta de resultados: {str(e)}")
            messagebox.showerror("Error", f"Error abriendo carpeta de resultados: {str(e)}")

    def _run_scraping(self, params):
        """
        Ejecuta el proceso de scraping en un hilo separado.
        
        Args:
            params: Parámetros de scraping
        """
        try:
            # En modo cliente/servidor, enviamos solicitud al servidor
            import requests
            import json
            import uuid
            
            server_url = self.server_url.get().rstrip('/')
            
            # Preparar datos para enviar al servidor
            scraping_config = {
                'from_sic': params['from_sic'],
                'to_sic': params['to_sic'],
                'from_course': params['from_course'],
                'to_course': params['to_course'],
                'min_words': self.config.get('min_words', 30),
                'search_engine': self.search_engine_var.get() # Obtener del nuevo combobox
            }
            
            # Enviar solicitud al servidor
            try:
                response = requests.post(
                    f"{server_url}/start_scraping", 
                    json=scraping_config,
                    timeout=30
                )
                
                if response.status_code == 202:
                    result = response.json()
                    task_id = result.get('task_id')
                    if task_id:
                        self.queue.put(('status', f"Scraping task submitted. Task ID: {task_id}"))
                        self.queue.put(('status', "Scraping task is being processed on the server"))
                        self.current_task_id = task_id
                    else:
                        self.queue.put(('error', f"Server error: {result.get('message', 'Unknown error')}"))
                else:
                    self.queue.put(('error', f"Server HTTP error: {response.status_code} - {response.text}"))
                    
            except requests.exceptions.ConnectionError:
                self.queue.put(('error', "Could not connect to the server"))
            except Exception as e:
                self.queue.put(('error', f"Error sending request to server: {str(e)}"))
                
        except Exception as e:
            logger.error(f"Error durante el scraping: {str(e)}")
            self.queue.put(('error', f"Error durante el scraping: {str(e)}"))
        finally:
            # Detener el timer cuando se completa el scraping
            self.timer_manager.stop()
            self.queue.put(('scraping_done', None))

    def _log_callback(self, log_entry):
        """
        Callback para recibir logs en tiempo real.
        
        Args:
            log_entry: Entrada de log
        """
        # Enviar el log a la cola para ser procesado en el hilo principal
        self.queue.put(('log', log_entry))

    def _progress_callback(self, percentage, message, stats, current_course=0, total_courses=0, phase=1):
        """
        Callback para actualizar el progreso del scraping.
        
        Args:
            percentage: Porcentaje de progreso (0-100)
            message: Mensaje de estado
            stats: Estadísticas del scraping
            current_course: Curso actual
            total_courses: Total de cursos
            phase: Fase actual (1=búsqueda, 2=tabulación)
        """
        try:
            # Actualizar la barra de progreso
            if hasattr(self, 'progress_frame'):
                self.progress_frame.update_progress(percentage)
        
                # Actualizar el mensaje de estado en la etiqueta de búsqueda
                self.progress_frame.update_searching_text(message)
        
                # Actualizar las estadísticas
                saved = stats.get('saved_records', 0)
                not_saved = stats.get('files_not_saved', 0)
                errors = stats.get('total_errors', 0)
                self.progress_frame.update_stats(saved, not_saved, errors)
        
                # Actualizar la información del curso según la fase
                course_info = ""
        
                if phase == 1:  # Fase de búsqueda
                    if current_course > 0 and total_courses > 0:
                        course_info = f"Curso {current_course} de {total_courses}"
                        # Actualizar texto de procesamiento para mostrar información adicional
                        self.progress_frame.update_processing_text(course_info)
                elif phase == 2:  # Fase de tabulación
                    if current_course > 0 and total_courses > 0:
                        course_info = f"Tabulando curso {current_course} de {total_courses}"
                        # Actualizar texto de procesamiento para mostrar información adicional
                        self.progress_frame.update_processing_text(course_info)
        
            # Registrar el mensaje en el log
            logging.info(message)
        
        except Exception as e:
            logging.error(f"Error en callback de progreso: {str(e)}")

    def process_queue(self):
        """Procesa mensajes de la cola."""
        try:
            # Limitar el número de mensajes procesados por ciclo para evitar parpadeo
            messages_processed = 0
            max_messages_per_cycle = 10
            
            while not self.queue.empty() and messages_processed < max_messages_per_cycle:
                message_type, message = self.queue.get_nowait()
                messages_processed += 1
                
                if message_type == 'status':
                    logger.info(message)
                elif message_type == 'progress':
                    # Actualizar la barra de progreso con el valor exacto proporcionado
                    if hasattr(self, 'progress_frame'):
                        self.progress_frame.update_progress(message)
                elif message_type == 'results':
                    self.results = message
                    if hasattr(self, 'results_frame'):
                        self.results_frame.display_results(message)
                elif message_type == 'error':
                    messagebox.showerror("Error", message)
                    logger.error(message)
                elif message_type == 'scraping_done':
                    if hasattr(self, 'control_frame'):
                        self.control_frame.set_scraping_stopped()
                    # Detener el timer cuando se completa el scraping
                    self.timer_manager.stop()
                    logger.info("Proceso de scraping finalizado, timer detenido")
                elif message_type == 'enable_export':
                    self.export_button.config(state=tk.NORMAL)
                elif message_type == 'show_message':
                    messagebox.showinfo("Proceso Completado", message)
                elif message_type == 'update_timer':
                    if hasattr(self, 'timer_label'):
                        self.timer_label.config(text=message)
                elif message_type == 'update_course_info':
                    self.current_course_info = message
                elif message_type == 'update_stats':
                    if hasattr(self, 'progress_frame'):
                        saved = message.get('saved_records', 0)
                        not_saved = message.get('files_not_saved', 0)
                        errors = message.get('total_errors', 0)
                        self.progress_frame.update_stats(saved, not_saved, errors)
                elif message_type == 'update_url':
                    if hasattr(self, 'progress_frame'):
                        self.progress_frame.update_url(message)
                elif message_type == 'update_processing':
                    if hasattr(self, 'progress_frame'):
                        self.progress_frame.update_processing_text(f"Tabulados {message}")
                elif message_type == 'update_searching':
                    if hasattr(self, 'progress_frame'):
                        self.progress_frame.update_searching_text(message)
                elif message_type == 'update_tabulating':
                    if hasattr(self, 'progress_frame'):
                        self.progress_frame.update_processing_text(message)
                elif message_type == 'log':
                    if hasattr(self, 'results_frame'):
                        self.results_frame.add_log(message)
                elif message_type == 'add_server':
                    # Añadir servidor a la lista si no está ya presente
                    if message not in self.server_listbox.get(0, tk.END):
                        self.server_listbox.insert(tk.END, message)
                        logger.info(f"Servidor descubierto: {message}")
        
        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"Error procesando cola: {e}")
        finally:
            # Programar siguiente verificación de cola
            self.master.after(200, self.process_queue)
