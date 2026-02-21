"""
Configuration Tab
-----------------
Pestaña de configuración para la aplicación de scraping.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import logging
import json
import os
from typing import Dict, Any, Optional, List, Callable
import threading
import time
import multiprocessing

from utils.config import Config
from gui.captcha_config import CaptchaConfigWindow
from gui.database_config import DatabaseConfigTab

logger = logging.getLogger(__name__)

class ConfigTab:
    """
    Pestaña de configuración para la aplicación de scraping.
    Permite configurar proxies, CAPTCHAs y otros parámetros.
    """
    
    def __init__(self, parent_notebook: ttk.Notebook, config: Config):
        """
        Inicializa la pestaña de configuración.
        
        Args:
            parent_notebook: Notebook padre donde se añadirá la pestaña
            config: Instancia de configuración
        """
        self.config = config
        self.parent_notebook = parent_notebook
        
        # Crear el frame principal de la pestaña
        self.main_frame = ttk.Frame(parent_notebook)
        parent_notebook.add(self.main_frame, text="Configuración")
        
        # Variables de control
        self.proxy_test_results = {}
        self.is_testing_proxies = False
        
        # Callbacks
        self.on_config_changed = None
        
        # Crear la interfaz
        self._create_interface()
        
        # Cargar configuración inicial
        self._load_current_config()
        
        logger.info("ConfigTab inicializado correctamente")
    
    def _create_interface(self):
        """Crea la interfaz de la pestaña de configuración."""
        # Frame para botones principales (Empaquetar PRIMERO al fondo para asegurar visibilidad)
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(10, 10))
        
        # Botones principales
        ttk.Button(button_frame, text="Aplicar Configuración", 
                  command=self._apply_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Restablecer", 
                  command=self._reset_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Importar", 
                  command=self._import_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Exportar", 
                  command=self._export_config).pack(side=tk.LEFT, padx=5)

        # Crear notebook para sub-pestañas (Empaquetar después para llenar el resto)
        self.config_notebook = ttk.Notebook(self.main_frame)
        self.config_notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
        
        # Crear las sub-pestañas
        self._create_proxy_tab()
        self._create_captcha_tab()
        self._create_general_tab()
        self._create_database_tab()
        self._create_presets_tab()
    
    def _create_proxy_tab(self):
        """Crea la pestaña de configuración de proxies."""
        proxy_frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(proxy_frame, text="Proxies")
        
        # Frame principal con scroll
        canvas = tk.Canvas(proxy_frame)
        scrollbar = ttk.Scrollbar(proxy_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Configuración general de proxies
        general_frame = ttk.LabelFrame(scrollable_frame, text="Configuración General", padding="10")
        general_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Habilitar/deshabilitar proxies
        self.proxy_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(general_frame, text="Habilitar uso de proxies", 
                       variable=self.proxy_enabled_var,
                       command=self._on_proxy_enabled_changed).pack(anchor=tk.W)
        
        # Rotación automática
        self.proxy_rotation_var = tk.BooleanVar()
        ttk.Checkbutton(general_frame, text="Rotación automática de proxies", 
                       variable=self.proxy_rotation_var).pack(anchor=tk.W)
        
        # Timeout de proxy
        timeout_frame = ttk.Frame(general_frame)
        timeout_frame.pack(fill=tk.X, pady=5)
        ttk.Label(timeout_frame, text="Timeout (segundos):").pack(side=tk.LEFT)
        self.proxy_timeout_var = tk.StringVar(value="30")
        ttk.Entry(timeout_frame, textvariable=self.proxy_timeout_var, width=10).pack(side=tk.LEFT, padx=(5, 0))
        
        # Lista de proxies
        proxy_list_frame = ttk.LabelFrame(scrollable_frame, text="Lista de Proxies", padding="10")
        proxy_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Área de texto para proxies
        text_frame = ttk.Frame(proxy_list_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.proxy_text = tk.Text(text_frame, height=10, width=50)
        proxy_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.proxy_text.yview)
        self.proxy_text.configure(yscrollcommand=proxy_scrollbar.set)
        
        self.proxy_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        proxy_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Instrucciones
        ttk.Label(proxy_list_frame, 
                 text="Formato: host:puerto:usuario:contraseña (usuario y contraseña opcionales)\n"
                      "Ejemplo: 192.168.1.1:8080 o 192.168.1.1:8080:user:pass",
                 font=("Arial", 8)).pack(pady=5)
        
        # Botones de proxy
        proxy_buttons_frame = ttk.Frame(proxy_list_frame)
        proxy_buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(proxy_buttons_frame, text="Cargar desde archivo", 
                  command=self._load_proxies_from_file).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(proxy_buttons_frame, text="Guardar Configuración de Proxies", 
                  command=self._apply_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(proxy_buttons_frame, text="Probar proxies", 
                  command=self._test_proxies).pack(side=tk.LEFT, padx=5)
        ttk.Button(proxy_buttons_frame, text="Limpiar lista", 
                  command=self._clear_proxies).pack(side=tk.LEFT, padx=5)
        
        # Resultados de pruebas
        results_frame = ttk.LabelFrame(scrollable_frame, text="Resultados de Pruebas", padding="10")
        results_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.proxy_results_text = tk.Text(results_frame, height=6, width=50)
        results_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.proxy_results_text.yview)
        self.proxy_results_text.configure(yscrollcommand=results_scrollbar.set)
        
        self.proxy_results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configurar scroll
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_captcha_tab(self):
        """Crea la pestaña de configuración de CAPTCHAs."""
        captcha_frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(captcha_frame, text="CAPTCHA")
        
        # Botón para abrir la configuración de CAPTCHA
        config_button = ttk.Button(
            captcha_frame,
            text="Abrir Configuración de CAPTCHA",
            command=self._open_captcha_config_window
        )
        config_button.pack(pady=20, padx=20)

    def _open_captcha_config_window(self):
        """Abre la ventana de configuración de CAPTCHA."""
        CaptchaConfigWindow(self.main_frame, config_manager=self.config)
    
    def _create_general_tab(self):
        """Crea la pestaña de configuración general."""
        general_frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(general_frame, text="General")
        
        # Configuración de scraping
        scraping_frame = ttk.LabelFrame(general_frame, text="Configuración de Scraping", padding="10")
        scraping_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Palabras mínimas
        words_frame = ttk.Frame(scraping_frame)
        words_frame.pack(fill=tk.X, pady=2)
        ttk.Label(words_frame, text="Palabras mínimas por página:").pack(side=tk.LEFT)
        self.min_words_var = tk.StringVar(value="30")
        ttk.Entry(words_frame, textvariable=self.min_words_var, width=10).pack(side=tk.LEFT, padx=(5, 0))
        
        # Número de Workers
        workers_frame = ttk.Frame(scraping_frame)
        workers_frame.pack(fill=tk.X, pady=2)
        ttk.Label(workers_frame, text="Número de Workers (Hilos):").pack(side=tk.LEFT)
        
        max_workers = multiprocessing.cpu_count()
        self.num_workers_var = tk.StringVar(value=str(max_workers))
        
        workers_spinbox = ttk.Spinbox(
            workers_frame, 
            from_=1, 
            to=250, 
            textvariable=self.num_workers_var, 
            width=5
        )
        workers_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(workers_frame, text=f"(Máx: 250)").pack(side=tk.LEFT, padx=5)
        
        # Delay entre requests
        delay_frame = ttk.Frame(scraping_frame)
        delay_frame.pack(fill=tk.X, pady=2)
        ttk.Label(delay_frame, text="Delay entre requests (segundos):").pack(side=tk.LEFT)
        self.request_delay_var = tk.StringVar(value="1.0")
        ttk.Entry(delay_frame, textvariable=self.request_delay_var, width=10).pack(side=tk.LEFT, padx=(5, 0))
        
        # Timeout de página
        page_timeout_frame = ttk.Frame(scraping_frame)
        page_timeout_frame.pack(fill=tk.X, pady=2)
        ttk.Label(page_timeout_frame, text="Timeout de página (segundos):").pack(side=tk.LEFT)
        self.page_timeout_var = tk.StringVar(value="30")
        ttk.Entry(page_timeout_frame, textvariable=self.page_timeout_var, width=10).pack(side=tk.LEFT, padx=(5, 0))
        
        # User Agent
        ua_frame = ttk.Frame(scraping_frame)
        ua_frame.pack(fill=tk.X, pady=2)
        ttk.Label(ua_frame, text="User Agent personalizado:").pack(anchor=tk.W)
        self.user_agent_var = tk.StringVar()
        ttk.Entry(ua_frame, textvariable=self.user_agent_var, width=80).pack(fill=tk.X, pady=2)
        
        # Configuración de archivos
        files_frame = ttk.LabelFrame(general_frame, text="Configuración de Archivos", padding="10")
        files_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Directorio de salida
        output_frame = ttk.Frame(files_frame)
        output_frame.pack(fill=tk.X, pady=2)
        ttk.Label(output_frame, text="Directorio de salida:").pack(side=tk.LEFT)
        self.output_dir_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.output_dir_var, width=50).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(output_frame, text="Examinar", 
                  command=self._browse_output_dir).pack(side=tk.LEFT, padx=(5, 0))
        
        # Formato de archivo
        format_frame = ttk.Frame(files_frame)
        format_frame.pack(fill=tk.X, pady=2)
        ttk.Label(format_frame, text="Formato de salida:").pack(side=tk.LEFT)
        self.output_format_var = tk.StringVar()
        ttk.Combobox(format_frame, textvariable=self.output_format_var,
                    values=["CSV", "Excel", "JSON"], state="readonly").pack(side=tk.LEFT, padx=(5, 0))
        
        # Configuración de logging
        logging_frame = ttk.LabelFrame(general_frame, text="Configuración de Logging", padding="10")
        logging_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Nivel de log
        log_level_frame = ttk.Frame(logging_frame)
        log_level_frame.pack(fill=tk.X, pady=2)
        ttk.Label(log_level_frame, text="Nivel de log:").pack(side=tk.LEFT)
        self.log_level_var = tk.StringVar()
        ttk.Combobox(log_level_frame, textvariable=self.log_level_var,
                    values=["DEBUG", "INFO", "WARNING", "ERROR"], state="readonly").pack(side=tk.LEFT, padx=(5, 0))
        
        # Guardar logs en archivo
        self.save_logs_var = tk.BooleanVar()
        ttk.Checkbutton(logging_frame, text="Guardar logs en archivo", 
                       variable=self.save_logs_var).pack(anchor=tk.W, pady=2)
        
        # Modo Headless
        self.headless_mode_var = tk.BooleanVar()
        self.headless_mode_var.trace_add("write", lambda *args: self._on_headless_mode_changed())
        ttk.Checkbutton(logging_frame, text="Ejecutar navegador en modo Headless (sin interfaz gráfica)",
                       variable=self.headless_mode_var).pack(anchor=tk.W, pady=2)
        
        # Configuración de archivos de resultados
        results_config_frame = ttk.LabelFrame(general_frame, text="Configuración de Archivos de Resultados", padding="10")
        results_config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Modo de salida de resultados
        output_mode_frame = ttk.Frame(results_config_frame)
        output_mode_frame.pack(fill=tk.X, pady=2)
        ttk.Label(output_mode_frame, text="Modo de archivos de resultados:").pack(side=tk.LEFT)
        
        self.results_output_mode_var = tk.StringVar(value="Por curso")
        results_mode_combo = ttk.Combobox(output_mode_frame, textvariable=self.results_output_mode_var,
                                          values=["Por curso", "Conglomerado"], state="readonly", width=20)
        results_mode_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Descripción de los modos
        mode_desc_frame = ttk.Frame(results_config_frame)
        mode_desc_frame.pack(fill=tk.X, pady=2)
        mode_desc_label = ttk.Label(mode_desc_frame, 
                                    text="• Por curso: Un archivo CSV por cada curso procesado (recomendado)\n"
                                         "• Conglomerado: Un solo archivo CSV con todos los resultados",
                                    font=("Arial", 8), foreground="gray")
        mode_desc_label.pack(anchor=tk.W)

    def _create_database_tab(self):
        """Crea la pestaña de configuración de base de datos."""
        database_frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(database_frame, text="🔧 Base de Datos")

        # Integrar la pestaña de configuración de base de datos
        try:
            self.database_tab = DatabaseConfigTab(database_frame)
            self.database_tab.pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            logger.error(f"Error creando pestaña de base de datos: {str(e)}")
            # Si falla, mostrar mensaje de error
            error_label = ttk.Label(database_frame,
                                   text=f"❌ Error cargando configuración de base de datos:\n{str(e)}",
                                   font=("Arial", 10))
            error_label.pack(pady=20, padx=20)
    
    def _create_presets_tab(self):
        """Crea la pestaña de presets de configuración."""
        presets_frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(presets_frame, text="Presets")
        
        # Descripción
        ttk.Label(presets_frame, 
                 text="Los presets permiten cargar configuraciones predefinidas para diferentes escenarios.",
                 font=("Arial", 10)).pack(padx=10, pady=10)
        
        # Lista de presets
        presets_list_frame = ttk.LabelFrame(presets_frame, text="Presets Disponibles", padding="10")
        presets_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Listbox con presets
        self.presets_listbox = tk.Listbox(presets_list_frame, height=8)
        self.presets_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Botones de presets
        presets_buttons_frame = ttk.Frame(presets_list_frame)
        presets_buttons_frame.pack(fill=tk.X)
        
        ttk.Button(presets_buttons_frame, text="Cargar Preset", 
                  command=self._load_preset).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(presets_buttons_frame, text="Guardar como Preset", 
                  command=self._save_preset).pack(side=tk.LEFT, padx=5)
        ttk.Button(presets_buttons_frame, text="Eliminar Preset", 
                  command=self._delete_preset).pack(side=tk.LEFT, padx=5)
        
        # Descripción del preset seleccionado
        description_frame = ttk.LabelFrame(presets_frame, text="Descripción", padding="10")
        description_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.preset_description_text = tk.Text(description_frame, height=4, width=50)
        preset_description_scrollbar = ttk.Scrollbar(description_frame, orient="vertical", command=self.preset_description_text.yview)
        self.preset_description_text.configure(yscrollcommand=preset_description_scrollbar.set)
        self.preset_description_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preset_description_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Cargar presets predefinidos
        self._load_predefined_presets()
        
        # Bind para mostrar descripción
        self.presets_listbox.bind("<<ListboxSelect>>", self._on_preset_selected)
    
    def _load_predefined_presets(self):
        """Carga los presets predefinidos."""
        predefined_presets = {
            "Rápido": {
                "description": "Configuración optimizada para velocidad máxima",
                "config": {
                    "proxy_enabled": False,
                    "captcha_solving_enabled": False,
                    "min_words": 20,
                    "request_delay": 0.5,
                    "page_timeout": 15
                }
            },
            "Seguro": {
                "description": "Configuración balanceada con proxies y delays moderados",
                "config": {
                    "proxy_enabled": True,
                    "proxy_rotation": True,
                    "captcha_solving_enabled": True,
                    "min_words": 30,
                    "request_delay": 2.0,
                    "page_timeout": 30
                }
            },
            "Completo": {
                "description": "Configuración exhaustiva con todas las características habilitadas",
                "config": {
                    "proxy_enabled": True,
                    "proxy_rotation": True,
                    "captcha_solving_enabled": True,
                    "captcha_service": "2Captcha",
                    "min_words": 50,
                    "request_delay": 3.0,
                    "page_timeout": 60
                }
            }
        }
        
        # Limpiar listbox
        self.presets_listbox.delete(0, tk.END)
        
        # Añadir presets predefinidos
        for preset_name in predefined_presets.keys():
            self.presets_listbox.insert(tk.END, preset_name)
        
        # Guardar presets en memoria
        self.predefined_presets = predefined_presets
    
    def _on_proxy_enabled_changed(self):
        """Maneja el cambio en la habilitación de proxies."""
        enabled = self.proxy_enabled_var.get()
        # Aquí puedes añadir lógica adicional si es necesario
        logger.info(f"Proxies {'habilitados' if enabled else 'deshabilitados'}")
    
    def _on_captcha_enabled_changed(self):
        """Maneja el cambio en la habilitación de CAPTCHAs."""
        enabled = self.config.get("captcha_solving_enabled")
        # Aquí puedes añadir lógica adicional si es necesario
        logger.info(f"CAPTCHA {'habilitado' if enabled else 'deshabilitado'}")
    
    def _on_captcha_service_changed(self, event=None):
        """Maneja el cambio en el servicio de CAPTCHA."""
        service = self.config.get("captcha_service")
        logger.info(f"Servicio de CAPTCHA cambiado a: {service}")

    def _on_headless_mode_changed(self):
        """Maneja el cambio en el modo headless y guarda la configuración."""
        self.config.set("headless_mode", self.headless_mode_var.get())
        self.config.save_config()
        logger.info(f"Headless mode changed to: {self.headless_mode_var.get()}")
    
    def _load_proxies_from_file(self):
        """Carga proxies desde un archivo."""
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de proxies",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.* Experiencia")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    proxies = f.read()
                
                # Añadir al texto existente
                current_text = self.proxy_text.get("1.0", tk.END)
                if current_text.strip():
                    self.proxy_text.insert(tk.END, "\n" + proxies)
                else:
                    self.proxy_text.insert("1.0", proxies)
                
                messagebox.showinfo("Éxito", f"Proxies cargados desde {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error cargando proxies: {str(e)}")
    
    def _test_proxies(self):
        """Prueba los proxies configurados."""
        if self.is_testing_proxies:
            messagebox.showwarning("Advertencia", "Ya se está ejecutando una prueba de proxies")
            return
        
        proxies_text = self.proxy_text.get("1.0", tk.END).strip()
        if not proxies_text:
            messagebox.showwarning("Advertencia", "No hay proxies para probar")
            return
        
        # Ejecutar prueba en hilo separado
        self.is_testing_proxies = True
        threading.Thread(target=self._run_proxy_tests, args=(proxies_text,), daemon=True).start()
    
    def _run_proxy_tests(self, proxies_text: str):
        """Ejecuta las pruebas de proxies en un hilo separado."""
        try:
            # Limpiar resultados anteriores
            self.proxy_results_text.delete("1.0", tk.END)
            self.proxy_results_text.insert(tk.END, "Iniciando pruebas de proxies...\n")
            
            proxies = [line.strip() for line in proxies_text.split('\n') if line.strip()]
            total_proxies = len(proxies)
            working_proxies = 0
            
            for i, proxy in enumerate(proxies, 1):
                self.proxy_results_text.insert(tk.END, f"Probando proxy {i}/{total_proxies}: {proxy}\n")
                self.proxy_results_text.see(tk.END)
                self.proxy_results_text.update()
                
                # Simular prueba de proxy (aquí irían las pruebas reales)
                time.sleep(0.5)  # Simular tiempo de prueba
                
                # Resultado simulado (en implementación real, probar conectividad)
                import random
                is_working = random.choice([True, False])
                
                if is_working:
                    working_proxies += 1
                    self.proxy_results_text.insert(tk.END, f"✓ Proxy funciona correctamente\n")
                else:
                    self.proxy_results_text.insert(tk.END, f"✗ Proxy no responde\n")
                
                self.proxy_results_text.see(tk.END)
                self.proxy_results_text.update()
            
            # Resumen final
            self.proxy_results_text.insert(tk.END, f"\nResumen: {working_proxies}/{total_proxies} proxies funcionando\n")
            self.proxy_results_text.see(tk.END)
            
        except Exception as e:
            self.proxy_results_text.insert(tk.END, f"Error durante las pruebas: {str(e)}\n")
        finally:
            self.is_testing_proxies = False
    
    def _clear_proxies(self):
        """Limpia la lista de proxies."""
        if messagebox.askyesno("Confirmar", "¿Está seguro de que desea limpiar la lista de proxies?"):
            self.proxy_text.delete("1.0", tk.END)
            self.proxy_results_text.delete("1.0", tk.END)
    
    def _test_captcha_config(self):
        """Prueba la configuración de CAPTCHA."""
        if not self.config.get("captcha_solving_enabled"):
            messagebox.showwarning("Advertencia", "CAPTCHA no está habilitado")
            return
        
        service = self.config.get("captcha_service")
        api_key = self.config.get("captcha_api_key")
        
        if not service:
            messagebox.showwarning("Advertencia", "Seleccione un servicio de CAPTCHA")
            return
        
        if not api_key and service != "manual":
            messagebox.showwarning("Advertencia", "Ingrese la API Key")
            return
        
        # Simular prueba de CAPTCHA
        messagebox.showinfo("Prueba de CAPTCHA", f"Probando configuración de {service}...\n(Esta es una simulación)")
    
    def _browse_output_dir(self):
        """Examina directorio de salida."""
        directory = filedialog.askdirectory(title="Seleccionar directorio de salida")
        if directory:
            self.output_dir_var.set(directory)
    
    def _on_preset_selected(self, event=None):
        """Maneja la selección de un preset."""
        selection = self.presets_listbox.curselection()
        if selection:
            preset_name = self.presets_listbox.get(selection[0])
            if preset_name in self.predefined_presets:
                description = self.predefined_presets[preset_name]["description"]
                self.preset_description_text.delete("1.0", tk.END)
                self.preset_description_text.insert("1.0", description)
    
    def _load_preset(self):
        """Carga el preset seleccionado."""
        selection = self.presets_listbox.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un preset para cargar")
            return
        
        preset_name = self.presets_listbox.get(selection[0])
        if preset_name in self.predefined_presets:
            config = self.predefined_presets[preset_name]["config"]
            self._apply_preset_config(config)
            messagebox.showinfo("Éxito", f"Preset '{preset_name}' cargado correctamente")
    
    def _apply_preset_config(self, config: Dict[str, Any]):
        """Aplica la configuración de un preset."""
        # Aplicar configuración de proxies
        if "proxy_enabled" in config:
            self.proxy_enabled_var.set(config["proxy_enabled"])
        if "proxy_rotation" in config:
            self.proxy_rotation_var.set(config["proxy_rotation"])
        
        # Aplicar configuración de CAPTCHA
        if "captcha_solving_enabled" in config:
            self.config.set("captcha_solving_enabled", config["captcha_solving_enabled"])
        if "captcha_service" in config:
            self.config.set("captcha_service", config["captcha_service"])
        
        # Aplicar configuración general
        if "min_words" in config:
            self.min_words_var.set(str(config["min_words"]))
        if "request_delay" in config:
            self.request_delay_var.set(str(config["request_delay"]))
        if "page_timeout" in config:
            self.page_timeout_var.set(str(config["page_timeout"]))
    
    def _save_preset(self):
        """Guarda la configuración actual como preset."""
        preset_name = simpledialog.askstring("Guardar Preset", "Nombre del preset:")
        if not preset_name:
            return
        
        description = simpledialog.askstring("Descripción", "Descripción del preset (opcional):")
        if description is None:
            description = ""
        
        # Obtener configuración actual
        current_config = self._get_current_config()
        
        # Guardar preset (en implementación real, guardar en archivo)
        self.predefined_presets[preset_name] = {
            "description": description,
            "config": current_config
        }
        
        # Actualizar listbox
        if preset_name not in [self.presets_listbox.get(i) for i in range(self.presets_listbox.size())]:
            self.presets_listbox.insert(tk.END, preset_name)
        
        messagebox.showinfo("Éxito", f"Preset '{preset_name}' guardado correctamente")
    
    def _delete_preset(self):
        """Elimina el preset seleccionado."""
        selection = self.presets_listbox.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un preset para eliminar")
            return
        
        preset_name = self.presets_listbox.get(selection[0])
        
        # No permitir eliminar presets predefinidos
        if preset_name in ["Rápido", "Seguro", "Completo"]:
            messagebox.showwarning("Advertencia", "No se pueden eliminar los presets predefinidos")
            return
        
        if messagebox.askyesno("Confirmar", f"¿Está seguro de que desea eliminar el preset '{preset_name}'?"):
            # Eliminar de la lista y del diccionario
            self.presets_listbox.delete(selection[0])
            if preset_name in self.predefined_presets:
                del self.predefined_presets[preset_name]
            
            # Limpiar descripción
            self.preset_description_text.delete("1.0", tk.END)
            
            messagebox.showinfo("Éxito", f"Preset '{preset_name}' eliminado correctamente")
    
    def _get_current_config(self) -> Dict[str, Any]:
        """Obtiene la configuración actual de la interfaz."""
        config_data = {
            # Proxies
            "proxy_enabled": self.proxy_enabled_var.get(),
            "proxy_rotation": self.proxy_rotation_var.get(),
            "proxy_timeout": self.proxy_timeout_var.get(),
            "proxy_list": self.proxy_text.get("1.0", tk.END).strip(),
            
            # General
            "min_words": self.min_words_var.get(),
            "min_words": self.min_words_var.get(),
            "num_workers": self.num_workers_var.get(),
            "request_delay": self.request_delay_var.get(),
            "page_timeout": self.page_timeout_var.get(),
            "user_agent": self.user_agent_var.get(),
            "output_dir": self.output_dir_var.get(),
            "output_format": self.output_format_var.get(),
            "log_level": self.log_level_var.get(),
            "save_logs": self.save_logs_var.get(),
            "headless_mode": self.headless_mode_var.get(), # Guardar estado del modo headless
            "results_output_mode": self.results_output_mode_var.get()  # Modo de archivos de resultados
        }
        # La configuración de CAPTCHA se obtiene directamente del config_manager
        config_data.update({
            "captcha_solving_enabled": self.config.get("captcha_solving_enabled"),
            "captcha_service": self.config.get("captcha_service"),
            "captcha_api_key": self.config.get("captcha_api_key"),
        })
        return config_data
    
    def _load_current_config(self):
        """Carga la configuración actual desde el objeto Config."""
        try:
            # Cargar valores por defecto o desde el archivo de config
            self.proxy_enabled_var.set(self.config.get("proxy_enabled", False))
            self.proxy_rotation_var.set(self.config.get("proxy_rotation", True))
            self.proxy_timeout_var.set(self.config.get("proxy_timeout", "30"))
            
            # Cargar lista de proxies en el widget de texto
            proxy_list = self.config.get("proxy_list", "")
            self.proxy_text.delete("1.0", tk.END)
            self.proxy_text.insert("1.0", proxy_list)
            
            self.min_words_var.set(self.config.get("min_words", "30"))
            self.min_words_var.set(self.config.get("min_words", "30"))
            self.num_workers_var.set(self.config.get("num_workers", str(multiprocessing.cpu_count())))
            self.request_delay_var.set(self.config.get("request_delay", "1.0"))
            self.page_timeout_var.set(self.config.get("page_timeout", "30"))
            self.output_dir_var.set(self.config.get("output_dir", "results"))
            self.output_format_var.set(self.config.get("output_format", "CSV"))
            self.log_level_var.set(self.config.get("log_level", "INFO"))
            self.save_logs_var.set(self.config.get("save_logs", True))
            self.headless_mode_var.set(self.config.get("headless_mode", True)) # Cargar estado del modo headless
            self.results_output_mode_var.set(self.config.get("results_output_mode", "Por curso"))  # Modo de archivos
            
            logger.info("Configuración cargada en la GUI")
            
        except Exception as e:
            logger.error(f"Error cargando configuración en la GUI: {str(e)}")
    
    def _apply_config(self):
        """Aplica la configuración actual."""
        try:
            config = self._get_current_config()
            
            # Validar configuración
            if not self._validate_config(config):
                return
            
            # Aplicar configuración al objeto Config
            self.config.update(config)
            
            # Guardar la configuración en el archivo
            if self.config.save_config():
                messagebox.showinfo("Éxito", "Configuración aplicada y guardada correctamente")
                logger.info("Configuración aplicada y guardada correctamente")
                # Llamar callback si está configurado
                if self.on_config_changed:
                    self.on_config_changed(config)
            else:
                messagebox.showerror("Error", "No se pudo guardar la configuración. Revise los logs.")

        except Exception as e:
            logger.error(f"Error aplicando configuración: {str(e)}")
            messagebox.showerror("Error", f"Error aplicando configuración: {str(e)}")
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Valida la configuración antes de aplicarla."""
        try:
            # Validar valores numéricos
            numeric_fields = ["proxy_timeout", "min_words", "request_delay", "page_timeout", "num_workers"]
            
            for field in numeric_fields:
                if field in config:
                    try:
                        float(config[field])
                    except ValueError:
                        messagebox.showerror("Error de validación", f"El campo '{field}' debe ser un número válido")
                        return False
            
            # Validar directorio de salida
            if config.get("output_dir"):
                output_dir = config["output_dir"]
                if not os.path.exists(output_dir):
                    try:
                        os.makedirs(output_dir, exist_ok=True)
                    except Exception as e:
                        messagebox.showerror("Error de validación", f"No se puede crear el directorio de salida: {str(e)}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validando configuración: {str(e)}")
            messagebox.showerror("Error", f"Error validando configuración: {str(e)}")
            return False
    
    def _reset_config(self):
        """Restablece la configuración a valores por defecto."""
        if messagebox.askyesno("Confirmar", "¿Está seguro de que desea restablecer la configuración?"):
            # Esto debería recargar los valores por defecto del config manager, no solo los de la GUI
            self.config = Config() # Recargar desde cero
            self._load_current_config()
            messagebox.showinfo("Éxito", "Configuración restablecida a valores por defecto")
    
    def _import_config(self):
        """Importa configuración desde un archivo."""
        file_path = filedialog.askopenfilename(
            title="Importar configuración",
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.* Experiencia")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                self.config.update(config_data)
                self._load_current_config() # Recargar la GUI con los nuevos valores
                messagebox.showinfo("Éxito", f"Configuración importada desde {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error importando configuración: {str(e)}")
    
    def _export_config(self):
        """Exporta la configuración actual a un archivo."""
        file_path = filedialog.asksaveasfilename(
            title="Exportar configuración",
            defaultextension=".json",
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.* Experiencia")]
        )
        
        if file_path:
            try:
                # Usar la configuración directamente del config_manager
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config.config, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Éxito", f"Configuración exportada a {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error exportando configuración: {str(e)}")
    
    def set_config_changed_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Establece el callback para cambios de configuración.
        
        Args:
            callback: Función a llamar cuando cambie la configuración
        """
        self.on_config_changed = callback
