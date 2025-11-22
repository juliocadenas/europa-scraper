#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
import sys
import os

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from client.scraper_client_gui import ScraperClientGUI
    print("Importación exitosa")
except Exception as e:
    print(f"Error en importación: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def test_gui():
    try:
        root = tk.Tk()
        root.title("Test GUI")
        root.geometry("800x600")
        
        # Crear un frame para probar la GUI
        test_frame = ttk.Frame(root)
        test_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Crear una instancia de la GUI
        print("Creando instancia de ScraperClientGUI...")
        gui = ScraperClientGUI(test_frame, None)
        gui.pack(fill=tk.BOTH, expand=True)
        print("GUI creada exitosamente")
        
        #root.mainloop()
        print("Test completado exitosamente")
        
    except Exception as e:
        print(f"Error al crear GUI: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gui()