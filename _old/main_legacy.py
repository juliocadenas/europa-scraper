#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
USA.gov CSV Scraper - Aplicación Principal
==========================================
Scraper avanzado para extraer datos de sitios web gubernamentales.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
import threading
import time
import logging
from pathlib import Path
import asyncio
import subprocess

# Añadir el directorio actual al path para importaciones
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar módulos del proyecto
from utils.logger import setup_logger
from utils.instance_checker import ensure_single_instance
from utils.admin_check import check_admin_privileges
from controllers.scraper_controller import ScraperController
from utils.proxy_manager import ProxyManager
from utils.config import Config

# Configurar logging primero
setup_logger(log_level=logging.INFO)
logger = logging.getLogger('main')

def configure_pandas_memory():
    """Configura pandas para usar menos memoria"""
    try:
        import pandas as pd
        # Configurar pandas para usar menos memoria
        pd.options.mode.chained_assignment = None  # default='warn'
        # Limitar el número de hilos que pandas puede usar
        pd.set_option('compute.use_numexpr', False)
        # Usar menos precisión para ahorrar memoria
        pd.set_option('display.precision', 2)
        logger.info("Pandas configurado para usar menos memoria")
    except Exception as e:
        logger.warning(f"No se pudo configurar pandas: {e}")

def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler to log unhandled exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't log keyboard interrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
        
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Show error message to user
    error_msg = f"An unexpected error occurred:\n{exc_type.__name__}: {exc_value}"
    messagebox.showerror("Application Error", error_msg)

def install_browsers():
    """Install Playwright browsers"""
    try:
        print("Installing Playwright browsers...")
        
        # Set environment variable for Playwright browsers
        browsers_path = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), 'playwright_browsers')
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browsers_path
        
        # Create the browsers directory if it doesn't exist
        os.makedirs(browsers_path, exist_ok=True)
        
        # Install only Chromium browser to save space and time
        subprocess.run(
            [sys.executable, '-m', 'playwright', 'install', 'chromium'],
            check=True
        )
        
        print("Playwright browsers installed successfully")
        return True
    except Exception as e:
        print(f"Error installing Playwright browsers: {e}")
        return False

def main():
    """Función principal de la aplicación."""
    try:
        # Verificar si estamos en un entorno empaquetado
        if getattr(sys, 'frozen', False):
            # Estamos en un ejecutable empaquetado
            application_path = os.path.dirname(sys.executable)
        else:
            # Estamos ejecutando desde código fuente
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        # Cambiar al directorio de la aplicación
        os.chdir(application_path)
        
        logger.info("Iniciando USA.gov CSV Scraper...")
        logger.info(f"Directorio de trabajo: {application_path}")
        
        # Ensure required directories exist
        required_dirs = ["data", "logs", "results", "omitidos"]
        for directory in required_dirs:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")
        
        # Set global exception handler
        sys.excepthook = handle_exception
        
        # Check if we're being asked to install browsers
        if len(sys.argv) > 1 and sys.argv[1] == '--install-browsers':
            success = install_browsers()
            sys.exit(0 if success else 1)
        
        # Ensure only one instance is running - con mejor manejo de errores
        try:
            if not ensure_single_instance():
                logger.warning("Another instance is already running. Exiting.")
                messagebox.showwarning("Application Running", 
                                      "Another instance of the application is already running.")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error checking for single instance: {e}")
            # Continuar de todos modos, mejor que fallar completamente
        
        # Check for admin privileges (optional)
        if not check_admin_privileges():
            logger.warning("Application running without admin privileges")
        
        # Configurar pandas para usar menos memoria
        configure_pandas_memory()
        
        # Verificar si es la primera ejecución
        temp_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "usagov_scraper")
        install_state_file = os.path.join(temp_dir, "install_state.txt")

        # Si no existe el archivo de estado, ejecutar el launcher primero
        if not os.path.exists(install_state_file):
            logger.info("Primera ejecución detectada, iniciando launcher...")
            
            # Buscar el launcher
            launcher_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.py")
            
            if os.path.exists(launcher_path):
                try:
                    # Ejecutar el launcher y esperar a que termine
                    subprocess.run([sys.executable, launcher_path], check=True)
                except Exception as e:
                    logger.error(f"Error al ejecutar launcher: {e}")
            else:
                logger.warning("No se encontró el launcher.py")
                
                # Crear el archivo de estado para evitar bucles
                os.makedirs(temp_dir, exist_ok=True)
                with open(install_state_file, "w") as f:
                    f.write("installed=true\n")
                    f.write(f"install_date={time.ctime()}\n")
        
        # Create the main application window
        root = tk.Tk()
        root.title("CORDIS Europa CSV Scraper")
        root.geometry("1000x700")
        root.minsize(800, 600)
        
        # Configurar fuentes predeterminadas para mejor accesibilidad
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=12)
        
        text_font = font.nametofont("TkTextFont")
        text_font.configure(size=12)
        
        # Configurar el color de fondo de la ventana principal
        root.configure(background="#f0f0f0")
        
        # Inicializar el gestor de configuración
        config = Config()

        # Inicializar el gestor de proxies primero
        proxy_manager = ProxyManager()
        
        # Create controller and set proxy manager
        controller = ScraperController(config_manager=config)
        controller.set_proxy_manager(proxy_manager)
        
        # Import ScraperGUI here to avoid circular imports
        from gui.scraper_gui import ScraperGUI
        
        # Create and initialize GUI
        app = ScraperGUI(root, controller=controller)
        app.pack(fill=tk.BOTH, expand=True)
        
        # Start the application
        try:
            logger.info("Starting main application loop")
            root.mainloop()
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            # Clean up resources
            logger.info("Application shutting down")

    except ImportError as e:
        error_msg = f"Error importando módulos: {e}\n\nAsegúrese de que todos los archivos necesarios estén presentes."
        logger.error(error_msg)
        messagebox.showerror("Error de Importación", error_msg)
        sys.exit(1)
        
    except Exception as e:
        error_msg = f"Error fatal en aplicación: {e}"
        logger.error(error_msg)
        messagebox.showerror("Error Fatal", error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()
