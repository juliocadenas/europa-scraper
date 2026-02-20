#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar el botón de carga de cursos en la GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def probar_boton_cursos():
    """Función de prueba para verificar que el botón es visible y funcional"""
    
    # Crear ventana de prueba
    root = tk.Tk()
    root.title("Prueba Botón Cargar Cursos")
    root.geometry("600x400")
    
    # Frame principal
    main_frame = ttk.Frame(root, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Título
    title_label = ttk.Label(main_frame, text="PRUEBA - Botón Cargar Cursos", style="Heading.TLabel")
    title_label.pack(pady=20)
    
    # Botón de prueba (idéntico al del GUI principal)
    load_courses_button = ttk.Button(
        main_frame,
        text="📁 CARGAR CURSOS (CSV/XLS)",
        command=lambda: messagebox.showinfo("Éxito", "¡El botón funciona correctamente!"),
        width=50
    )
    load_courses_button.pack(fill=tk.X, pady=10, ipadx=20, ipady=10)
    
    # Información
    info_text = """
    Este es un script de prueba para verificar que el botón
    de carga de cursos es visible y funcional.
    
    Si puedes ver este botón y hacer clic en él,
    entonces el problema está en otro lugar del código.
    
    Pasos para probar en el sistema principal:
    1. Ejecutar: cd client && python main.py
    2. Buscar el botón en la pestaña Principal
    3. Debe estar visible debajo del título
    """
    
    info_label = ttk.Label(main_frame, text=info_text, justify=tk.LEFT)
    info_label.pack(pady=20)
    
    # Botón para salir
    exit_button = ttk.Button(main_frame, text="Salir", command=root.destroy)
    exit_button.pack(pady=10)
    
    print("✅ Ventana de prueba creada")
    print("📁 El botón 'CARGAR CURSOS (CSV/XLS)' debe ser visible")
    print("🔍 Si puedes ver el botón aquí, el problema está en el código principal")
    
    root.mainloop()

if __name__ == "__main__":
    probar_boton_cursos()