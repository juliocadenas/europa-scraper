"""
GUI Components
-------------
Componentes reutilizables para la interfaz gráfica.
"""

import tkinter as tk
from tkinter import ttk, font

class ProgressFrame(ttk.LabelFrame):
    """Marco para mostrar el progreso del scraping."""
    
    def __init__(self, master, **kwargs):
        """Inicializa el marco de progreso."""
        super().__init__(master, text="Progreso", padding=10, **kwargs)
        
        # Barra de progreso
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self,
            orient=tk.HORIZONTAL,
            length=100,
            mode='determinate',
            variable=self.progress_var
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=10)

        # Configurar el estilo de la barra de progreso
        style = ttk.Style()
        style.configure("TProgressbar", 
                    background='green',
                    troughcolor='#f0f0f0',
                    thickness=20)
        self.progress_bar.configure(style="TProgressbar")
        
        # Etiqueta para mostrar el texto de búsqueda de cursos
        self.searching_var = tk.StringVar(value="")
        self.searching_label = ttk.Label(
            self,
            textvariable=self.searching_var,
            anchor=tk.W,
            style="Processing.TLabel",
            wraplength=500
        )
        self.searching_label.pack(fill=tk.X, padx=5, pady=5)
        
        # Etiqueta para mostrar el texto de procesamiento
        self.processing_var = tk.StringVar(value="")
        self.processing_label = ttk.Label(
            self,
            textvariable=self.processing_var,
            anchor=tk.W,
            style="Processing.TLabel",
            wraplength=500
        )
        self.processing_label.pack(fill=tk.X, padx=5, pady=5)
        
        # Crear un frame para las estadísticas
        self.stats_frame = ttk.Frame(self)
        self.stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Configurar grid para estadísticas en dos columnas
        self.stats_frame.columnconfigure(0, weight=1)
        self.stats_frame.columnconfigure(1, weight=1)

        # Etiquetas para las estadísticas
        self.saved_files_label = ttk.Label(
            self.stats_frame, 
            text="Archivos Tabulados: 0",
            style="Stats.TLabel"
        )
        self.saved_files_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.not_saved_files_label = ttk.Label(
            self.stats_frame, 
            text="Archivos Omitidos: 0",
            style="Stats.TLabel"
        )
        self.not_saved_files_label.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        self.errors_label = ttk.Label(
            self.stats_frame, 
            text="Errores: 0",
            style="Stats.TLabel"
        )
        self.errors_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        
        # Añadir etiqueta para la URL
        self.url_label = ttk.Label(
            self,
            text="URL:",
            anchor=tk.W,
            style="Stats.TLabel"
        )
        self.url_label.pack(fill=tk.X, padx=5, pady=5, anchor=tk.W)
    
    def update_progress(self, value, text=None):
        """Actualiza el valor de la barra de progreso y el texto asociado."""
        self.progress_var.set(value)
        if text:
            self.update_searching_text(text)
    
    def update_searching_text(self, text):
        """Actualiza el texto de búsqueda."""
        self.searching_var.set(text)
        
        # Cambiar el estilo según la fase
        if "Tabulando" in text or "Tabulados" in text:
            self.searching_label.configure(style="Tabulating.TLabel")
        else:
            self.searching_label.configure(style="Processing.TLabel")
    
    def update_processing_text(self, text):
        """Actualiza el texto de procesamiento."""
        self.processing_var.set(text)
    
    def update_url(self, url):
        """Actualiza la URL mostrada."""
        if url and url.strip():
            self.url_label.config(text=f"URL: {url}")
        else:
            self.url_label.config(text="URL:")
    
    def update_stats(self, saved, not_saved, errors):
        """Actualiza las estadísticas mostradas."""
        self.saved_files_label.config(text=f"Archivos Tabulados: {saved}")
        self.not_saved_files_label.config(text=f"Archivos Omitidos: {not_saved}")
        self.errors_label.config(text=f"Errores: {errors}")


class ResultsFrame(ttk.LabelFrame):
    """Marco para mostrar los resultados del scraping."""
    
    def __init__(self, master, **kwargs):
        """Inicializa el marco de resultados."""
        super().__init__(master, text="Resultados", padding=10, **kwargs)
        
        # Crear un frame para contener el texto y su scrollbar
        self.text_frame = ttk.Frame(self)
        self.text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Texto de resultados
        self.text = tk.Text(
            self.text_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 10),
            padx=10,
            pady=10,
            background="#ffffff",
            foreground="#000000"
        )
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar = ttk.Scrollbar(
            self.text_frame,
            orient=tk.VERTICAL,
            command=self.text.yview
        )
        self.text.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
        
        # Configurar etiquetas para el texto
        self.text.tag_configure("title", font=("Arial", 14, "bold"))
        self.text.tag_configure("url", font=("Arial", 12, "italic"), foreground="#0056b3")
        self.text.tag_configure("total_words", font=("Arial", 12))
        self.text.tag_configure("description", font=("Arial", 12))
        self.text.tag_configure("log", font=("Consolas", 10), foreground="#333333")
        self.text.tag_configure("log_info", font=("Consolas", 10), foreground="#0056b3")
        self.text.tag_configure("log_warning", font=("Consolas", 10), foreground="#ff9900")
        self.text.tag_configure("log_error", font=("Consolas", 10), foreground="#ff0000")
        self.text.tag_configure("log_phase", font=("Consolas", 11, "bold"), foreground="#009900")
    
    def add_log(self, log_entry):
        """Añade una entrada de log al área de resultados."""
        self.text.config(state=tk.NORMAL)
        
        # Determinar el tag a usar según el nivel de log
        tag = "log"
        if "INFO" in log_entry:
            tag = "log_info"
        elif "WARNING" in log_entry:
            tag = "log_warning"
        elif "ERROR" in log_entry:
            tag = "log_error"
        elif "===" in log_entry:  # Para las fases del proceso
            tag = "log_phase"
        
        # Insertar el log con el tag correspondiente
        self.text.insert(tk.END, f"{log_entry}\n", tag)
        
        # Desplazar automáticamente al final
        self.text.see(tk.END)
        
        self.text.config(state=tk.DISABLED)
    
    def display_results(self, results):
        """Muestra resultados en el widget de texto."""
        self.text.config(state=tk.NORMAL)
        
        # Añadir un separador antes de mostrar los resultados
        self.text.insert(tk.END, "\n" + "="*50 + "\n", "log_phase")
        self.text.insert(tk.END, "RESULTADOS FINALES\n", "log_phase")
        self.text.insert(tk.END, "="*50 + "\n\n", "log_phase")
        
        if not results:
            self.text.insert(tk.END, "No se encontraron resultados.\n", "description")
            self.text.config(state=tk.DISABLED)
            return
        
        for i, result in enumerate(results):
            title = result.get('title', 'Sin Título')
            description = result.get('description', 'Sin Descripción')
            url = result.get('url', 'Sin URL')
            total_words = result.get('total_words', 0)
        
            self.text.insert(tk.END, f"{i+1}. {title}\n", "title")
            self.text.insert(tk.END, f"Descripción: {description}\n", "description")
            self.text.insert(tk.END, f"URL: {url}\n", "url")
            self.text.insert(tk.END, f"Palabras significativas: {total_words}\n\n", "total_words")

        # Desplazar automáticamente al final
        self.text.see(tk.END)
        self.text.config(state=tk.DISABLED)
    
    def clear(self):
        """Limpia el widget de texto."""
        self.text.config(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        self.text.insert(tk.END, "Iniciando proceso de scraping...\n", "log_info")
        self.text.config(state=tk.DISABLED)


class ControlFrame(ttk.Frame):
    """Marco para los controles de la aplicación."""
    
    def __init__(self, master, on_start=None, on_stop=None, **kwargs):
        """Inicializa el marco de controles."""
        super().__init__(master, **kwargs)
        
        # Guardar callbacks
        self.on_start = on_start
        self.on_stop = on_stop
        
        # Estado de conexión al servidor
        self.server_connected = False
        
        # Crear marco de botones
        self.buttons_frame = ttk.Frame(self)
        self.buttons_frame.pack(fill=tk.X, pady=0)
        
        # Botones en dos filas para mejor visualización
        # Primera fila
        self.buttons_row1 = ttk.Frame(self.buttons_frame)
        self.buttons_row1.pack(fill=tk.X, pady=5)
        
        # Botón de inicio
        self.start_button = ttk.Button(
            self.buttons_row1,
            text="Iniciar Scraping",
            command=self._on_start_click,
            style="Start.TButton"
        )
        self.start_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        # Botón de detención
        self.stop_button = ttk.Button(
            self.buttons_row1,
            text="Detener",
            command=self._on_stop_click,
            state=tk.DISABLED,
            style="Stop.TButton"
        )
        self.stop_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
    
    def _on_start_click(self):
        """Maneja el clic del botón de inicio."""
        if self.on_start:
            self.on_start()
    
    def _on_stop_click(self):
        """Maneja el clic del botón de detención."""
        if self.on_stop:
            self.on_stop()
    
    def set_scraping_started(self):
        """Actualiza la interfaz cuando comienza el scraping."""
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Actualizar el texto del botón de inicio para indicar que está en ejecución
        self.start_button.config(text="Ejecutando...")
        
        # Deshabilitar la selección de códigos SIC durante el scraping
        if hasattr(self.master, 'from_sic_listbox'):
            self.master.from_sic_listbox.config(state=tk.DISABLED)
        if hasattr(self.master, 'to_sic_listbox'):
            self.master.to_sic_listbox.config(state=tk.DISABLED)

    def set_scraping_stopped(self):
        """Actualiza la interfaz cuando se detiene el scraping."""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # Restaurar el texto del botón de inicio
        self.start_button.config(text="Iniciar Búsqueda")
        
        # Habilitar la selección de códigos SIC
        if hasattr(self.master, 'from_sic_listbox'):
            self.master.from_sic_listbox.config(state=tk.NORMAL)
        if hasattr(self.master, 'to_sic_listbox'):
            self.master.to_sic_listbox.config(state=tk.NORMAL)



