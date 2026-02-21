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
from gui.search_config_tab import SearchConfigTab
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
        self.is_closing = False  # Fix: inicializar bandera de cierre para _update_status_loop
        print("ScraperGUI inicializado")
        
        self.proxy_manager = ProxyManager()
        
        # Determinar la ruta de configuración persistente
        if getattr(sys, 'frozen', False):
            # Si estamos corriendo como ejecutable (PyInstaller), usar el directorio del exe
            base_path = os.path.dirname(sys.executable)
        else:
            # Si estamos en desarrollo, usar la carpeta client del proyecto
            base_path = os.path.join(project_root, 'client')
            
        config_path = os.path.join(base_path, 'config.json')
        logger.info(f"Usando archivo de configuración en: {config_path}")
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
        """Configura los componentes de la interfaz de usuario con un diseño lógico y dinámico."""
        import socket
        computer_name = socket.gethostname()
        self.master.title(f"Europa Scraper v3 (CON MONITOR) - {computer_name}")
        self.master.geometry("1450x900") # Tamaño inicial generoso
        self.master.minsize(1100, 750)
        self.master.configure(background="#f0f0f0")
        
        # Estilos modernos
        style = ttk.Style()
        style.configure("Heading.TLabel", font=("Arial", 16, "bold"))
        style.configure("Timer.TLabel", font=("Consolas", 14, "bold"), foreground="black", background="#e0e0e0")
        style.configure("Accent.TButton", font=("Arial", 10, "bold"))
        
        # --- SISTEMA DE PESTAÑAS ---
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.main_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.main_frame, text="Principal")
        
        # Pestaña Monitor de Estado Expandido (al lado de Principal)
        self.monitor_expanded_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.monitor_expanded_tab, text="📊 Monitor de Estado")
        
        self._create_server_config_tab()
        self.config_tab = ConfigTab(self.notebook, self.config)
        self.search_config_tab = SearchConfigTab(self.notebook, self.config)
        
        # Inicializar la pestaña de Monitor Expandido
        self._setup_expanded_monitor_tab()

        # === ESTILO VERDE BRILLANTE PARA BARRA DE PROGRESO ===
        style.configure("Green.Horizontal.TProgressbar", 
                        troughcolor='#e0e0e0', 
                        background='#00ff00',  # Verde encendido
                        lightcolor='#00ff00',
                        darkcolor='#00cc00')
        
        # === MONITOR DE ESTADO INTEGRADO EN LA PARTE SUPERIOR ===
        # Crear el monitor de estado como parte del main_frame (no como pestaña separada)
        self.status_monitor_frame = ttk.LabelFrame(self.main_frame, text="📊 Monitor de Estado del Sistema", padding="5")
        self.status_monitor_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Fila 1: Estado y Progreso
        self.monitor_top_frame = ttk.Frame(self.status_monitor_frame)
        self.monitor_top_frame.pack(fill=tk.X, pady=2)
        
        # Indicador de estado
        self.status_indicator_label = ttk.Label(
            self.monitor_top_frame, 
            text="● INACTIVO", 
            font=("Arial", 14, "bold"),
            foreground="gray"
        )
        self.status_indicator_label.pack(side=tk.LEFT, padx=10)
        
        # Mensaje de estado
        self.status_msg_label = ttk.Label(
            self.monitor_top_frame,
            text="Sistema listo para iniciar",
            font=("Arial", 10)
        )
        self.status_msg_label.pack(side=tk.LEFT, padx=10)
        
        # Barra de progreso verde
        self.main_progress_var = tk.DoubleVar(value=0)
        self.main_progress_bar = ttk.Progressbar(
            self.monitor_top_frame, 
            variable=self.main_progress_var,
            maximum=100,
            mode='determinate',
            length=300,
            style="Green.Horizontal.TProgressbar"
        )
        self.main_progress_bar.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Etiqueta de porcentaje
        self.main_progress_label = ttk.Label(
            self.monitor_top_frame,
            text="0%",
            font=("Arial", 10, "bold"),
            width=6
        )
        self.main_progress_label.pack(side=tk.LEFT, padx=5)
        
        # Fila 2: Estadísticas rápidas
        self.monitor_stats_frame = ttk.Frame(self.status_monitor_frame)
        self.monitor_stats_frame.pack(fill=tk.X, pady=2)
        
        self.stat_completed = ttk.Label(self.monitor_stats_frame, text="✅ Completados: 0", font=("Arial", 9))
        self.stat_completed.pack(side=tk.LEFT, padx=15)
        
        self.stat_pending = ttk.Label(self.monitor_stats_frame, text="⏳ Pendientes: 0", font=("Arial", 9))
        self.stat_pending.pack(side=tk.LEFT, padx=15)
        
        self.stat_failed = ttk.Label(self.monitor_stats_frame, text="❌ Fallidos: 0", font=("Arial", 9), foreground="red")
        self.stat_failed.pack(side=tk.LEFT, padx=15)
        
        # Fila 3: Log detallado con colores (colapsable)
        self.log_toggle_frame = ttk.Frame(self.status_monitor_frame)
        self.log_toggle_frame.pack(fill=tk.X, pady=2)
        
        self.log_visible = tk.BooleanVar(value=False)
        self.log_toggle_btn = ttk.Checkbutton(
            self.log_toggle_frame, 
            text="📋 Mostrar Log Detallado", 
            variable=self.log_visible,
            command=self._toggle_log_panel
        )
        self.log_toggle_btn.pack(side=tk.LEFT, padx=5)
        
        # Panel de log (inicialmente oculto)
        self.log_panel_frame = ttk.Frame(self.status_monitor_frame)
        # No se hace pack aquí, se controla con _toggle_log_panel
        
        self.detailed_log_text = tk.Text(
            self.log_panel_frame, 
            font=("Consolas", 9), 
            height=6, 
            wrap=tk.WORD,
            bg="#1e1e1e",  # Fondo oscuro
            fg="#ffffff",   # Texto blanco
            insertbackground="white"
        )
        self.detailed_log_scrollbar = ttk.Scrollbar(self.log_panel_frame, orient=tk.VERTICAL, command=self.detailed_log_text.yview)
        self.detailed_log_text.configure(yscrollcommand=self.detailed_log_scrollbar.set)
        
        # Tags para colores del log
        self.detailed_log_text.tag_configure('ERROR', foreground='#ff4444', background='#330000')    # Rojo
        self.detailed_log_text.tag_configure('WARNING', foreground='#ffaa00', background='#332200')  # Naranja
        self.detailed_log_text.tag_configure('SUCCESS', foreground='#00ff00', background='#003300')  # Verde
        self.detailed_log_text.tag_configure('INFO', foreground='#00aaff', background='#001133')     # Azul
        
        # Inicializar el StatusMonitorTab para compatibilidad (interno, no visible como pestaña)
        self.status_monitor_tab = StatusMonitorTab(None, self)
        self.status_monitor_tab.frame = self.status_monitor_frame  # Referencia al frame integrado
        
        # PanedWindow Horizontal Maestro (SIC | MONITOR+DETALLES | RESULTADOS) - REDIMENSIONABLE
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        self.left_column = ttk.Frame(self.paned_window)
        self.center_column = ttk.Frame(self.paned_window)
        self.right_column = ttk.Frame(self.paned_window)
        
        self.paned_window.add(self.left_column, weight=3)   # SIC - más estrecho
        self.paned_window.add(self.center_column, weight=5) # Monitor/Detalles
        self.paned_window.add(self.right_column, weight=4)  # Resultados
        
        # --- COLUMNA IZQUIERDA (SELECCIÓN DE CÓDIGOS) ---
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
        self.from_sic_listbox = tk.Listbox(self.sic_listbox_frame, exportselection=False, font=("TkDefaultFont", 11))
        self.from_sic_scrollbar = ttk.Scrollbar(self.sic_listbox_frame, orient=tk.VERTICAL, command=self.from_sic_listbox.yview)
        self.from_sic_listbox.configure(yscrollcommand=self.from_sic_scrollbar.set)
        self.from_sic_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.from_sic_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.from_sic_listbox.bind('<<ListboxSelect>>', self._on_from_sic_select)
        
        self.to_sic_listbox = tk.Listbox(self.sic_listbox_frame, exportselection=False, font=("TkDefaultFont", 11))
        self.to_sic_scrollbar = ttk.Scrollbar(self.sic_listbox_frame, orient=tk.VERTICAL, command=self.to_sic_listbox.yview)
        self.to_sic_listbox.configure(yscrollcommand=self.to_sic_scrollbar.set)
        self.to_sic_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.to_sic_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.to_sic_listbox.bind('<<ListboxSelect>>', self._on_to_sic_select)

        # --- COLUMNA CENTRAL (DIBUJAMOS DE ARRIBA Y ABAJO HACIA EL CENTRO) ---
        # 1. Cabecera (ARRIBA)
        self.header_frame = ttk.Frame(self.center_column)
        self.header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        self.title_label = ttk.Label(self.header_frame, text=f"Europa Scraper - {computer_name}", style="Heading.TLabel")
        self.title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.timer_label = ttk.Label(self.header_frame, text="Tiempo: 00:00:00", style="Timer.TLabel")
        self.timer_label.pack(side=tk.RIGHT, padx=10)
        
        self.load_courses_button = ttk.Button(
            self.center_column, 
            text="📁 CARGAR CURSOS (CSV/XLS)", 
            command=self._upload_courses_file, 
            style="Accent.TButton"
        )
        self.load_courses_button.pack(side=tk.TOP, fill=tk.X, pady=5, ipadx=10, ipady=10)

        # 2. Controles (ABAJO DEL TODO)
        self.control_frame = ControlFrame(self.center_column, on_start=self._on_start_scraping, on_stop=self._on_stop_scraping)
        self.control_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        self.engine_frame = ttk.Frame(self.center_column)
        self.engine_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        ttk.Label(self.engine_frame, text="Motor de Búsqueda:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_engine_var = tk.StringVar(value="Cordis Europa API")
        engine_values = ["Cordis Europa API", "Cordis Europa", "Google", "DuckDuckGo", "Common Crawl", "Wayback Machine"]
        self.search_engine_combo = ttk.Combobox(self.engine_frame, textvariable=self.search_engine_var, values=engine_values, state="readonly")
        self.search_engine_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ProgressFrame oculto pero necesario internamente
        self.progress_frame = ProgressFrame(self.center_column)

        # 3. PANED WINDOW VERTICAL MAESTRO (MONITOR vs DETALLES)
        self.center_master_paned = ttk.PanedWindow(self.center_column, orient=tk.VERTICAL)
        self.center_master_paned.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=10)

        # SECCIÓN 1: MONITOR ÁREA (WORKERS + AUDITORÍA) - MÁS ALTURA
        self.monitor_area = ttk.LabelFrame(self.center_master_paned, text="Monitor de Actividad Local", padding=5)
        self.center_master_paned.add(self.monitor_area, weight=5)

        # Botones del Monitor
        self.mon_btn_frame = ttk.Frame(self.monitor_area)
        self.mon_btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=2)
        ttk.Button(self.mon_btn_frame, text="Ver Detalles de Worker", command=self._show_worker_details).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # BOTON DE CURSOS FALLIDOS - BOTON ROJO GRANDE Y VISIBLE
        print("=" * 60)
        print("✅✅✅ BOTON 'VER CURSOS FALLIDOS' AGREGADO - VERSION CON DEBUG")
        print("=" * 60)
        
        # Crear un estilo especial para el botón de cursos fallidos
        style = ttk.Style()
        style.configure("FailedCourses.TButton", font=("Arial", 11, "bold"))
        
        btn_failed = ttk.Button(self.mon_btn_frame, text="❌ CURSOS FALLIDOS", 
                                command=self._show_failed_courses, style="FailedCourses.TButton")
        btn_failed.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        ttk.Button(self.mon_btn_frame, text="⚠️ Resetear Sistema (Emergencia)", command=self._force_reset_client_state).pack(side=tk.RIGHT, padx=5, expand=True, fill=tk.X)

        # PanedWindow solo para tener formato si se quiere, o usar un Frame simple
        self.workers_pane = ttk.Frame(self.monitor_area)
        self.workers_pane.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Workers Tree (Ahora es el Monitor de Cursos)
        self.worker_tree = ttk.Treeview(self.workers_pane, columns=('SIC', 'Status', 'Course', 'Progress'), show='headings')
        for col in ('SIC', 'Status', 'Course', 'Progress'):
            self.worker_tree.heading(col, text=col)
        self.worker_tree.column('SIC', width=70, anchor=tk.CENTER)
        self.worker_tree.column('Status', width=120)
        self.worker_tree.column('Course', width=350)
        self.worker_tree.column('Progress', width=80, anchor=tk.CENTER)
        self.worker_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb1 = ttk.Scrollbar(self.workers_pane, orient=tk.VERTICAL, command=self.worker_tree.yview)
        self.worker_tree.configure(yscrollcommand=sb1.set)
        sb1.pack(side=tk.RIGHT, fill=tk.Y)

        # Tags y Bindings
        self.worker_tree.bind("<Button-3>", self._show_context_menu)
        self.worker_tree.bind('<<TreeviewSelect>>', self._on_course_select_sync_worker)
        
        # --- COLUMNA DERECHA (AUDITORÍA, DETALLES Y RESULTADOS) ---
        self.right_paned = ttk.PanedWindow(self.right_column, orient=tk.VERTICAL)
        self.right_paned.pack(fill=tk.BOTH, expand=True)
        
        # 1. Auditoría Tree (Historial Técnico) - ESTRUCTURA JERÁRQUICA
        self.audit_pane = ttk.LabelFrame(self.right_paned, text="Auditoría de Procesos (por Worker)", padding=5)
        self.right_paned.add(self.audit_pane, weight=2)
        
        # TreeView jerárquico: Workers como padres, eventos como hijos
        self.audit_tree = ttk.Treeview(self.audit_pane, columns=('Time', 'Type', 'Message'), show='tree headings')
        self.audit_tree.heading('#0', text='Worker')
        self.audit_tree.heading('Time', text='Hora')
        self.audit_tree.heading('Type', text='Tipo')
        self.audit_tree.heading('Message', text='Mensaje')
        
        # Columna #0 (Worker) más ancha para ver el nombre
        self.audit_tree.column('#0', width=100, anchor=tk.W)
        self.audit_tree.column('Time', width=70, anchor=tk.CENTER)
        self.audit_tree.column('Type', width=80, anchor=tk.CENTER)
        self.audit_tree.column('Message', width=350, anchor=tk.W)
        
        self.audit_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb2 = ttk.Scrollbar(self.audit_pane, orient=tk.VERTICAL, command=self.audit_tree.yview)
        self.audit_tree.configure(yscrollcommand=sb2.set)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tags para tipos de eventos
        self.audit_tree.tag_configure('ERROR', foreground='white', background='#d32f2f')
        self.audit_tree.tag_configure('WARNING', foreground='black', background='#fbc02d')
        self.audit_tree.tag_configure('SUCCESS', foreground='white', background='#388e3c')
        self.audit_tree.tag_configure('SCRAPER', foreground='blue')
        self.audit_tree.tag_configure('SYSTEM', foreground='gray')
        self.audit_tree.tag_configure('INFO', foreground='black')
        # Tags para nodos padre (workers)
        self.audit_tree.tag_configure('worker_node', font=('Arial', 10, 'bold'))
        
        self.audit_tree.bind('<<TreeviewSelect>>', self._on_audit_select)
        self.audit_tree.bind("<Button-3>", self._show_context_menu)
        
        # Diccionario para tracking de workers y sus eventos
        self.audit_worker_nodes = {}  # worker_id -> node_id en el tree

        # 2. DETALLES DEL PROCESO SELECCIONADO (AHORA A LA DERECHA, DEBAJO DE AUDITORÍA)
        self.details_area = ttk.LabelFrame(self.right_paned, text="Detalles del Proceso Seleccionado", padding=5)
        self.right_paned.add(self.details_area, weight=1)
        
        # Frame contenedor con scrollbar
        self.details_container = ttk.Frame(self.details_area)
        self.details_container.pack(fill=tk.BOTH, expand=True)
        
        self.details_text = tk.Text(self.details_container, font=("Consolas", 10), state=tk.DISABLED, bg="#f5f5f5", height=6, wrap=tk.WORD)
        self.details_scrollbar = ttk.Scrollbar(self.details_container, orient=tk.VERTICAL, command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=self.details_scrollbar.set)
        
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 3. Resultados (solo botones, sin área de texto redundante)
        self.results_container = ttk.LabelFrame(self.right_paned, text="Acciones de Resultados", padding=5)
        self.right_paned.add(self.results_container, weight=0)
        
        # Botones de acciones
        self.results_btns = ttk.Frame(self.results_container)
        self.results_btns.pack(fill=tk.X, pady=5)
        ttk.Button(self.results_btns, text="📥 Exportar ZIP", command=self._on_export_results).pack(side=tk.LEFT, padx=2, pady=2, fill=tk.X, expand=True)
        ttk.Button(self.results_btns, text="📂 Ver Archivos", command=self._on_open_results_folder).pack(side=tk.LEFT, padx=2, pady=2, fill=tk.X, expand=True)
        ttk.Button(self.results_btns, text="🗑️ Limpiar", command=self._cleanup_files_action).pack(side=tk.LEFT, padx=2, pady=2, fill=tk.X, expand=True)
        
        # ResultsFrame eliminado - su función de log ahora está en el Monitor de Estado
        # Mantenemos una referencia dummy para compatibilidad con código existente
        self.results_frame = DummyResultsFrame()
        self.results_frame.set_gui(self)

        # Ajuste final de sashes
        self.paned_window.update()
        w = self.paned_window.winfo_width()
        if w > 0:
            self.paned_window.sashpos(0, int(w * 0.30))
            self.paned_window.sashpos(1, int(w * 0.70))

    def _create_server_config_tab(self):
        """Crea la pestaña de configuración del servidor"""
        self.server_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.server_frame, text="Configuración del Servidor")
        
        config_frame = ttk.LabelFrame(self.server_frame, text="Configuración de Conexión", padding=10)
        config_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(config_frame, text="URL del Servidor:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        current_url = self.config.get('server_url', "https://scraper.docuplay.com")
        # Mantener scraper.docuplay.com como predeterminado para el túnel de Cloudflare.
            
        self.server_url = tk.StringVar(value=current_url)
        self.server_url_entry = ttk.Entry(config_frame, textvariable=self.server_url, width=50)
        self.server_url_entry.grid(row=0, column=1, padx=10, pady=5, sticky=tk.EW)
        
        # Guardar URL automáticamente al cambiar
        self.server_url.trace_add("write", lambda *args: self.config.set('server_url', self.server_url.get()))
        
        self.connect_button = ttk.Button(config_frame, text="Conectar / Refrescar", command=self._connect_to_server_threaded)
        self.connect_button.grid(row=2, column=1, padx=10, pady=20, sticky=tk.E)
        
        self.connection_status_label = ttk.Label(config_frame, text="Desconectado", foreground="red")
        self.connection_status_label.grid(row=3, column=1, padx=10, sticky=tk.E)
        
        config_frame.columnconfigure(1, weight=1)
    
    def _setup_expanded_monitor_tab(self):
        """Crea la pestaña de Monitor de Estado Expandido con toda la información detallada."""
        # === PANED WINDOW VERTICAL PARA DIVIDIR SECCIONES ===
        self.expanded_paned = ttk.PanedWindow(self.monitor_expanded_tab, orient=tk.VERTICAL)
        self.expanded_paned.pack(fill=tk.BOTH, expand=True)
        
        # === SECCIÓN 1: ESTADO GENERAL Y PROGRESO (ARRIBA) ===
        top_frame = ttk.Frame(self.expanded_paned)
        self.expanded_paned.add(top_frame, weight=1)
        
        # Estado del Sistema
        status_frame = ttk.LabelFrame(top_frame, text="Estado del Sistema", padding="10")
        status_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Indicador de estado grande
        self.expanded_status_label = ttk.Label(
            status_frame, 
            text="● INACTIVO", 
            font=("Arial", 24, "bold"),
            foreground="gray"
        )
        self.expanded_status_label.pack(side=tk.LEFT, padx=20)
        
        # Mensaje de estado
        self.expanded_status_msg = ttk.Label(
            status_frame,
            text="Sistema listo para iniciar",
            font=("Arial", 14)
        )
        self.expanded_status_msg.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)
        
        # Progreso General con barra verde
        progress_frame = ttk.LabelFrame(top_frame, text="Progreso General", padding="10")
        progress_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Barra de progreso verde grande
        self.expanded_progress_var = tk.DoubleVar(value=0)
        self.expanded_progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.expanded_progress_var,
            maximum=100,
            mode='determinate',
            length=600,
            style="Green.Horizontal.TProgressbar"
        )
        self.expanded_progress_bar.pack(fill=tk.X, pady=5)
        
        # Etiqueta de porcentaje grande
        self.expanded_progress_label = ttk.Label(
            progress_frame,
            text="0% - Sin progreso",
            font=("Arial", 16, "bold")
        )
        self.expanded_progress_label.pack()
        
        # Estadísticas detalladas
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.pack(fill=tk.X, pady=10)
        
        self.exp_stat_completed = ttk.Label(stats_frame, text="✅ Completados: 0", font=("Arial", 12))
        self.exp_stat_completed.pack(side=tk.LEFT, padx=20)
        
        self.exp_stat_pending = ttk.Label(stats_frame, text="⏳ Pendientes: 0", font=("Arial", 12))
        self.exp_stat_pending.pack(side=tk.LEFT, padx=20)
        
        self.exp_stat_failed = ttk.Label(stats_frame, text="❌ Fallidos: 0", font=("Arial", 12), foreground="red")
        self.exp_stat_failed.pack(side=tk.LEFT, padx=20)
        
        self.exp_stat_in_progress = ttk.Label(stats_frame, text="🔄 En Progreso: 0", font=("Arial", 12), foreground="blue")
        self.exp_stat_in_progress.pack(side=tk.LEFT, padx=20)
        
        # === SECCIÓN 2: ERRORES CRÍTICOS (CENTRO) ===
        errors_frame = ttk.LabelFrame(self.expanded_paned, text="⚠️ Errores Críticos", padding="10")
        self.expanded_paned.add(errors_frame, weight=1)
        
        # Lista de errores con scrollbar
        errors_container = ttk.Frame(errors_frame)
        errors_container.pack(fill=tk.BOTH, expand=True)
        
        self.expanded_errors_text = tk.Text(
            errors_container, 
            font=("Consolas", 11), 
            height=8, 
            wrap=tk.WORD,
            bg="#1e1e1e",
            fg="#ff4444",
            insertbackground="white"
        )
        self.expanded_errors_scrollbar = ttk.Scrollbar(errors_container, orient=tk.VERTICAL, command=self.expanded_errors_text.yview)
        self.expanded_errors_text.configure(yscrollcommand=self.expanded_errors_scrollbar.set)
        
        self.expanded_errors_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.expanded_errors_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.expanded_errors_text.insert(tk.END, "No hay errores críticos registrados.\n")
        self.expanded_errors_text.config(state=tk.DISABLED)
        
        # Botón para limpiar errores
        ttk.Button(errors_frame, text="🗑️ Limpiar Errores", command=self._clear_expanded_errors).pack(pady=5)
        
        # === SECCIÓN 3: LOG DETALLADO CON COLORES (ABAJO) ===
        log_frame = ttk.LabelFrame(self.expanded_paned, text="📋 Log Detallado del Proceso", padding="10")
        self.expanded_paned.add(log_frame, weight=2)
        
        # Área de log con scrollbar
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        self.expanded_log_text = tk.Text(
            log_container, 
            font=("Consolas", 10), 
            height=15, 
            wrap=tk.WORD,
            bg="#1e1e1e",  # Fondo oscuro
            fg="#ffffff",   # Texto blanco
            insertbackground="white"
        )
        self.expanded_log_scrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL, command=self.expanded_log_text.yview)
        self.expanded_log_text.configure(yscrollcommand=self.expanded_log_scrollbar.set)
        
        self.expanded_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.expanded_log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configurar tags para colores
        self.expanded_log_text.tag_configure('ERROR', foreground='#ff4444', background='#330000')    # Rojo
        self.expanded_log_text.tag_configure('WARNING', foreground='#ffaa00', background='#332200')  # Naranja
        self.expanded_log_text.tag_configure('SUCCESS', foreground='#00ff00', background='#003300')  # Verde
        self.expanded_log_text.tag_configure('INFO', foreground='#00aaff', background='#001133')     # Azul
        
        # Botones de control
        btn_frame = ttk.Frame(log_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="🗑️ Limpiar Log", command=self._clear_expanded_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📋 Copiar Log", command=self._copy_expanded_log).pack(side=tk.LEFT, padx=5)
    
    def _clear_expanded_errors(self):
        """Limpia la lista de errores en la pestaña expandida."""
        self.expanded_errors_text.config(state=tk.NORMAL)
        self.expanded_errors_text.delete(1.0, tk.END)
        self.expanded_errors_text.insert(tk.END, "No hay errores críticos registrados.\n")
        self.expanded_errors_text.config(state=tk.DISABLED)
    
    def _clear_expanded_log(self):
        """Limpia el log en la pestaña expandida."""
        self.expanded_log_text.delete(1.0, tk.END)
    
    def _copy_expanded_log(self):
        """Copia el log de la pestaña expandida al portapapeles."""
        log_content = self.expanded_log_text.get(1.0, tk.END)
        self.monitor_expanded_tab.clipboard_clear()
        self.monitor_expanded_tab.clipboard_append(log_content)
        messagebox.showinfo("Copiado", "Log copiado al portapapeles.")

    def _start_status_polling(self):
        """Este método ahora es manejado externamente por la ClientApp."""
        pass

    def _on_tree_select(self, event):
        """Muestra los detalles completos del worker seleccionado."""
        selection = self.worker_tree.selection()
        if not selection: return
        row_id = selection[0]
        full_details = getattr(self, 'row_details_map', {}).get(row_id, "Sin detalles.")
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, full_details)
        self.details_text.config(state=tk.DISABLED)

    def _on_course_select_sync_worker(self, event):
        """
        Cuando se selecciona un curso en el Monitor de Actividad Local,
        busca y resalta el worker correspondiente en la Auditoría de Procesos.
        """
        selection = self.worker_tree.selection()
        if not selection:
            return
        
        row_id = selection[0]
        
        # Obtener los valores del curso seleccionado directamente del tree
        item_values = self.worker_tree.item(row_id, 'values')
        if not item_values or len(item_values) < 3:
            return
        
        # Los valores son: (SIC, Status, Course, Progress)
        sic_code = str(item_values[0])  # SIC code
        course_name = str(item_values[2]) if len(item_values) > 2 else ""  # Course name
        
        print(f"DEBUG: Seleccionado curso SIC={sic_code}, Nombre={course_name}")
        
        # Buscar en los eventos de auditoría qué worker procesó este curso
        worker_to_highlight = None
        
        # Método 1: Buscar en los mensajes compilados de cada worker
        if hasattr(self, 'worker_messages'):
            for worker_key, messages in self.worker_messages.items():
                for msg in messages:
                    # Buscar si el mensaje menciona el SIC o el nombre del curso
                    if sic_code in msg or (course_name and course_name[:30] in msg):
                        worker_to_highlight = worker_key
                        print(f"DEBUG: Encontrado worker {worker_key} por mensaje: {msg[:50]}")
                        break
                if worker_to_highlight:
                    break
        
        # Método 2: Buscar en los nodos hijos de cada worker en el árbol
        if not worker_to_highlight and hasattr(self, 'audit_worker_nodes'):
            for worker_key, node_id in self.audit_worker_nodes.items():
                if self.audit_tree.exists(node_id):
                    children = self.audit_tree.get_children(node_id)
                    for child in children:
                        values = self.audit_tree.item(child, 'values')
                        if values and len(values) >= 3:
                            msg = str(values[2])  # Columna Message
                            if sic_code in msg or (course_name and course_name[:30] in msg):
                                worker_to_highlight = worker_key
                                print(f"DEBUG: Encontrado worker {worker_key} por árbol: {msg[:50]}")
                                break
                if worker_to_highlight:
                    break
        
        # Resaltar el worker encontrado
        if worker_to_highlight and hasattr(self, 'audit_worker_nodes'):
            node_id = self.audit_worker_nodes.get(worker_to_highlight)
            if node_id and self.audit_tree.exists(node_id):
                # NO expandir el nodo - solo seleccionarlo e iluminarlo
                # self.audit_tree.item(node_id, open=True)  # Comentado: no expandir
                
                # Seleccionar el nodo del worker
                self.audit_tree.selection_set(node_id)
                self.audit_tree.see(node_id)
                
                # Resaltar visualmente (cambiar fondo temporalmente)
                self.audit_tree.tag_configure('highlighted', background='#ffeb3b')  # Amarillo
                self.audit_tree.item(node_id, tags=('highlighted', 'worker_node'))
                
                # Quitar el resaltado después de 3 segundos
                self.master.after(3000, lambda nid=node_id: self._remove_highlight(nid))
                
                # Actualizar el panel de detalles
                self._on_audit_select(None)
                
                print(f"DEBUG: Worker {worker_to_highlight} resaltado correctamente")
        else:
            print(f"DEBUG: No se encontró worker para SIC={sic_code}")

    def _remove_highlight(self, node_id):
        """Quita el resaltado de un nodo del árbol de auditoría."""
        if self.audit_tree.exists(node_id):
            self.audit_tree.item(node_id, tags=('worker_node',))
    
    def _update_status_monitor(self, workers, courses):
        """Actualiza el Monitor de Estado en AMBAS pestañas (Principal y Expandida)."""
        # Calcular estadísticas
        total_courses = len(courses)
        completed = sum(1 for c in courses if c.get('status') == 'Completado')
        pending = sum(1 for c in courses if c.get('status') == 'Pendiente')
        failed = sum(1 for c in courses if c.get('status') in ['Error', 'Fallido'])
        in_progress = sum(1 for c in courses if c.get('status') == 'En progreso')
        
        # Calcular progreso promedio
        if total_courses > 0:
            avg_progress = sum(c.get('progress', 0) for c in courses) / total_courses
        else:
            avg_progress = 0
        
        # Determinar estado del sistema
        active_workers = 0
        if isinstance(workers, dict):
            active_workers = sum(1 for w in workers.values() if w.get('status') not in ['Idle', 'Error'])
        
        if active_workers > 0 or in_progress > 0:
            status = "ACTIVO"
            message = f"Procesando {in_progress} cursos con {active_workers} workers activos"
        elif failed > 0 and completed + failed == total_courses:
            status = "DETENIDO"
            message = f"Proceso terminado con {failed} errores"
        elif completed == total_courses and total_courses > 0:
            status = "DETENIDO"
            message = "Proceso completado exitosamente"
        else:
            status = "INACTIVO"
            message = "Sistema listo para iniciar"
        
        # === ACTUALIZAR PESTAÑA PRINCIPAL ===
        # Actualizar indicador de estado
        if status == "ACTIVO":
            self.status_indicator_label.config(text="● ACTIVO", foreground="#00ff00")  # Verde brillante
        elif status == "DETENIDO":
            self.status_indicator_label.config(text="● DETENIDO", foreground="#ff4444")  # Rojo
        else:
            self.status_indicator_label.config(text="● INACTIVO", foreground="gray")
        
        # Actualizar mensaje
        self.status_msg_label.config(text=message)
        
        # Actualizar barra de progreso verde (Principal)
        self.main_progress_var.set(avg_progress)
        self.main_progress_label.config(text=f"{avg_progress:.0f}%")
        
        # Actualizar estadísticas (Principal)
        self.stat_completed.config(text=f"✅ Completados: {completed}")
        self.stat_pending.config(text=f"⏳ Pendientes: {pending}")
        self.stat_failed.config(text=f"❌ Fallidos: {failed}")
        
        # === ACTUALIZAR PESTAÑA MONITOR EXPANDIDO ===
        if hasattr(self, 'expanded_status_label'):
            # Estado
            if status == "ACTIVO":
                self.expanded_status_label.config(text="● ACTIVO", foreground="#00ff00")
            elif status == "DETENIDO":
                self.expanded_status_label.config(text="● DETENIDO", foreground="#ff4444")
            else:
                self.expanded_status_label.config(text="● INACTIVO", foreground="gray")
            
            # Mensaje
            self.expanded_status_msg.config(text=message)
            
            # Barra de progreso verde (Expandido)
            self.expanded_progress_var.set(avg_progress)
            self.expanded_progress_label.config(text=f"{avg_progress:.1f}% - {message}")
            
            # Estadísticas detalladas (Expandido)
            self.exp_stat_completed.config(text=f"✅ Completados: {completed}")
            self.exp_stat_pending.config(text=f"⏳ Pendientes: {pending}")
            self.exp_stat_failed.config(text=f"❌ Fallidos: {failed}")
            self.exp_stat_in_progress.config(text=f"🔄 En Progreso: {in_progress}")
        
        # Agregar entrada al log detallado si hay actividad significativa
        if not hasattr(self, 'last_logged_progress'):
            self.last_logged_progress = 0
        
        if status == "ACTIVO" and avg_progress - self.last_logged_progress >= 5:
            self._add_to_detailed_log(f"Progreso: {avg_progress:.1f}% - {completed}/{total_courses} cursos", "INFO")
            self.last_logged_progress = avg_progress
        
        # También actualizar el status_monitor_tab para compatibilidad
        if hasattr(self, 'status_monitor_tab') and self.status_monitor_tab:
            self.status_monitor_tab.update_status(status, message, avg_progress)
            self.status_monitor_tab.update_stats(completed, pending, failed)

    def _render_status(self, workers, courses):
        """Renderiza el estado dinámico de los cursos en el Monitor Principal."""
        # Mantener un diccionario para los detalles del panel inferior
        if not hasattr(self, 'row_details_map'): self.row_details_map = {}
        
        # 1. Renderizar Cursos (La nueva vista principal)
        # Formato de data de courses del server: list of dicts: [{'sic':'01.0', 'name':'...', 'status':'...', 'progress':X}, ...]
        if isinstance(courses, dict):
             # Por si viene como dict
             courses_list = courses.values()
        else:
             courses_list = courses
              
        for c in courses_list:
             sic = c.get('sic', 'N/A')
             name = c.get('name', 'N/A')
             status = c.get('status', 'Pendiente')
             progress = int(c.get('progress', 0))
              
             row_id = f"course_{sic.replace('.', '_')}"
             vals = (sic, status.capitalize(), name, f"{progress}%")
              
             self.row_details_map[row_id] = f"Curso: {sic} - {name}\nEstado Actual: {status}\nProgreso: {progress}%"
              
             if self.worker_tree.exists(row_id):
                  self.worker_tree.item(row_id, values=vals)
             else:
                  self.worker_tree.insert('', 'end', iid=row_id, values=vals)

        # 2. Agregar mensajes de los workers si están atascados o iniciando (opcional, solo para feedback transitorio)
        # Limpiamos los transitorios primero
        for item in self.worker_tree.get_children():
            if item.startswith("worker_msg_"):
                self.worker_tree.delete(item)
                
        if isinstance(workers, dict):
            for wid, state in workers.items():
                if state.get('status') in ['Idle', 'Error'] or state.get('progress', 0) == 0:
                    raw_task = state.get('current_task', '')
                    if "Iniciando" in raw_task or "Esperando" in raw_task or "CRASHED" in raw_task:
                        row_id = f"worker_msg_{wid}"
                        vals = ("--", state.get('status', '').capitalize(), f"Worker {wid}: {raw_task}", "--")
                        self.row_details_map[row_id] = f"Detalles de Trabajador {wid}:\nEstado: {state.get('status')}\nTarea: {raw_task}"
                        self.worker_tree.insert('', 'end', iid=row_id, values=vals)

        # Progreso general
        if courses_list:
            active_or_done = [c for c in courses_list if c.get('status') != 'Pendiente']
            if active_or_done:
                # El promedio es la suma de los progresos dividido por el TOTAL de cursos (para que llegue a 100% solo al final)
                avg = sum(c.get('progress', 0) for c in courses_list) / len(courses_list)
                self.progress_frame.update_progress(avg, f"General: {avg:.1f}%")
            else:
                self.progress_frame.update_progress(0, "Inactivo")
        elif workers:
             active_workers = [w for w in (workers.values() if isinstance(workers, dict) else workers) if w.get('status') != 'Idle']
             if active_workers:
                 self.progress_frame.update_progress(0, "Iniciando...")
             else:
                 self.progress_frame.update_progress(100, "Inactivo")
        
        # === ACTUALIZAR MONITOR DE ESTADO ===
        self._update_status_monitor(workers, courses_list if isinstance(courses_list, list) else list(courses_list))

    def _get_worker_sort_key(self, source):
        """Extrae el número del worker para ordenamiento numérico.
        Ej: 'Worker-1' -> 1, 'Worker-10' -> 10, 'System' -> 9999
        """
        if not source:
            return 9999
        match = re.search(r'(\d+)', source)
        if match:
            return int(match.group(1))
        return 9999  # System u otros van al final

    def _reorder_worker_nodes(self):
        """Reordena los nodos de workers en el árbol numéricamente."""
        if not hasattr(self, 'audit_worker_nodes') or not self.audit_worker_nodes:
            return
        
        # Obtener todos los workers con su clave de ordenamiento
        workers_with_keys = []
        for worker_key, node_id in self.audit_worker_nodes.items():
            # Extraer el display name del nodo
            if self.audit_tree.exists(node_id):
                text = self.audit_tree.item(node_id, 'text')
                sort_key = self._get_worker_sort_key(text)
                workers_with_keys.append((sort_key, worker_key, node_id))
        
        # Ordenar por número de worker
        workers_with_keys.sort(key=lambda x: x[0])
        
        # Mover cada nodo a su posición correcta
        for idx, (sort_key, worker_key, node_id) in enumerate(workers_with_keys):
            if self.audit_tree.exists(node_id):
                # Mover el nodo a la posición idx
                self.audit_tree.move(node_id, '', idx)

    def update_audit_log(self, events):
        """Actualiza el historial de auditoría con estructura jerárquica por Worker."""
        if not hasattr(self, 'audit_details_map'): self.audit_details_map = {}
        if not hasattr(self, 'audit_worker_nodes'): self.audit_worker_nodes = {}
        
        needs_reorder = False
        
        for ev in events:
            event_id = ev.get('id')
            source = ev.get('source', 'System')
            ev_type = ev.get('type', 'INFO')
            timestamp = ev.get('timestamp', '')
            msg = ev.get('message', '')
            
            # Extraer el worker_id del source (ej: "Worker-1" -> "worker_1")
            worker_key = source.replace('-', '_').lower() if source else 'system'
            worker_display = source if source else 'System'
            
            # Crear nodo padre del worker si no existe
            if worker_key not in self.audit_worker_nodes:
                # Insertar nodo padre para este worker (COLAPSADO por defecto)
                node_id = self.audit_tree.insert('', 'end', text=worker_display, 
                                                   values=('', '', f'Eventos de {worker_display}'),
                                                   tags=('worker_node',), open=False)
                self.audit_worker_nodes[worker_key] = node_id
                # Inicializar lista de mensajes para este worker
                if not hasattr(self, 'worker_messages'):
                    self.worker_messages = {}
                self.worker_messages[worker_key] = []
                needs_reorder = True
            
            parent_node = self.audit_worker_nodes[worker_key]
            
            # Crear ID único para el evento
            row_id = f"ev_{event_id}"
            
            # Guardar detalles completos
            self.audit_details_map[row_id] = f"{timestamp}\n{msg}\n\n{json.dumps(ev.get('details', {}), indent=2)}"
            
            # Insertar evento como hijo del worker (solo si no existe)
            if not self.audit_tree.exists(row_id):
                self.audit_tree.insert(parent_node, 'end', iid=row_id, 
                                        text='',  # Sin texto en columna #0 para hijos
                                        values=(timestamp, ev_type, msg[:80]),  # Truncar mensaje
                                        tags=(ev_type,))
                
                # Agregar mensaje a la lista del worker para el compilado
                if hasattr(self, 'worker_messages') and worker_key in self.worker_messages:
                    # Formato: [TIMESTAMP] TIPO: Mensaje
                    formatted_msg = f"[{timestamp}] {ev_type}: {msg}"
                    self.worker_messages[worker_key].append(formatted_msg)
            
            # === AGREGAR AL LOG DETALLADO CON COLORES ===
            if hasattr(self, 'detailed_log_text'):
                log_level = ev_type if ev_type in ['ERROR', 'WARNING', 'SUCCESS', 'INFO'] else 'INFO'
                self._add_to_detailed_log(f"[{source}] {msg}", log_level)
        
        # Reordenar workers si se agregó uno nuevo
        if needs_reorder:
            self._reorder_worker_nodes()
        
        # Actualizar panel de detalles en tiempo real si hay un worker seleccionado
        self._update_details_if_worker_selected()

    def _on_audit_select(self, event):
        """Muestra detalles del elemento seleccionado.
        Si es un nodo worker (nivel cero), muestra el compilado de todos sus mensajes.
        Si es un evento hijo, muestra los detalles individuales.
        """
        sel = self.audit_tree.selection()
        if not sel:
            return
        
        selected_id = sel[0]
        
        # Verificar si es un nodo worker (nivel cero)
        # Los nodos worker tienen IDs como 'worker_1', 'worker_2', etc.
        # y están en audit_worker_nodes
        worker_key = None
        if hasattr(self, 'audit_worker_nodes'):
            for wk, node_id in self.audit_worker_nodes.items():
                if node_id == selected_id:
                    worker_key = wk
                    break
        
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        
        if worker_key and hasattr(self, 'worker_messages'):
            # Es un nodo worker - mostrar compilado de mensajes
            messages = self.worker_messages.get(worker_key, [])
            if messages:
                compiled = "\n".join(messages)
                # Obtener el nombre display del worker
                worker_display = self.audit_tree.item(selected_id, 'text')
                self.details_text.insert(tk.END, f"=== {worker_display} - Historial de Eventos ===\n\n{compiled}")
            else:
                self.details_text.insert(tk.END, "Sin eventos registrados aún.")
        else:
            # Es un evento hijo - mostrar detalles individuales
            txt = self.audit_details_map.get(selected_id, "Sin detalles disponibles.")
            self.details_text.insert(tk.END, txt)
        
        self.details_text.config(state=tk.DISABLED)
    
    def _update_details_if_worker_selected(self):
        """Actualiza el panel de detalles en tiempo real si un worker está seleccionado."""
        sel = self.audit_tree.selection()
        if not sel:
            return
        
        selected_id = sel[0]
        
        # Verificar si es un nodo worker
        worker_key = None
        if hasattr(self, 'audit_worker_nodes'):
            for wk, node_id in self.audit_worker_nodes.items():
                if node_id == selected_id:
                    worker_key = wk
                    break
        
        if worker_key and hasattr(self, 'worker_messages'):
            # Actualizar el panel de detalles con los mensajes actualizados
            messages = self.worker_messages.get(worker_key, [])
            if messages:
                compiled = "\n".join(messages)
                worker_display = self.audit_tree.item(selected_id, 'text')
                
                self.details_text.config(state=tk.NORMAL)
                self.details_text.delete(1.0, tk.END)
                self.details_text.insert(tk.END, f"=== {worker_display} - Historial de Eventos ===\n\n{compiled}")
                self.details_text.config(state=tk.DISABLED)

    def _upload_courses_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV/Excel", "*.csv *.xlsx")])
        if not filepath: return
        try:
            # Mostrar solo el nombre del archivo en el log
            import os
            fname = os.path.basename(filepath)
            self.results_frame.add_log(f"Subiendo {fname}...")
            with open(filepath, 'rb') as f:
                r = requests.post(f"{self.server_url.get()}/api/upload_courses", files={'file': f}, timeout=30)
            if r.status_code == 200:
                self._refresh_courses_from_server()
                messagebox.showinfo("OK", "Subido correctamente.")
            else:
                self.results_frame.add_log(f"❌ Fallo en subida: {r.text}")
                messagebox.showerror("Error", f"Fallo al subir: {r.status_code}")
        except Exception as e: 
            self.results_frame.add_log(f"❌ Error en subida: {str(e)}")
            messagebox.showerror("Err", str(e))

    def _refresh_courses_from_server(self, event=None):
        try:
            url = f"{self.server_url.get()}/api/get_all_courses"
            self.results_frame.add_log(f"Refrescando cursos desde el servidor...")
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                self.results_frame.add_log(f"✅ Recibidos {len(data)} cursos.")
                self._update_ui_with_loaded_courses(data)
            else:
                self.results_frame.add_log(f"❌ Error al refrescar cursos: Status {r.status_code}")
        except Exception as e:
            self.results_frame.add_log(f"❌ Excepción al refrescar cursos: {str(e)}")
            # No mostrar messagebox aquí para no interrumpir el flujo si falla el inicio

    def _update_ui_with_loaded_courses(self, data):
        try:
            self.detailed_sic_codes_with_courses = []
            for i in data:
                # Soportar tanto formato antiguo (tupla) como nuevo (diccionario)
                if isinstance(i, dict):
                    s = str(i.get('sic_code', ''))
                    n = str(i.get('course_name', ''))
                elif isinstance(i, (list, tuple)) and len(i) >= 2:
                    s = str(i[0])
                    n = str(i[1])
                else:
                    continue
                
                if s and n:
                    self.detailed_sic_codes_with_courses.append((s, n))
            
            self.from_sic_listbox.delete(0, tk.END)
            self.to_sic_listbox.delete(0, tk.END)
            for s, n in self.detailed_sic_codes_with_courses:
                txt = f"{s} - {n}"
                self.from_sic_listbox.insert(tk.END, txt)
                self.to_sic_listbox.insert(tk.END, txt)
        except Exception as e:
            self.results_frame.add_log(f"❌ Error al procesar datos de cursos: {e}")

    def _connect_to_server(self, show_popups=True):
        """Conecta al servidor. SIEMPRE llamar desde un hilo de fondo."""
        url = self.server_url.get()
        try:
            r = requests.get(f"{url}/api/version", timeout=5)
            version = "???"
            if r.status_code == 200:
                try:
                    version = r.json().get('version', 'V3.1')
                except:
                    version = "V3.1-Legacy"
                
                # Actualizar UI desde hilo principal
                self.master.after(0, lambda v=version: self.connection_status_label.config(
                    text=f"CONECTADO ({v})", foreground="green"))
                
                # Cargar cursos en hilo de fondo también
                self._refresh_courses_from_server()
                
                # Iniciar polling de estado
                self.master.after(500, self._schedule_status_poll)
                
                if show_popups:
                    self.master.after(0, lambda v=version: messagebox.showinfo("OK", f"Conectado al servidor {v}"))
            else:
                self.master.after(0, lambda c=r.status_code: self.connection_status_label.config(
                    text=f"ERROR ({c})", foreground="red"))
        except Exception as e:
            self.master.after(0, lambda: self.connection_status_label.config(
                text="DESCONECTADO", foreground="red"))
            if show_popups:
                logger.error(f"Error de conexión: {e}")

    def _connect_to_server_threaded(self):
        """Botón 'Conectar': lanza la conexión en un hilo de fondo."""
        self.connection_status_label.config(text="Conectando...", foreground="orange")
        threading.Thread(target=self._connect_to_server, args=(True,), daemon=True).start()

    def _log_debug(self, msg):
        try:
            with open("debug_client.txt", "a") as f:
                import datetime
                f.write(f"{datetime.datetime.now()}: {msg}\n")
        except: pass

    def _on_start_scraping(self):
        try:
            self._log_debug("Botón Iniciar Scraping presionado")
            
            # Verificar existencia de listboxes
            if not hasattr(self, 'from_sic_listbox') or not hasattr(self, 'to_sic_listbox'):
                self._log_debug("ERROR: Listboxes no encontrados")
                messagebox.showerror("Error GUI", "Componentes de lista no inicializados.")
                return

            f_idx = self.from_sic_listbox.curselection()
            t_idx = self.to_sic_listbox.curselection()
            
            self._log_debug(f"Selección: From={f_idx}, To={t_idx}")
            
            if not f_idx or not t_idx:
                self._log_debug("Selección vacía. Mostrando aviso.")
                messagebox.showwarning(
                    "Selección Requerida",
                    "Selecciona un curso de inicio y un curso de fin en la lista de la izquierda.\n\n"
                    "Si la lista está vacía, ve a la pestaña 'Configuración del Servidor',\n"
                    "verifica la URL y presiona 'Conectar / Refrescar'."
                )
                return
            
            f_sic = self.from_sic_listbox.get(f_idx[0]).split(' - ')[0]
            t_sic = self.to_sic_listbox.get(t_idx[0]).split(' - ')[0]
            
            params = {
                'from_sic': f_sic,
                'to_sic': t_sic,
                # Parámetros desde la página principal (combobox visible)
                'search_engine': self.search_engine_var.get(),
                # Parámetros desde SearchConfigTab
                'search_mode': self.search_config_tab.search_mode_var.get(),
                'require_keywords': self.search_config_tab.require_keywords_var.get(),
                # Parámetros desde ConfigTab (General)
                'is_headless': self.config_tab.headless_mode_var.get(),
                'min_words': int(self.config_tab.min_words_var.get() or 0),
                'num_workers': int(self.config_tab.num_workers_var.get() or 4)
            }
            
            self._log_debug(f"Params preparados: {params}")

            if hasattr(self, 'controller') and self.controller:
                try:
                    # Pasar la URL completa (con https://)
                    full_url = self.server_url.get()
                    self._log_debug(f"URL Servidor: {full_url}")
                    self.results_frame.add_log(f"Iniciando solicitud de scraping a {full_url}...")
                    self.results_frame.add_log(f"Parámetros: {params}")
                    
                    # Ejecutar en hilo separado para asegurar que no bloquee aunque el controlador no lo hiciera
                    def _launch():
                        try:
                            self._log_debug("Lanzando thread de scraping...")
                            self.controller.start_scraping_on_server(full_url, params)
                            self._log_debug("Thread lanzado OK")
                        except Exception as e:
                            self._log_debug(f"ERROR en thread: {e}")
                            self.master.after(0, lambda: messagebox.showerror("Error en Controlador", f"Fallo al iniciar: {e}"))
                            self.master.after(0, lambda: self.results_frame.add_log(f"❌ Error lanzando scraping: {e}"))

                    threading.Thread(target=_launch, daemon=True).start()
                    
                except Exception as e:
                    self._log_debug(f"ERROR preparando solicitud: {e}")
                    messagebox.showerror("Error GUI", f"Error preparando solicitud: {e}")
                    logger.error(f"Error en _on_start_scraping: {e}")
            else:
                self._log_debug("ERROR: self.controller es None")
                self.results_frame.add_log("❌ Error: Controlador no inicializado.")
                messagebox.showerror("Error Fatal", "El controlador de la aplicación no está conectado a la GUI.")
        
        except Exception as e:
            self._log_debug(f"CRITICAL ERROR _on_start_scraping: {e}")
            import traceback
            self._log_debug(traceback.format_exc())
            messagebox.showerror("Error Crítico", f"Error inesperado en GUI:\n{e}")

    def _on_stop_scraping(self):
        if hasattr(self, 'controller') and self.controller:
            self.controller.stop_scraping()
        else:
            requests.post(f"{self.server_url.get()}/api/stop_scraping")

    def _show_worker_details(self):
        self._on_tree_select(None)

    def _show_failed_courses(self):
        """Muestra una ventana con el resumen de cursos fallidos."""
        try:
            # Obtener datos del servidor
            url = self.server_url.get()
            r = requests.get(f"{url}/api/failed_courses", timeout=10)
            
            if r.status_code != 200:
                messagebox.showerror("Error", f"No se pudo obtener información del servidor: {r.status_code}")
                return
            
            failed_data = r.json()
            
        except Exception as e:
            messagebox.showerror("Error de Conexión", f"No se pudo conectar al servidor: {e}")
            return
        
        # Crear ventana de resultados
        failed_window = tk.Toplevel(self.master)
        failed_window.title("Resumen de Cursos Fallidos")
        failed_window.geometry("900x700")
        
        # Frame principal
        main_frame = ttk.Frame(failed_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Resumen
        summary = failed_data.get('summary', {})
        summary_frame = ttk.LabelFrame(main_frame, text="Resumen", padding="10")
        summary_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(summary_frame, text=f"Total de cursos: {summary.get('total_courses', 0)}", font=("Arial", 10)).pack(anchor=tk.W)
        ttk.Label(summary_frame, text=f"Cursos fallidos: {summary.get('failed_courses', 0)}", font=("Arial", 10, "bold"), foreground="red").pack(anchor=tk.W)
        ttk.Label(summary_frame, text=f"Workers con errores: {summary.get('workers_with_errors', 0)}", font=("Arial", 10)).pack(anchor=tk.W)
        ttk.Label(summary_frame, text=f"Eventos de error: {summary.get('total_error_events', 0)}", font=("Arial", 10)).pack(anchor=tk.W)
        
        # Tipos de error
        error_types = summary.get('error_types', {})
        if error_types:
            error_types_frame = ttk.LabelFrame(main_frame, text="Tipos de Error", padding="10")
            error_types_frame.pack(fill=tk.X, pady=5)
            for error_type, count in error_types.items():
                ttk.Label(error_types_frame, text=f"  • {error_type}: {count}").pack(anchor=tk.W)
        
        # Notebook para pestañas
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Pestaña: Cursos Fallidos
        courses_frame = ttk.Frame(notebook)
        notebook.add(courses_frame, text="Cursos Fallidos")
        
        columns = ("SIC", "Curso", "Estado", "Progreso", "Razón")
        courses_tree = ttk.Treeview(courses_frame, columns=columns, show="headings", selectmode="browse")
        
        for col in columns:
            courses_tree.heading(col, text=col)
            courses_tree.column(col, width=150)
        
        courses_tree.column("Curso", width=300)
        courses_tree.column("Razón", width=200)
        
        vsb = ttk.Scrollbar(courses_frame, orient="vertical", command=courses_tree.yview)
        courses_tree.configure(yscrollcommand=vsb.set)
        
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        courses_tree.pack(fill=tk.BOTH, expand=True)
        
        failed_courses = failed_data.get('failed_courses', [])
        for course in failed_courses:
            courses_tree.insert("", "end", values=(
                course.get('sic_code', ''),
                course.get('course_name', ''),
                course.get('status', ''),
                course.get('progress', 0),
                course.get('reason', '')
            ))
        
        if not failed_courses:
            courses_tree.insert("", "end", values=("", "✅ No hay cursos fallidos", "", "", ""))
        
        # Pestaña: Workers con Errores
        workers_frame = ttk.Frame(notebook)
        notebook.add(workers_frame, text="Workers con Errores")
        
        columns = ("Worker ID", "Estado", "Tarea Actual", "Progreso")
        workers_tree = ttk.Treeview(workers_frame, columns=columns, show="headings", selectmode="browse")
        
        for col in columns:
            workers_tree.heading(col, text=col)
            workers_tree.column(col, width=200)
        
        vsb2 = ttk.Scrollbar(workers_frame, orient="vertical", command=workers_tree.yview)
        workers_tree.configure(yscrollcommand=vsb2.set)
        
        vsb2.pack(side=tk.RIGHT, fill=tk.Y)
        workers_tree.pack(fill=tk.BOTH, expand=True)
        
        workers_with_errors = failed_data.get('workers_with_errors', [])
        for worker in workers_with_errors:
            workers_tree.insert("", "end", values=(
                worker.get('worker_id', ''),
                worker.get('status', ''),
                worker.get('current_task', ''),
                worker.get('progress', 0)
            ))
        
        if not workers_with_errors:
            workers_tree.insert("", "end", values=("", "✅ No hay workers con errores", "", ""))
        
        # Pestaña: Errores Recientes
        errors_frame = ttk.Frame(notebook)
        notebook.add(errors_frame, text="Errores Recientes")
        
        columns = ("Hora", "Fuente", "Mensaje")
        errors_tree = ttk.Treeview(errors_frame, columns=columns, show="headings", selectmode="browse")
        
        for col in columns:
            errors_tree.heading(col, text=col)
            errors_tree.column(col, width=200)
        
        errors_tree.column("Mensaje", width=400)
        
        vsb3 = ttk.Scrollbar(errors_frame, orient="vertical", command=errors_tree.yview)
        errors_tree.configure(yscrollcommand=vsb3.set)
        
        vsb3.pack(side=tk.RIGHT, fill=tk.Y)
        errors_tree.pack(fill=tk.BOTH, expand=True)
        
        recent_errors = failed_data.get('recent_errors', [])
        for error in recent_errors:
            errors_tree.insert("", "end", values=(
                error.get('timestamp', ''),
                error.get('source', ''),
                error.get('message', '')[:100]
            ))
        
        if not recent_errors:
            errors_tree.insert("", "end", values=("", "✅ No hay errores recientes", ""))
        
        # Botón cerrar
        ttk.Button(main_frame, text="Cerrar", command=failed_window.destroy).pack(pady=10)

    def _force_reset_client_state(self):
        """Detiene todo en el servidor, limpia la vista local, auditoría y archivos del servidor."""
        if messagebox.askyesno("Confirmar RESET TOTAL", 
            "¿Seguro que desea resetear TODO el sistema?\n\n"
            "Esta acción:\n"
            "• Detendrá todos los procesos activos en el servidor\n"
            "• Limpiará el Monitor de Actividad Local\n"
            "• Limpiará la Auditoría de Procesos\n"
            "• ELIMINARÁ todos los archivos de resultados del servidor\n\n"
            "¿Continuar?"):
            try:
                # 1. Resetear el servidor (detiene procesos)
                r = requests.post(f"{self.server_url.get()}/api/reset", timeout=10)
                
                # 2. Limpiar archivos del servidor
                r_cleanup = requests.post(f"{self.server_url.get()}/api/cleanup_files", timeout=10)
                
                if r.status_code == 200:
                    self.results_frame.add_log("⚠️ Sistema reiniciado (Cliente + Servidor).")
                    
                    # 3. Limpiar Monitor de Actividad Local
                    self.worker_tree.delete(*self.worker_tree.get_children())
                    
                    # 4. Limpiar Auditoría de Procesos
                    self.audit_tree.delete(*self.audit_tree.get_children())
                    if hasattr(self, 'audit_details_map'):
                        self.audit_details_map.clear()
                    if hasattr(self, 'audit_worker_nodes'):
                        self.audit_worker_nodes.clear()
                    
                    # 5. Limpiar detalles del proceso seleccionado
                    self.details_text.config(state=tk.NORMAL)
                    self.details_text.delete(1.0, tk.END)
                    self.details_text.config(state=tk.DISABLED)
                    
                    # 6. Resetear el contador de eventos
                    if hasattr(self.controller, 'last_event_id'):
                        self.controller.last_event_id = 0
                    
                    messagebox.showinfo("Reset Completo", 
                        "Sistema reseteado correctamente:\n"
                        "✓ Procesos detenidos\n"
                        "✓ Monitor limpio\n"
                        "✓ Auditoría limpiada\n"
                        f"✓ Archivos: {'Borrados' if r_cleanup.status_code == 200 else 'Error al borrar'}")
                else:
                    messagebox.showerror("Error", f"Fallo al resetear servidor: {r.status_code}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo conectar para resetear: {e}")

    def _on_export_results(self):
        path = filedialog.asksaveasfilename(defaultextension=".zip")
        if not path: return
        r = requests.get(f"{self.server_url.get()}/api/download_results")
        with open(path, 'wb') as f: f.write(r.content)

    def _on_open_results_folder(self):
        os.startfile("results") if os.name == 'nt' else subprocess.run(['xdg-open', 'results'])

    def _cleanup_files_action(self):
        ServerFilesWindow(self.master, self.server_url.get())

    def _on_search_from(self, e):
        q = self.search_from_entry.get().lower()
        self.from_sic_listbox.delete(0, tk.END)
        for s, n in getattr(self, 'detailed_sic_codes_with_courses', []):
            if q in s.lower() or q in n.lower(): self.from_sic_listbox.insert(tk.END, f"{s} - {n}")

    def _on_search_to(self, e):
        q = self.search_to_entry.get().lower()
        self.to_sic_listbox.delete(0, tk.END)
        for s, n in getattr(self, 'detailed_sic_codes_with_courses', []):
            if q in s.lower() or q in n.lower(): self.to_sic_listbox.insert(tk.END, f"{s} - {n}")

    def _on_resize(self, e): pass
    def _on_from_sic_select(self, e): pass
    def _on_to_sic_select(self, e): pass
    def _update_timer_display(self, t): self.queue.put(('update_timer', t))
    def _log_callback(self, l): self.queue.put(('log', l))
    
    def _toggle_log_panel(self):
        """Muestra u oculta el panel de log detallado."""
        if self.log_visible.get():
            self.detailed_log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.detailed_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.log_panel_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        else:
            self.log_panel_frame.pack_forget()
            self.detailed_log_text.pack_forget()
            self.detailed_log_scrollbar.pack_forget()
    
    def _add_to_detailed_log(self, message, level="INFO"):
        """Agrega una entrada al log detallado con color según su naturaleza (en AMBAS pestañas)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_entry = f"[{timestamp}] {message}\n"
        
        # Agregar al log de la pestaña Principal
        self.detailed_log_text.insert(tk.END, formatted_entry, level)
        self.detailed_log_text.see(tk.END)
        
        # Agregar al log de la pestaña Expandida
        if hasattr(self, 'expanded_log_text'):
            self.expanded_log_text.insert(tk.END, formatted_entry, level)
            self.expanded_log_text.see(tk.END)
        
        # Si es ERROR, también agregar a la lista de errores expandida
        if level == "ERROR" and hasattr(self, 'expanded_errors_text'):
            self.expanded_errors_text.config(state=tk.NORMAL)
            self.expanded_errors_text.delete(1.0, tk.END)
            self.expanded_errors_text.insert(tk.END, formatted_entry)
            self.expanded_errors_text.config(state=tk.DISABLED)
            self.expanded_errors_text.see(tk.END)
    
    def handle_scraping_finished(self):
        """Maneja el evento de finalización del scraping."""
        self.results_frame.add_log("✅ Proceso de scraping finalizado.")
        self.progress_frame.update_progress(100, "Completado")
        # Actualizar el estado del monitor si existe
        if hasattr(self, 'status_monitor_tab'):
            self.status_monitor_tab.update_status("DETENIDO", "Proceso completado", 100)
    
    def handle_scraping_stopped(self, data):
        """Maneja el evento de detención del scraping."""
        self.results_frame.add_log("⏹️ Proceso de scraping detenido por el usuario.")
        if hasattr(self, 'status_monitor_tab'):
            self.status_monitor_tab.update_status("DETENIDO", "Detenido por usuario", None)
    def _connect_and_load_initial_data(self):
        """Conecta al servidor en un hilo de fondo para no bloquear la GUI."""
        url = self.server_url.get()
        if not url: return
        threading.Thread(target=self._connect_to_server, args=(False,), daemon=True).start()
    def _show_context_menu(self, event):
        """Muestra el menú contextual en la posición del ratón."""
        self.last_event_widget = event.widget
        self.monitor_menu.post(event.x_root, event.y_root)

    def _delete_selected_records(self):
        """Elimina los registros seleccionados del widget que disparó el menú."""
        widget = getattr(self, 'last_event_widget', None)
        if not widget: return
        selection = widget.selection()
        for item in selection:
            widget.delete(item)

    def process_queue(self):
        try:
            while not self.queue.empty():
                t, m = self.queue.get_nowait()
                if t == 'update_timer': self.timer_label.config(text=m)
                elif t == 'log': self.results_frame.add_log(m)
        except: pass
        finally: self.master.after(200, self.process_queue)

    def _schedule_status_poll(self):
        """Programa el polling de estado en un hilo de fondo (no bloquea la GUI)."""
        if self.is_closing: return
        threading.Thread(target=self._do_status_poll, daemon=True).start()

    def _do_status_poll(self):
        """Hace las llamadas HTTP de polling en un hilo de fondo."""
        url = self.server_url.get()
        if not url or self.is_closing: return
        try:
            r = requests.get(f"{url}/api/detailed_status", timeout=3)
            if r.status_code == 200:
                data = r.json()
                workers = data.get('workers', {})
                courses = data.get('courses', [])
                if courses or workers:
                    self.master.after(0, lambda w=workers, c=courses: self._render_status(w, c))

            r_logs = requests.get(f"{url}/api/events?min_id={getattr(self, 'last_event_id', 0)}", timeout=3)
            if r_logs.status_code == 200:
                evs = r_logs.json().get('events', [])
                if evs:
                    self.master.after(0, lambda e=evs: self.update_audit_log(e))
                    self.last_event_id = evs[-1]['id']
        except:
            pass
        finally:
            if not self.is_closing:
                self.master.after(2000, self._schedule_status_poll)

    def _update_status_loop(self):
        """Compatibilidad: redirige al nuevo sistema de polling en hilo de fondo."""
        self._schedule_status_poll()

class ServerFilesWindow(tk.Toplevel):
    def __init__(self, parent, url):
        super().__init__(parent)
        self.url = url
        self.title("Gestor de Archivos del Servidor")
        self.geometry("900x600")
        
        # Tabs para Resultados y Omitidos
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.res_tab = ttk.Frame(self.notebook)
        self.omit_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.res_tab, text="Resultados (.csv)")
        self.notebook.add(self.omit_tab, text="Omitidos (.xlsx)")
        
        self._setup_tab(self.res_tab, "Resultados")
        self._setup_tab(self.omit_tab, "Omitidos")
        
        # Info bar
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.X, padx=10)
        self.status_label = ttk.Label(info_frame, text="Estado: Cargando...", font=("Consolas", 9))
        self.status_label.pack(side=tk.LEFT)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(btn_frame, text="🔄 Refrescar Todo", command=self.refresh).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ LIMPIAR SERVIDOR (BORRAR TODO)", 
                   style="Danger.TButton", command=self._cleanup_all).pack(side=tk.RIGHT, padx=5)
        
        self.refresh()

    def _setup_tab(self, frame, category):
        # Filtro por categoría (EN, ES, Omitidos)
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('name', 'category', 'size', 'date')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        tree.heading('name', text='Archivo')
        tree.heading('category', text='Cat')
        tree.heading('size', text='Tamaño')
        tree.heading('date', text='Fecha Modificación')
        
        tree.column('name', width=300)
        tree.column('category', width=80, anchor=tk.CENTER)
        tree.column('size', width=100, anchor=tk.E)
        tree.column('date', width=150, anchor=tk.CENTER)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Atajos de botón por fila si fuera posible, pero en Treeview es mejor menú contextual
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Descargar", command=lambda: self._download_selected(tree))
        menu.add_command(label="Eliminar", command=lambda: self._delete_selected(tree))
        
        tree.bind("<Button-3>", lambda e: menu.post(e.x_root, e.y_root))
        
        # Guardar referencia
        if category == "Resultados": self.res_tree = tree
        else: self.omit_tree = tree

    def refresh(self):
        self.res_tree.delete(*self.res_tree.get_children())
        self.omit_tree.delete(*self.omit_tree.get_children())
        self.status_label.config(text="Estado: Actualizando...", foreground="black")
        
        try:
            r = requests.get(f"{self.url}/api/list_results", timeout=15)
            if r.status_code == 200:
                data = r.json()
                files = data.get('files', [])
                dir_path = data.get('results_dir', '/app/results')
                self.status_label.config(text=f"Directorio: {dir_path} | Archivos: {len(files)}", foreground="blue")
                
                for f in files:
                    vals = (f['name'], f['category'], f['size_human'], f['modified_human'])
                    if f['category'] == "Omitidos":
                        self.omit_tree.insert('', tk.END, iid=f['name'], values=vals)
                    else:
                        self.res_tree.insert('', tk.END, iid=f['name'], values=vals)
            else:
                self.status_label.config(text=f"Error {r.status_code} al listar archivos.", foreground="red")
        except Exception as e:
            self.status_label.config(text=f"Error de conexión: {str(e)[:50]}...", foreground="red")

    def _download_selected(self, tree):
        sel = tree.selection()
        if not sel: return
        filename = sel[0]
        path = filedialog.asksaveasfilename(initialfile=filename)
        if not path: return
        
        try:
            r = requests.get(f"{self.url}/api/download_file", params={"filename": filename}, stream=True)
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
            messagebox.showinfo("OK", "Archivo descargado.")
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al descargar: {e}")

    def _delete_selected(self, tree):
        sel = tree.selection()
        if not sel: return
        filename = sel[0]
        if messagebox.askyesno("Confirmar", f"¿Eliminar {filename} del servidor?"):
            try:
                r = requests.delete(f"{self.url}/api/delete_file", params={"filename": filename}, timeout=10)
                if r.status_code == 200:
                    messagebox.showinfo("OK", f"Archivo '{filename}' eliminado del servidor.")
                    self.refresh()
                else:
                    try:
                        detail = r.json().get('detail', r.text)
                    except Exception:
                        detail = r.text
                    messagebox.showerror("Error", f"No se pudo eliminar: {detail}")
            except Exception as e:
                messagebox.showerror("Error", f"Fallo de conexión: {e}")

    def _cleanup_all(self):
        if messagebox.askyesno("PELIGRO", "¿Seguro que desea BORRAR TODOS los archivos de resultados en el servidor?\nEsta acción no se puede deshacer."):
            try:
                r = requests.post(f"{self.url}/api/cleanup_files")
                if r.status_code == 200:
                    messagebox.showinfo("OK", "Servidor limpio.")
                    self.refresh()
                else: messagebox.showerror("Error", f"Fallo: {r.status_code}")
            except Exception as e: messagebox.showerror("Error", str(e))

class DummyResultsFrame:
    """
    Clase dummy para compatibilidad con código que llama a results_frame.add_log().
    Redirige los logs al Monitor de Estado en lugar de mostrarlos en un frame separado.
    """
    def __init__(self):
        self.gui = None
    
    def set_gui(self, gui):
        """Establece referencia al GUI principal."""
        self.gui = gui
    
    def add_log(self, message):
        """Redirige logs al log detallado del Monitor de Estado."""
        # Determinar el nivel del log basado en el contenido
        if "ERROR" in message or "❌" in message or "Error" in message:
            level = "ERROR"
        elif "WARNING" in message or "⚠️" in message:
            level = "WARNING"
        elif "✅" in message or "Completado" in message or "exitosamente" in message:
            level = "SUCCESS"
        else:
            level = "INFO"
        
        # Agregar al log detallado si el GUI está disponible
        if self.gui and hasattr(self.gui, '_add_to_detailed_log'):
            self.gui._add_to_detailed_log(message, level)


class StatusMonitorTab:
    """
    Monitor de Estado del Sistema (ahora integrado en la pestaña Principal)
    =======================================================================
    Muestra:
    - Estado actual del proceso (activo/detenido)
    - Porcentaje de avance general
    - Lista de errores críticos
    - Log detallado del proceso
    
    NOTA: Esta clase ahora es solo para compatibilidad interna.
    El monitor real está integrado en la pestaña Principal.
    """
    
    def __init__(self, notebook, gui):
        self.gui = gui
        # Si notebook es None, crear un frame dummy para compatibilidad
        if notebook is not None:
            self.frame = ttk.Frame(notebook, padding="10")
            self._setup_ui_standalone()
        else:
            self.frame = None  # Modo integrado
        
        # Variables de estado
        self.current_status = "INACTIVO"
        self.current_progress = 0
        self.current_message = "Sistema listo"
        self.error_count = 0
        self.critical_errors = []
        self.last_log_progress = 0
    
    def _setup_ui_standalone(self):
        """Configura la interfaz cuando está como pestaña separada (no usado actualmente)."""
        pass  # El modo standalone ya no se usa
    
    def _setup_ui(self):
        """Configura la interfaz del monitor de estado."""
        
        # === SECCIÓN 1: ESTADO GENERAL ===
        status_frame = ttk.LabelFrame(self.frame, text="Estado del Sistema", padding="10")
        status_frame.pack(fill=tk.X, pady=5)
        
        # Indicador de estado con color
        self.status_indicator_frame = ttk.Frame(status_frame)
        self.status_indicator_frame.pack(fill=tk.X)
        
        # Etiqueta de estado
        self.status_label = ttk.Label(
            self.status_indicator_frame, 
            text="● INACTIVO", 
            font=("Arial", 18, "bold"),
            foreground="gray"
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Mensaje de estado
        self.status_message = ttk.Label(
            self.status_indicator_frame,
            text="Sistema listo para iniciar",
            font=("Arial", 11)
        )
        self.status_message.pack(side=tk.LEFT, padx=20)
        
        # === SECCIÓN 2: PROGRESO GENERAL ===
        progress_frame = ttk.LabelFrame(self.frame, text="Progreso General", padding="10")
        progress_frame.pack(fill=tk.X, pady=5)
        
        # Barra de progreso
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Etiqueta de porcentaje
        self.progress_label = ttk.Label(
            progress_frame,
            text="0% - Sin progreso",
            font=("Arial", 12, "bold")
        )
        self.progress_label.pack()
        
        # Estadísticas rápidas
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.courses_completed_label = ttk.Label(stats_frame, text="✅ Completados: 0")
        self.courses_completed_label.pack(side=tk.LEFT, padx=10)
        
        self.courses_pending_label = ttk.Label(stats_frame, text="⏳ Pendientes: 0")
        self.courses_pending_label.pack(side=tk.LEFT, padx=10)
        
        self.courses_failed_label = ttk.Label(stats_frame, text="❌ Fallidos: 0", foreground="red")
        self.courses_failed_label.pack(side=tk.LEFT, padx=10)
        
        # === SECCIÓN 3: ERRORES CRÍTICOS ===
        errors_frame = ttk.LabelFrame(self.frame, text="⚠️ Errores Críticos", padding="10")
        errors_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Lista de errores con scrollbar
        errors_container = ttk.Frame(errors_frame)
        errors_container.pack(fill=tk.BOTH, expand=True)
        
        self.errors_text = tk.Text(
            errors_container, 
            font=("Consolas", 10), 
            height=8, 
            wrap=tk.WORD,
            bg="#fff5f5"
        )
        self.errors_scrollbar = ttk.Scrollbar(errors_container, orient=tk.VERTICAL, command=self.errors_text.yview)
        self.errors_text.configure(yscrollcommand=self.errors_scrollbar.set)
        
        self.errors_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.errors_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.errors_text.insert(tk.END, "No hay errores críticos registrados.\n")
        self.errors_text.config(state=tk.DISABLED)
        
        # Botón para limpiar errores
        ttk.Button(errors_frame, text="🗑️ Limpiar Errores", command=self._clear_errors).pack(pady=5)
        
        # === SECCIÓN 4: LOG DETALLADO ===
        log_frame = ttk.LabelFrame(self.frame, text="📋 Log Detallado del Proceso", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Área de log con scrollbar
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(
            log_container, 
            font=("Consolas", 9), 
            height=10, 
            wrap=tk.WORD,
            bg="#f5f5f5"
        )
        self.log_scrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configurar tags para colores
        self.log_text.tag_configure('ERROR', foreground='red')
        self.log_text.tag_configure('WARNING', foreground='orange')
        self.log_text.tag_configure('SUCCESS', foreground='green')
        self.log_text.tag_configure('INFO', foreground='blue')
        
        # Botones de control
        btn_frame = ttk.Frame(log_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="🗑️ Limpiar Log", command=self._clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📋 Copiar Log", command=self._copy_log).pack(side=tk.LEFT, padx=5)
    
    def update_status(self, status, message=None, progress=None):
        """Actualiza el estado del sistema (compatibilidad)."""
        self.current_status = status
        if message:
            self.current_message = message
        if progress is not None:
            self.current_progress = progress
    
    def update_stats(self, completed=0, pending=0, failed=0):
        """Actualiza las estadísticas de cursos (compatibilidad)."""
        pass  # Ahora manejado por _update_status_monitor
    
    def add_error(self, error_message, source="System"):
        """Agrega un error crítico a la lista (compatibilidad)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_error = f"[{timestamp}] [{source}] {error_message}\n"
        self.critical_errors.append(formatted_error)
        self.error_count += 1
    
    def add_log_entry(self, message, level="INFO"):
        """Agrega una entrada al log detallado (compatibilidad)."""
        # Ahora manejado por _add_to_detailed_log
        pass


if __name__ == "__main__":
    pass
