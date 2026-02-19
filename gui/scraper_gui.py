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
        
        self._create_server_config_tab()
        self.config_tab = ConfigTab(self.notebook, self.config)
        self.search_config_tab = SearchConfigTab(self.notebook, self.config)

        # PanedWindow Horizontal Maestro (SIC | MONITOR+DETALLES | RESULTADOS)
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        self.left_column = ttk.Frame(self.paned_window)
        self.center_column = ttk.Frame(self.paned_window)
        self.right_column = ttk.Frame(self.paned_window)
        
        self.paned_window.add(self.left_column, weight=4)   # SIC
        self.paned_window.add(self.center_column, weight=5) # Monitor/Detalles
        self.paned_window.add(self.right_column, weight=3)  # Resultados
        
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

        # SECCIÓN 1: MONITOR ÁREA (WORKERS + AUDITORÍA)
        self.monitor_area = ttk.LabelFrame(self.center_master_paned, text="Monitor de Actividad Local", padding=5)
        self.center_master_paned.add(self.monitor_area, weight=3)

        # Botones del Monitor
        self.mon_btn_frame = ttk.Frame(self.monitor_area)
        self.mon_btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=2)
        ttk.Button(self.mon_btn_frame, text="Ver Detalles de Worker", command=self._show_worker_details).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(self.mon_btn_frame, text="⚠️ Resetear Sistema (Emergencia)", command=self._force_reset_client_state).pack(side=tk.RIGHT, padx=5, expand=True, fill=tk.X)

        # PanedWindow Interna (Workers vs Historial)
        self.inner_monitor_paned = ttk.PanedWindow(self.monitor_area, orient=tk.VERTICAL)
        self.inner_monitor_paned.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Workers Tree
        self.workers_pane = ttk.Frame(self.inner_monitor_paned)
        self.inner_monitor_paned.add(self.workers_pane, weight=1)
        self.worker_tree = ttk.Treeview(self.workers_pane, columns=('ID', 'Status', 'Course', 'Progress'), show='headings')
        for col in ('ID', 'Status', 'Course', 'Progress'):
            self.worker_tree.heading(col, text=col)
        self.worker_tree.column('ID', width=50, anchor=tk.CENTER)
        self.worker_tree.column('Status', width=120)
        self.worker_tree.column('Course', width=350)
        self.worker_tree.column('Progress', width=80, anchor=tk.CENTER)
        self.worker_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb1 = ttk.Scrollbar(self.workers_pane, orient=tk.VERTICAL, command=self.worker_tree.yview)
        self.worker_tree.configure(yscrollcommand=sb1.set)
        sb1.pack(side=tk.RIGHT, fill=tk.Y)

        # Audit Tree (Historial)
        self.audit_pane = ttk.LabelFrame(self.inner_monitor_paned, text="Auditoría de Procesos (Historial)", padding=5)
        self.inner_monitor_paned.add(self.audit_pane, weight=2)
        self.audit_tree = ttk.Treeview(self.audit_pane, columns=('Time', 'Type', 'Source', 'Message'), show='headings')
        for col in ('Time', 'Type', 'Source', 'Message'):
            self.audit_tree.heading(col, text=col)
        self.audit_tree.column('Time', width=80, anchor=tk.CENTER)
        self.audit_tree.column('Type', width=100, anchor=tk.CENTER)
        self.audit_tree.column('Source', width=100, anchor=tk.CENTER)
        self.audit_tree.column('Message', width=500)
        self.audit_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb2 = ttk.Scrollbar(self.audit_pane, orient=tk.VERTICAL, command=self.audit_tree.yview)
        self.audit_tree.configure(yscrollcommand=sb2.set)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)

        # SECCIÓN 2: DETALLES DEL PROCESO SELECCIONADO (ABAJO)
        self.details_area = ttk.LabelFrame(self.center_master_paned, text="Detalles del Proceso Seleccionado", padding=5)
        self.center_master_paned.add(self.details_area, weight=2)
        self.details_text = tk.Text(self.details_area, font=("Consolas", 11), state=tk.DISABLED, bg="#f0f0f0")
        self.details_text.pack(fill=tk.BOTH, expand=True)

        # Tags y Bindings
        self.audit_tree.tag_configure('ERROR', foreground='white', background='#d32f2f')
        self.audit_tree.tag_configure('WARNING', foreground='black', background='#fbc02d')
        self.audit_tree.tag_configure('SUCCESS', foreground='white', background='#388e3c')
        self.audit_tree.tag_configure('SCRAPER', foreground='blue')
        self.audit_tree.tag_configure('SYSTEM', foreground='gray')
        self.worker_tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.audit_tree.bind('<<TreeviewSelect>>', self._on_audit_select)
        self.monitor_menu = tk.Menu(self.master, tearoff=0)
        self.monitor_menu.add_command(label="Eliminar registro", command=self._delete_selected_records)
        self.worker_tree.bind("<Button-3>", self._show_context_menu)
        self.audit_tree.bind("<Button-3>", self._show_context_menu)
        
        # --- COLUMNA DERECHA (RESULTADOS) ---
        self.results_frame = ResultsFrame(self.right_column)
        self.results_frame.pack(fill=tk.BOTH, expand=True)
        self.results_btns = ttk.Frame(self.right_column)
        self.results_btns.pack(fill=tk.X, pady=5)
        ttk.Button(self.results_btns, text="Exportar Resultados (ZIP)", command=self._on_export_results).pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        ttk.Button(self.results_btns, text="Abrir Carpeta", command=self._on_open_results_folder).pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        ttk.Button(self.results_btns, text="Gestionar Servidor", command=self._cleanup_files_action).pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

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
        
        self.connect_button = ttk.Button(config_frame, text="Conectar / Refrescar", command=self._connect_to_server)
        self.connect_button.grid(row=2, column=1, padx=10, pady=20, sticky=tk.E)
        
        self.connection_status_label = ttk.Label(config_frame, text="Desconectado", foreground="red")
        self.connection_status_label.grid(row=3, column=1, padx=10, sticky=tk.E)
        
        config_frame.columnconfigure(1, weight=1)

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

    def _render_worker_status(self, worker_states):
        """Renderiza el estado dinámico de los trabajadores en el Monitor (UN SOLO REGISTRO POR CURSO)."""
        if not hasattr(self, 'row_details_map'): self.row_details_map = {}
        for worker_id, state in worker_states.items():
            worker_id_str = str(worker_id)
            raw_task = state.get('current_task', 'N/A')
            server_status = state.get('status', 'N/A').capitalize()
            
            # Parsing para separar Curso de Estado (Evitar filas duplicadas para un mismo curso)
            display_status = server_status
            display_course = raw_task
            is_transient = False
            
            # Limpiar curso y extraer sub-fases (ej: Cordis Página X)
            clean_task = raw_task
            if "Cordis API" in raw_task:
                 # Ejemplo: "Cordis API | Página 26 | 920/937 resultados"
                 parts = [p.strip() for p in re.split(r'[-|]', raw_task)]
                 display_status = " - ".join(parts[:2]) if len(parts) >= 2 else parts[0]
                 display_course = " - ".join(parts[2:]) if len(parts) >= 3 else "Buscando..."
            elif "Buscando curso" in raw_task and (" - " in raw_task or " | " in raw_task):
                 # Ejemplo: "Buscando curso 1 de 10 - 0119.0 - Cash Grains"
                 parts = [p.strip() for p in re.split(r'[-|]', raw_task)]
                 display_status = parts[0]
                 display_course = " - ".join(parts[1:])
            elif "Tabulando curso" in raw_task and (" - " in raw_task or " | " in raw_task):
                 parts = [p.strip() for p in re.split(r'[-|]', raw_task)]
                 display_status = parts[0]
                 display_course = " - ".join(parts[1:])
            elif "|" in raw_task:
                 display_status = raw_task.split('|')[1].strip()
                 display_course = raw_task.split('|')[0].strip()

            # ID único por curso para evitar duplicidad
            import re
            sic_match = re.search(r'(\d+\.\d+)', display_course)
            if sic_match:
                row_id = f"sic_{sic_match.group(1).replace('.', '_')}"
            elif "Iniciando" in raw_task or "Esperando" in raw_task:
                row_id = f"worker_msg_{worker_id_str}"
                is_transient = True
            else:
                row_id = f"course_{hashlib.md5(display_course.encode()).hexdigest()[:8]}"

            vals = (worker_id_str, display_status, display_course, f"{int(state.get('progress', 0))}%")
            self.row_details_map[row_id] = raw_task
            if self.worker_tree.exists(row_id):
                self.worker_tree.item(row_id, values=vals)
            else:
                self.worker_tree.insert('', '0' if not is_transient else 'end', iid=row_id, values=vals)
        
        # Progreso general
        if worker_states:
            active = [s for s in worker_states.values() if s.get('status') != 'Idle']
            if active:
                avg = sum(s.get('progress', 0) for s in active) / len(active)
                self.progress_frame.update_progress(avg, f"General: {avg:.1f}%")
            else:
                self.progress_frame.update_progress(100, "Inactivo")

    def update_audit_log(self, events):
        """Actualiza el historial de auditoría."""
        if not hasattr(self, 'audit_details_map'): self.audit_details_map = {}
        for ev in events:
            row_id = f"ev_{ev['id']}"
            msg = ev.get('message', '')
            self.audit_details_map[row_id] = f"{ev.get('timestamp')}\n{msg}\n\n{json.dumps(ev.get('details'), indent=2)}"
            self.audit_tree.insert('', 0, iid=row_id, values=(ev.get('timestamp'), ev.get('type'), ev.get('source'), msg), tags=(ev.get('type'),))

    def _on_audit_select(self, event):
        sel = self.audit_tree.selection()
        if sel:
            txt = self.audit_details_map.get(sel[0], "")
            self.details_text.config(state=tk.NORMAL)
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, txt)
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
        try:
            r = requests.get(f"{self.server_url.get()}/api/version", timeout=5)
            version = "???"
            if r.status_code == 200:
                try:
                    version = r.json().get('version', 'V3.1')
                except:
                    version = "V3.1-Legacy"
                
                self.connection_status_label.config(text=f"CONECTADO ({version})", foreground="green")
                self._refresh_courses_from_server()
                self._update_status_loop()
                if show_popups: messagebox.showinfo("OK", f"Conectado al servidor {version}")
            else:
                self.connection_status_label.config(text=f"ERROR ({r.status_code})", foreground="red")
        except Exception as e:
            self.connection_status_label.config(text="DESCONECTADO", foreground="red")
            if show_popups: logger.error(f"Error de conexión: {e}")

    def _on_start_scraping(self):
        f_idx = self.from_sic_listbox.curselection()
        t_idx = self.to_sic_listbox.curselection()
        if not f_idx or not t_idx: return
        f_sic = self.from_sic_listbox.get(f_idx[0]).split(' - ')[0]
        t_sic = self.to_sic_listbox.get(t_idx[0]).split(' - ')[0]
        
        params = {
            'from_sic': f_sic,
            'to_sic': t_sic,
            'search_engine': self.search_config_tab.search_engine.get(),
            'is_headless': self.search_config_tab.is_headless.get(),
            'min_words': int(self.search_config_tab.min_words.get() or 0),
            'search_mode': self.search_config_tab.search_mode.get(),
            'require_keywords': self.search_config_tab.require_keywords.get(),
            'num_workers': int(self.search_config_tab.num_workers.get() or 4)
        }
        
        if hasattr(self, 'controller') and self.controller:
            self.controller.start_scraping_on_server(self.server_url.get().replace('http://',''), params)
        else:
            self.results_frame.add_log("❌ Error: Controlador no inicializado.")

    def _on_stop_scraping(self):
        if hasattr(self, 'controller') and self.controller:
            self.controller.stop_scraping()
        else:
            requests.post(f"{self.server_url.get()}/api/stop_scraping")

    def _show_worker_details(self):
        self._on_tree_select(None)

    def _force_reset_client_state(self):
        """Detiene todo en el servidor y limpia la vista local."""
        if messagebox.askyesno("Confirmar", "¿Seguro que desea resetear TODO el sistema (Servidor + Cliente)?\nSe detendrán todos los procesos activos."):
            try:
                r = requests.post(f"{self.server_url.get()}/api/reset", timeout=10)
                if r.status_code == 200:
                    self.results_frame.add_log("⚠️ Sistema reiniciado (Cliente + Servidor).")
                    # No reseteamos los listboxes para no perder la selección, solo el estado de workers
                    self.worker_tree.delete(*self.worker_tree.get_children())
                    messagebox.showinfo("Reset", "El sistema ha sido reseteado correctamente.")
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
    def _connect_and_load_initial_data(self):
        """Intenta conectar con el servidor y cargar datos iniciales."""
        url = self.server_url.get()
        if not url: return
        
        try:
            # Probar conexión (ping)
            r = requests.get(f"{url}/api/ping", timeout=3)
            self._connect_to_server(False)
        except: pass
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

    def _update_status_loop(self):
        """Bucle para obtener estado y logs periódicamente."""
        url = self.server_url.get()
        if not url or self.is_closing: return
        
        try:
            # Estado detallado
            r = requests.get(f"{url}/api/detailed_status", timeout=2)
            if r.status_code == 200:
                data = r.json()
                self._render_worker_status(data.get('workers', {}))
                
            # Audit logs (scan_events fue renombrado a events para consistencia)
            r_logs = requests.get(f"{url}/api/events?min_id={getattr(self, 'last_event_id', 0)}", timeout=2)
            if r_logs.status_code == 200:
                evs = r_logs.json().get('events', [])
                if evs:
                    self.update_audit_log(evs)
                    self.last_event_id = evs[-1]['id']
        except requests.exceptions.ConnectionError:
            # Server might be down or unreachable
            pass
        except Exception as e:
            print(f"Error in _update_status_loop: {e}")
        finally:
            if not self.is_closing:
                self.master.after(1000, self._update_status_loop) # Poll every 1 second

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

if __name__ == "__main__":
    pass
