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
        self.master = master
        self.controller = controller
        
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
        
        # Crear la pestaña de configuración con los parámetros correctos - AQUÍ ESTÁ LA CORRECCIÓN
        self.config_tab = ConfigTab(self.notebook, self.config)
        
        # Crear un PanedWindow para permitir al usuario redimensionar las columnas
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Crear las dos columnas como paneles del PanedWindow
        self.left_column = ttk.Frame(self.paned_window)
        self.right_column = ttk.Frame(self.paned_window)
        
        # Añadir las columnas al PanedWindow
        self.paned_window.add(self.left_column, weight=6)  # Columna izquierda más ancha (60%)
        self.paned_window.add(self.right_column, weight=4)  # Columna derecha más angosta (40%)
        
        # COLUMNA IZQUIERDA - Controles
        
        # Crear un frame para el título y el timer
        self.header_frame = ttk.Frame(self.left_column)
        self.header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Título de la aplicación
        # Obtener el nombre del equipo
        computer_name = socket.gethostname()
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
        
        # Crear marco para selección de código SIC
        self.sic_frame = ttk.LabelFrame(self.left_column, text="Selección de Código", padding=10)
        self.sic_frame.pack(fill=tk.X, pady=10)

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
        
        # Crear marco de controles
        self.control_frame = ControlFrame(
            self.left_column,
            on_start=self._on_start_scraping,
            on_stop=self._on_stop_scraping
        )
        self.control_frame.pack(fill=tk.X, pady=2)
        
        # Crear marco de progreso
        self.progress_frame = ProgressFrame(self.left_column)
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
            self.paned_window.sashpos(0, int(width * 0.6))  # Posicionar el divisor al 60% del ancho

    def _on_config_saved(self, config):
        """
        Callback para cuando se guarda la configuración.
        
        Args:
            config: Diccionario con la configuración guardada
        """
        logger.info("Configuración guardada. Actualizando componentes...")
        
        # Actualizar componentes con la nueva configuración
        if self.controller:
            # Actualizar configuración en el controlador
            if hasattr(self.controller, 'update_config'):
                self.controller.update_config(config)
            
            # Actualizar configuración en el browser_manager
            if hasattr(self.controller, 'browser_manager'):
                browser_manager = self.controller.browser_manager
                
                # Actualizar proxies
                if hasattr(browser_manager, 'set_proxies') and self.proxy_manager:
                    browser_manager.set_proxies(self.proxy_manager.get_all_proxies())
        
        # Mostrar mensaje en el área de logs
        if hasattr(self, 'results_frame'):
            self.results_frame.add_log("Configuración actualizada correctamente.")

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

    def _on_captcha_config_saved(self, use_service, api_key):
        """
        Callback para cuando se guarda la configuración de CAPTCHAs.
        
        Args:
            use_service: Si se debe usar el servicio de resolución
            api_key: Clave API para el servicio
        """
        logger.info(f"Configuración de CAPTCHAs actualizada. Usar servicio: {use_service}")
        
        # Mostrar mensaje en el área de logs
        if hasattr(self, 'results_frame'):
            self.results_frame.add_log(f"Configuración de CAPTCHAs actualizada. Usar servicio: {use_service}")

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

    def _on_search_from(self, event):
        """Filtra el listbox 'desde' según el término de búsqueda."""
        search_term = self.search_from_entry.get()
        self._filter_listbox(self.from_sic_listbox, search_term)

    def _on_search_to(self, event):
        """Filtra el listbox 'hasta' según el término de búsqueda."""
        search_term = self.search_to_entry.get()
        self._filter_listbox(self.to_sic_listbox, search_term)

    def _filter_listbox(self, listbox, search_term):
        """Filtra un listbox según el término de búsqueda."""
        listbox.delete(0, tk.END)
        for item in self.detailed_sic_codes_with_courses:
            if search_term.lower() in str(item).lower():
                listbox.insert(tk.END, item)

    def _load_data(self):
        """Carga datos del archivo CSV y puebla los componentes de la interfaz."""
        try:
            # Cargar datos del curso
            self.csv_handler.load_course_data()
          
            # Obtener códigos SIC detallados con nombres de cursos y poblar comboboxes
            self.detailed_sic_codes_with_courses = self.csv_handler.get_detailed_sic_codes_with_courses()
          
            # Registrar el número de elementos para depuración
            logger.info(f"Cargados {len(self.detailed_sic_codes_with_courses)} códigos SIC con cursos para comboboxes")
          
            if not self.detailed_sic_codes_with_courses:
                logger.warning("No se encontraron códigos SIC detallados con cursos")
                messagebox.showwarning("Advertencia", "No se encontraron códigos SIC en el archivo CSV. Verifique que el archivo data/class5_course_list.csv existe y tiene las columnas 'sic_code' y 'course'.")
                return
          
            # Establecer valores en el marco de selección SIC
            if hasattr(self, 'from_sic_listbox') and hasattr(self, 'to_sic_listbox'):
                for item in self.detailed_sic_codes_with_courses:
                    self.from_sic_listbox.insert(tk.END, item)
                    self.to_sic_listbox.insert(tk.END, item)

                if self.detailed_sic_codes_with_courses:
                    self.from_sic_listbox.selection_set(0)
                    self.to_sic_listbox.selection_set(len(self.detailed_sic_codes_with_courses) - 1)
          
            logger.info("Datos cargados exitosamente")
          
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

    def _on_from_sic_select(self, selected_item):
        """
        Maneja la selección del código SIC 'desde'.
        
        Args:
            selected_item: Código SIC seleccionado
        """
        logger.info(f"Seleccionado 'desde' SIC: {selected_item}")

    def _on_to_sic_select(self, selected_item):
        """
        Maneja la selección del código SIC 'hasta'.
        
        Args:
            selected_item: Código SIC seleccionado
        """
        logger.info(f"Seleccionado 'hasta' SIC: {selected_item}")

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
        from_sic_index = self.from_sic_listbox.curselection()
        to_sic_index = self.to_sic_listbox.curselection()

        if not from_sic_index or not to_sic_index:
            messagebox.showwarning("Entrada Faltante", "Por favor seleccione el rango de código")
            return

        from_sic = self.from_sic_listbox.get(from_sic_index[0])
        to_sic = self.to_sic_listbox.get(to_sic_index[0])
        
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
            'from_sic': from_sic[0] if isinstance(from_sic, tuple) else from_sic,
            'to_sic': to_sic[0] if isinstance(from_sic, tuple) else to_sic,
            'from_course': from_sic[1] if isinstance(from_sic, tuple) else "",
            'to_course': to_sic[1] if isinstance(from_sic, tuple) else ""
        }

        # Registrar los valores seleccionados para depuración
        logger.info(f"Rango seleccionado: Desde Código {params['from_sic']} hasta {params['to_sic']}")
        logger.info(f"Cursos seleccionados: Desde '{params['from_course']}' hasta '{params['to_course']}'")
        
        # Iniciar scraping en un hilo separado
        threading.Thread(target=self._run_scraping, args=(params,), daemon=True).start()

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
            # Verificar si el controlador está disponible
            if not self.controller:
                self.queue.put(('error', "Controlador de scraping no inicializado"))
                self.timer_manager.stop()
                self.queue.put(('scraping_done', None))
                return

            # Iniciar el proceso de scraping
            self.queue.put(('status', "Inicializando scraper..."))

            # Crear bucle de eventos asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Ejecutar el proceso de scraping sin timeout global
            try:
                # Configurar el callback para los logs
                results = loop.run_until_complete(
                    self.controller.run_scraping(
                        params,
                        progress_callback=self._progress_callback
                    )
                )
          
                # Procesar resultados
                if results:
                    self.queue.put(('results', results))
                    self.queue.put(('status', f"Scraping completado. Se encontraron {len(results)} resultados."))
                    self.queue.put(('enable_export', None))
              
                    # Mostrar mensaje en una ventana emergente
                    # Verificar si hay resultados omitidos
                    omitted_count = 0
                    omitted_file = ""
                    if hasattr(self.controller, 'omitted_results'):
                        omitted_count = len(self.controller.omitted_results)
                        omitted_file = self.controller.omitted_file

                    if omitted_count > 0:
                        self.queue.put(('show_message', f"Proceso completado.\n\nSe encontraron {len(results)} resultados guardados en:\n{self.controller.result_manager.get_output_file()}\n\nSe omitieron {omitted_count} resultados guardados en:\n{omitted_file}"))
                    else:
                        self.queue.put(('show_message', f"Proceso completado. Se encontraron {len(results)} resultados.\n\nGuardados en:\n{self.controller.result_manager.get_output_file()}"))
                else:
                    self.queue.put(('status', "No se encontraron resultados."))
              
                    # Mostrar mensaje en una ventana emergente
                    # Verificar si hay resultados omitidos
                    omitted_count = 0
                    omitted_file = ""
                    if hasattr(self.controller, 'omitted_results'):
                        omitted_count = len(self.controller.omitted_results)
                        omitted_file = self.controller.omitted_file

                    if omitted_count > 0:
                        self.queue.put(('show_message', f"Proceso completado.\n\nNo se encontraron resultados. Archivo CSV vacío creado en:\n{self.controller.result_manager.get_output_file()}\n\nSe omitieron {omitted_count} resultados guardados en:\n{omitted_file}"))
                    else:
                        self.queue.put(('show_message', f"Proceso completado. No se encontraron resultados.\n\nArchivo CSV vacío creado en:\n{self.controller.result_manager.get_output_file()}"))
          
            except Exception as e:
                logger.error(f"Error durante la ejecución del scraping: {str(e)}")
                self.queue.put(('error', f"Error durante la ejecución del scraping: {str(e)}"))
                self.timer_manager.stop()

            finally:
                # Cerrar el bucle de eventos
                loop.close()
          
        except Exception as e:
            logger.error(f"Error durante el scraping: {str(e)}")
            self.queue.put(('error', f"Error durante el scraping: {str(e)}"))
            self.timer_manager.stop()
        finally:
            # Asegurarse de que la interfaz se actualice correctamente
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
        
        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"Error procesando cola: {e}")
        finally:
            # Programar siguiente verificación de cola
            self.master.after(200, self.process_queue)
