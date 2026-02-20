"""
Search Configuration Tab
-----------------------
Pestaña para configuración avanzada de búsqueda (Broad vs Exact).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, Any

from utils.config import Config

logger = logging.getLogger(__name__)

class SearchConfigTab:
    """
    Pestaña de configuración avanzada de búsqueda.
    Permite alternar entre modo 'Broad' (Aspiradora) y 'Exact'.
    """
    
    def __init__(self, parent_notebook: ttk.Notebook, config: Config):
        self.config = config
        self.parent_notebook = parent_notebook
        
        # Frame principal
        self.main_frame = ttk.Frame(parent_notebook)
        parent_notebook.add(self.main_frame, text="Búsqueda Avanzada")
        
        self._create_interface()
        self._load_current_config()
        
    def _create_interface(self):
        """Crea los widgets de la interfaz."""
        
        # --- Panel de Modo de Búsqueda ---
        # --- Panel de Motor de Búsqueda ---
        engine_frame = ttk.LabelFrame(self.main_frame, text="Motor de Búsqueda", padding="15")
        engine_frame.pack(fill=tk.X, padx=15, pady=5)
        
        self.search_engine_var = tk.StringVar(value="Cordis Europa API")
        
        engine_combo = ttk.Combobox(
            engine_frame, 
            textvariable=self.search_engine_var,
            values=["Cordis Europa API", "Cordis Europa", "Google", "Bing", "DuckDuckGo", "Common Crawl", "Wayback Machine"],
            state="readonly",
            font=("Arial", 10)
        )
        engine_combo.pack(fill=tk.X, pady=5)
        
        # --- Panel de Modo de Búsqueda ---
        mode_frame = ttk.LabelFrame(self.main_frame, text="Modo de Búsqueda", padding="15")
        mode_frame.pack(fill=tk.X, padx=15, pady=15)
        
        self.search_mode_var = tk.StringVar(value="broad")
        
        # Opción BROAD (Default)
        ttk.Radiobutton(
            mode_frame, 
            text="Búsqueda Amplia (RECOMENDADO)", 
            variable=self.search_mode_var, 
            value="broad"
        ).pack(anchor=tk.W, pady=5)
        
        ttk.Label(
            mode_frame, 
            text="   • Usa lógica OR (trae resultados si aparece CUALQUIER palabra).\n   • Maximiza la cantidad de resultados.\n   • Ideal para barridos masivos.",
            foreground="#666666",
            font=("Arial", 9)
        ).pack(anchor=tk.W, padx=20, pady=(0, 10))
        
        # Opción EXACT
        ttk.Radiobutton(
            mode_frame, 
            text="Búsqueda Exacta (Estricta)", 
            variable=self.search_mode_var, 
            value="exact"
        ).pack(anchor=tk.W, pady=5)
        
        ttk.Label(
            mode_frame, 
            text="   • Usa lógica AND (deben aparecer TODAS las palabras).\n   • Resultados muy precisos pero menor volumen.\n   • Úsalo si obtienes demasiada basura.",
            foreground="#666666",
            font=("Arial", 9)
        ).pack(anchor=tk.W, padx=20, pady=(0, 5))

        # --- Panel de Filtrado de Contenido ---
        filter_frame = ttk.LabelFrame(self.main_frame, text="Filtrado de Contenido", padding="15")
        filter_frame.pack(fill=tk.X, padx=15, pady=5)
        
        self.require_keywords_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(
            filter_frame, 
            text="Requerir palabras clave en el texto extraído", 
            variable=self.require_keywords_var
        ).pack(anchor=tk.W)
        
        ttk.Label(
            filter_frame, 
            text="Si se activa, descartará documentos donde no encuentre las palabras clave en el cuerpo del texto.\nSi se desactiva (recomendado para volumen), solo usará el filtro de 'Palabras mínimas'.",
            foreground="#666666",
            font=("Arial", 9),
            wraplength=600
        ).pack(anchor=tk.W, padx=20, pady=5)

        # --- Botón de Guardar ---
        save_btn = ttk.Button(self.main_frame, text="Guardar Configuración de Búsqueda", command=self._save_config)
        save_btn.pack(side=tk.BOTTOM, pady=20)

    def _load_current_config(self):
        """Carga valores desde config.json."""
        self.search_engine_var.set(self.config.get("search_engine", "Google"))
        self.search_mode_var.set(self.config.get("search_mode", "broad"))
        self.require_keywords_var.set(self.config.get("require_keywords", False))

    def _save_config(self):
        """Guarda valores en config.json."""
        self.config.set("search_engine", self.search_engine_var.get())
        self.config.set("search_mode", self.search_mode_var.get())
        self.config.set("require_keywords", self.require_keywords_var.get())
        
        if self.config.save_config():
            messagebox.showinfo("Éxito", "Configuración de búsqueda actualizada.")
        else:
            messagebox.showerror("Error", "No se pudo guardar la configuración.")
