"""
Styles
------
Estilos para la interfaz gráfica.
"""

import tkinter as tk
from tkinter import ttk, font

def apply_styles(widget=None):
    """Configura estilos personalizados para mejorar la accesibilidad."""
    style = ttk.Style()
    
    # Forzar el tema 'clam' que permite personalización de colores
    if 'clam' in style.theme_names():
        style.theme_use('clam')

    # Crear fuentes más grandes para mejor legibilidad
    default_font = font.nametofont("TkDefaultFont")
    default_font.configure(size=12)
    
    text_font = font.nametofont("TkTextFont")
    text_font.configure(size=12)
    
    # --- ESTILOS DE BOTONES ---
    # Estilo general para botones (azul oscuro con letras blancas)
    # Este será el estilo por defecto para TButton
    style.configure("TButton", 
                    font=("Arial", 12, "bold"), 
                    padding=8, 
                    foreground="white", 
                    background="#191970",  # Azul oscuro
                    borderwidth=1)
    style.map("TButton",
            foreground=[('pressed', 'white'), 
                        ('active', 'white'),
                        ('disabled', '#a9a9a9')], # Color de texto para estado deshabilitado
            background=[('pressed', '#00008B'), # Azul más oscuro al presionar
                        ('active', '#0000CD'), # Azul medio al pasar el ratón
                        ('disabled', '#d3d3d3')]) # Color de fondo para estado deshabilitado

    # Estilo para el botón de iniciar (verde)
    style.configure("Start.TButton", 
                    font=("Arial", 12, "bold"), 
                    padding=8, 
                    foreground="white", 
                    background="#28a745") # Verde
    style.map("Start.TButton",
            foreground=[('pressed', 'white'), ('active', 'white')],
            background=[('pressed', '#218838'), ('active', '#2ebf4f')])

    # Estilo para el botón de detener (rojo)
    style.configure("Stop.TButton", 
                    font=("Arial", 12, "bold"), 
                    padding=8, 
                    foreground="white", 
                    background="#dc3545") # Rojo
    style.map("Stop.TButton",
            foreground=[('pressed', 'white'), ('active', 'white')],
            background=[('pressed', '#c82333'), ('active', '#e44d5a')])

    # --- OTROS ESTILOS ---
    style.configure("TLabel", font=("Arial", 12), padding=5)
    style.configure("TCheckbutton", font=("Arial", 12), padding=5)
    style.configure("TLabelframe.Label", font=("Arial", 12, "bold"))
    style.configure("TLabelframe", padding=10)
    style.configure("Heading.TLabel", font=("Arial", 16, "bold"), padding=10)
    style.configure("Status.TLabel", font=("Arial", 12), padding=5)
    style.configure("CourseInfo.TLabel", font=("Arial", 14, "bold"), padding=5)
    style.configure("Timer.TLabel", font=("Arial", 16, "bold"), padding=5)
    style.configure("Stats.TLabel", font=("Arial", 12), padding=5)
    
    # Configurar colores para mejor contraste
    style.configure("TLabel", foreground="#000000", background="#f0f0f0")
    style.configure("TLabelframe", background="#f0f0f0")
    style.configure("TLabelframe.Label", foreground="#000000", background="#f0f0f0")
    
    # Configurar estilo para el PanedWindow
    style.configure("TPanedwindow", background="#f0f0f0")
    
    # Estilo para el texto de procesamiento
    style.configure("Processing.TLabel", font=("Arial", 14, "bold"), padding=5)
    
    # Estilo para el texto de tabulación (rojo)
    style.configure("Tabulating.TLabel", font=("Arial", 14, "bold"), foreground="#FF0000", padding=5)
    
    # Estilo para los logs
    style.configure("Log.TText", font=("Consolas", 10), background="#ffffff", foreground="#333333")
    
    # Estilo para botones de acento (si se usa)
    style.configure("Accent.TButton", font=("Arial", 12, "bold"), padding=8, 
                   background="#4a86e8", foreground="#ffffff")
    style.map("Accent.TButton",
             foreground=[('pressed', '#ffffff'), ('active', '#ffffff')],
             background=[('pressed', '#3a76d8'), ('active', '#5a96f8')])
    
    # Si se proporciona un widget, aplicar recursivamente a todos los hijos
    if widget:
        for child in widget.winfo_children():
            apply_styles(child)

# Mantener setup_styles como alias para compatibilidad con código existente
setup_styles = apply_styles