#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build Optimized Executable
--------------------------
Este script compila la aplicación en un único archivo ejecutable (.exe)
que incluye todas las dependencias y el navegador web.
Implementa verificación inteligente para evitar reinstalaciones innecesarias.
"""

import os
import sys
import shutil
import subprocess
import urllib.request
import zipfile
import tempfile
import time
import platform
from pathlib import Path
import json

# Configuración global
APP_NAME = "USAGov Scraper"
CONFIG_FILE = "build_config.json"
TEMP_DIR = os.path.join(tempfile.gettempdir(), "usagov_scraper_build")
BROWSER_ZIP = os.path.join(TEMP_DIR, "chromium-win64.zip")
BROWSER_URL = "https://cdn.playwright.dev/dbazure/download/playwright/builds/chromium/1161/chromium-win64.zip"

def load_config():
    """Carga la configuración de compilación o crea una nueva si no existe"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
    
    # Configuración por defecto
    return {
        "last_build": None,
        "browser_downloaded": False,
        "packages_created": False,
        "build_count": 0
    }

def save_config(config):
    """Guarda la configuración de compilación"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error al guardar configuración: {e}")
        return False

def download_file(url, output_path, force=False):
    """Descarga un archivo con barra de progreso simple"""
    if os.path.exists(output_path) and not force:
        print(f"Archivo ya existe: {output_path}")
        print("Omitiendo descarga. Use force=True para forzar la descarga.")
        return True
    
    print(f"Descargando desde: {url}")
    print(f"Guardando en: {output_path}")
    
    try:
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        def report_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, int(downloaded * 100 / total_size))
            sys.stdout.write(f"\rProgreso: {percent}%")
            sys.stdout.flush()
        
        # Descargar el archivo
        urllib.request.urlretrieve(url, output_path, reporthook=report_progress)
        print("\nDescarga completada!")
        return True
    except Exception as e:
        print(f"Error durante la descarga: {e}")
        return False

def create_smart_launcher():
    """Crea un script de lanzamiento inteligente que verifica componentes existentes"""
    launcher_code = '''
# -*- coding: utf-8 -*-
import os
import sys
import zipfile
import tempfile
import subprocess
import shutil
import time
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
import importlib.util
import json
import platform
import ctypes
import stat

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("launcher")

# Directorio de la aplicación
if getattr(sys, 'frozen', False):
    # Ejecutando como ejecutable compilado
    APP_DIR = os.path.dirname(sys.executable)
else:
    # Ejecutando como script
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Directorio temporal para extracciones
TEMP_DIR = os.path.join(tempfile.gettempdir(), "usagov_scraper")
BROWSER_DIR = os.path.join(TEMP_DIR, "browser")
PLAYWRIGHT_DIR = os.path.join(TEMP_DIR, "playwright_browsers")
PACKAGES_DIR = os.path.join(TEMP_DIR, "packages")
CONFIG_FILE = os.path.join(TEMP_DIR, "launcher_config.json")

def is_admin():
    """Verifica si el script se está ejecutando con privilegios de administrador"""
    try:
        if platform.system() == "Windows":
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except:
        return False

def run_as_admin():
    """Reinicia el script con privilegios de administrador"""
    try:
        if platform.system() == "Windows":
            if sys.executable.endswith("pythonw.exe"):
                executable = sys.executable.replace("pythonw.exe", "python.exe")
            else:
                executable = sys.executable
            
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", executable, " ".join(sys.argv), None, 1
            )
        else:
            # En sistemas Unix, usar sudo
            os.system(f'sudo "{sys.executable}" "{" ".join(sys.argv)}"')
        return True
    except Exception as e:
        logger.error(f"Error al intentar ejecutar como administrador: {e}")
        return False

def set_full_permissions(path):
    """Establece permisos completos en un archivo o directorio"""
    try:
        if os.path.isfile(path):
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | 
                          stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | 
                          stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)
        else:
            for root, dirs, files in os.walk(path):
                for d in dirs:
                    try:
                        os.chmod(os.path.join(root, d), stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | 
                                                      stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | 
                                                      stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)
                    except:
                        pass
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | 
                                                      stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | 
                                                      stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)
                    except:
                        pass
    except Exception as e:
        logger.warning(f"No se pudieron establecer permisos en {path}: {e}")

def ensure_dir(directory):
    """Asegura que un directorio exista"""
    os.makedirs(directory, exist_ok=True)
    set_full_permissions(directory)
    return directory

def load_config():
    """Carga la configuración o crea una nueva si no existe"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    """Guarda la configuración"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def extract_browser(zip_data, target_dir, progress_callback=None):
    """Extrae el navegador desde los datos binarios del zip"""
    try:
        # Crear directorio temporal para extraer el zip
        temp_zip = os.path.join(tempfile.gettempdir(), "chromium_temp.zip")
        
        # Escribir los datos del zip a un archivo temporal
        with open(temp_zip, 'wb') as f:
            f.write(zip_data)
        
        # Extraer el zip
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            total_files = len(zip_ref.infolist())
            extracted_files = 0
            
            for file in zip_ref.infolist():
                zip_ref.extract(file, target_dir)
                extracted_files += 1
                if progress_callback:
                    progress = int((extracted_files / total_files) * 100)
                    progress_callback(progress)
        
        # Eliminar el archivo temporal
        os.remove(temp_zip)
        return True
    except Exception as e:
        logger.error(f"Error extracting browser: {e}")
        return False

def extract_packages(packages_data, target_dir, progress_callback=None):
    """Extrae los paquetes Python desde los datos binarios del zip"""
    try:
        # Crear directorio temporal para extraer el zip
        temp_zip = os.path.join(tempfile.gettempdir(), "packages_temp.zip")
        
        # Escribir los datos del zip a un archivo temporal
        with open(temp_zip, 'wb') as f:
            f.write(packages_data)
        
        # Extraer el zip
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            total_files = len(zip_ref.infolist())
            extracted_files = 0
            
            for file in zip_ref.infolist():
                zip_ref.extract(file, target_dir)
                extracted_files += 1
                if progress_callback:
                    progress = int((extracted_files / total_files) * 100)
                    progress_callback(progress)
        
        # Eliminar el archivo temporal
        os.remove(temp_zip)
        return True
    except Exception as e:
        logger.error(f"Error extracting packages: {e}")
        return False

def setup_playwright_browser(progress_callback=None):
    """Configura Playwright para usar el navegador extraído"""
    try:
        if progress_callback:
            progress_callback(10, "Preparando directorios...")
        
        # Crear directorios para Playwright
        chromium_dir = os.path.join(PLAYWRIGHT_DIR, "chromium-1161")
        os.makedirs(chromium_dir, exist_ok=True)
        
        # También crear la estructura alternativa que Playwright podría buscar
        chromium_headless_dir = os.path.join(PLAYWRIGHT_DIR, "chromium_headless_shell-1161")
        os.makedirs(chromium_headless_dir, exist_ok=True)
        
        if progress_callback:
            progress_callback(20, "Copiando archivos del navegador...")
        
        # Fuente: navegador extraído
        chrome_win_source = os.path.join(BROWSER_DIR, "chrome-win")
        
        # Destinos para Playwright
        chrome_win_target1 = os.path.join(chromium_dir, "chrome-win")
        chrome_win_target2 = os.path.join(chromium_headless_dir, "chrome-win")
        
        # Si los destinos ya existen, eliminarlos
        if os.path.exists(chrome_win_target1):
            try:
                if os.path.islink(chrome_win_target1):
                    os.unlink(chrome_win_target1)
                else:
                    shutil.rmtree(chrome_win_target1)
            except Exception as e:
                logger.error(f"Error removing existing browser dir 1: {e}")
        
        if os.path.exists(chrome_win_target2):
            try:
                if os.path.islink(chrome_win_target2):
                    os.unlink(chrome_win_target2)
                else:
                    shutil.rmtree(chrome_win_target2)
            except Exception as e:
                logger.error(f"Error removing existing browser dir 2: {e}")
        
        # Copiar archivos a ambas ubicaciones
        if progress_callback:
            progress_callback(30, "Copiando archivos a ubicación principal...")
        
        # Contar archivos para mostrar progreso
        total_files = sum([len(files) for _, _, files in os.walk(chrome_win_source)])
        
        # Copiar a la primera ubicación con progreso
        copied_files = 0
        for root, dirs, files in os.walk(chrome_win_source):
            rel_path = os.path.relpath(root, chrome_win_source)
            target_dir = os.path.join(chrome_win_target1, rel_path)
            os.makedirs(target_dir, exist_ok=True)
            
            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_dir, file)
                shutil.copy2(src_file, dst_file)
                copied_files += 1
                if progress_callback and total_files > 0:
                    progress = 30 + int((copied_files / total_files) * 30)  # 30% a 60%
                    progress_callback(progress, f"Copiando archivos: {copied_files}/{total_files}")
        
        if progress_callback:
            progress_callback(60, "Copiando archivos a ubicación alternativa...")
        
        # Copiar a la segunda ubicación con progreso
        copied_files = 0
        for root, dirs, files in os.walk(chrome_win_source):
            rel_path = os.path.relpath(root, chrome_win_source)
            target_dir = os.path.join(chrome_win_target2, rel_path)
            os.makedirs(target_dir, exist_ok=True)
            
            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_dir, file)
                shutil.copy2(src_file, dst_file)
                copied_files += 1
                if progress_callback and total_files > 0:
                    progress = 60 + int((copied_files / total_files) * 30)  # 60% a 90%
                    progress_callback(progress, f"Copiando archivos alternativos: {copied_files}/{total_files}")
        
        if progress_callback:
            progress_callback(90, "Configurando ejecutables...")
        
        # Crear headless_shell.exe si no existe
        headless_shell_exe1 = os.path.join(chrome_win_target1, "headless_shell.exe")
        chrome_exe1 = os.path.join(chrome_win_target1, "chrome.exe")
        
        headless_shell_exe2 = os.path.join(chrome_win_target2, "headless_shell.exe")
        chrome_exe2 = os.path.join(chrome_win_target2, "chrome.exe")
        
        if os.path.exists(chrome_exe1) and not os.path.exists(headless_shell_exe1):
            try:
                shutil.copy2(chrome_exe1, headless_shell_exe1)
                logger.info(f"Created headless_shell.exe at {headless_shell_exe1}")
            except Exception as e:
                logger.error(f"Error creating headless_shell.exe 1: {e}")
        
        if os.path.exists(chrome_exe2) and not os.path.exists(headless_shell_exe2):
            try:
                shutil.copy2(chrome_exe2, headless_shell_exe2)
                logger.info(f"Created headless_shell.exe at {headless_shell_exe2}")
            except Exception as e:
                logger.error(f"Error creating headless_shell.exe 2: {e}")
        
        # Configurar variable de entorno para Playwright
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = PLAYWRIGHT_DIR
        logger.info(f"Set PLAYWRIGHT_BROWSERS_PATH to {PLAYWRIGHT_DIR}")
        
        if progress_callback:
            progress_callback(100, "Configuración de navegador completada.")
        
        # Verificar que todo esté correcto
        if os.path.exists(os.path.join(chrome_win_target1, "chrome.exe")) or \
           os.path.exists(os.path.join(chrome_win_target2, "chrome.exe")):
            logger.info(f"Browser successfully set up")
            return True
        else:
            logger.error(f"Browser setup failed, chrome.exe not found")
            return False
    except Exception as e:
        logger.error(f"Error setting up Playwright browser: {e}")
        return False

def check_chrome_installed():
    """Verifica si Chrome está instalado en el sistema"""
    try:
        # Buscar Chrome en ubicaciones comunes
        chrome_path = None
        if platform.system() == "Windows":
            possible_paths = [
                os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Google\\Chrome\\Application\\chrome.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Google\\Chrome\\Application\\chrome.exe'),
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google\\Chrome\\Application\\chrome.exe'),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
        
            # Si no encontramos Chrome en las rutas comunes, intentar encontrarlo con where
            if not chrome_path:
                try:
                    result = subprocess.run(['where', 'chrome'], capture_output=True, text=True, check=False)
                    if result.returncode == 0 and result.stdout.strip():
                        chrome_path = result.stdout.strip().split('\\n')[0]
                except Exception:
                    pass
        
        if chrome_path:
            logger.info(f"Chrome found at: {chrome_path}")
            return True, chrome_path
        else:
            logger.info("Chrome not found on system")
            return False, None
    except Exception as e:
        logger.error(f"Error checking Chrome: {e}")
        return False, None

def install_playwright_manually():
    """Instala manualmente los componentes de Playwright"""
    try:
        logger.info("Installing Playwright components manually...")
        
        # URLs de los componentes de Playwright
        chromium_url = "https://playwright.azureedge.net/builds/chromium/1161/chromium-win64.zip"
        
        # Directorios de destino
        chromium_dir = os.path.join(PLAYWRIGHT_DIR, "chromium-1161")
        
        os.makedirs(chromium_dir, exist_ok=True)
        
        # Descargar y extraer Chromium
        chromium_zip = os.path.join(tempfile.gettempdir(), "chromium-win64.zip")
        logger.info(f"Downloading Chromium from {chromium_url}...")
        
        try:
            # Usar urllib para descargar
            import urllib.request
            urllib.request.urlretrieve(chromium_url, chromium_zip)
            
            # Extraer el archivo
            logger.info("Extracting Chromium...")
            with zipfile.ZipFile(chromium_zip, "r") as zip_ref:
                zip_ref.extractall(chromium_dir)
            
            # Establecer permisos
            set_full_permissions(chromium_dir)
        except Exception as e:
            logger.error(f"Error downloading/extracting Chromium: {e}")
        
        # Limpiar archivos temporales
        try:
            os.remove(chromium_zip)
        except:
            pass
        
        logger.info("Playwright components installed manually")
        return True
    except Exception as e:
        logger.error(f"Error installing Playwright components manually: {e}")
        return False

def check_dependencies():
    """Verifica que todas las dependencias estén disponibles"""
    required_modules = [
        'pandas', 'playwright', 'aiohttp', 'asyncio', 'PIL', 
        'openpyxl', 'PyPDF2', 'pdfminer.six', 'docx', 'pptx', 'chardet'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            if module == 'PIL':
                importlib.import_module('PIL')
            else:
                importlib.import_module(module)
        except ImportError:
            missing_modules.append(module)
    
    return missing_modules

def get_browser_data():
    """Obtiene los datos binarios del navegador desde el recurso"""
    # Esta función será reemplazada durante la compilación
    # con el código real que extrae los datos del navegador
    return b''  # Placeholder

def get_packages_data():
    """Obtiene los datos binarios de los paquetes Python desde el recurso"""
    # Esta función será reemplazada durante la compilación
    # con el código real que extrae los datos de los paquetes
    return b''  # Placeholder

def get_main_code():
    """Obtiene el código del script principal"""
    # Esta función será reemplazada durante la compilación
    # con el código real del script principal
    return ""  # Placeholder

def setup_environment(show_ui=True):
    """Configura el entorno para la aplicación"""
    # Cargar configuración
    config = load_config()
    
    # Verificar si ya está configurado
    if config.get("setup_complete", False):
        # Verificar que los archivos realmente existan
        chrome_path = os.path.join(PLAYWRIGHT_DIR, "chromium-1161", "chrome-win", "chrome.exe")
        if os.path.exists(chrome_path):
            logger.info("Environment already set up, skipping setup")
            
            # Configurar variable de entorno para Playwright
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = PLAYWRIGHT_DIR
            
            # Añadir directorio de paquetes al path si existe
            if os.path.exists(PACKAGES_DIR):
                if PACKAGES_DIR not in sys.path:
                    sys.path.insert(0, PACKAGES_DIR)
            
            return True
    
    # Si llegamos aquí, necesitamos configurar el entorno
    if show_ui:
        return show_setup_window()
    else:
        try:
            # Crear directorios necesarios
            ensure_dir(TEMP_DIR)
            ensure_dir(BROWSER_DIR)
            ensure_dir(PLAYWRIGHT_DIR)
            ensure_dir(PACKAGES_DIR)
            
            # Extraer el navegador si no existe
            chrome_path = os.path.join(PLAYWRIGHT_DIR, "chromium-1161", "chrome-win", "chrome.exe")
            if not os.path.exists(chrome_path):
                browser_data = get_browser_data()
                if browser_data:
                    logger.info("Extracting browser...")
                    if not extract_browser(browser_data, BROWSER_DIR):
                        logger.error("Error extracting browser. Trying manual installation...")
                        install_playwright_manually()
                else:
                    # Intentar usar Chrome instalado
                    chrome_installed, chrome_path = check_chrome_installed()
                    if chrome_installed:
                        logger.info(f"Using installed Chrome: {chrome_path}")
                        os.environ["CHROME_EXECUTABLE_PATH"] = chrome_path
                    else:
                        logger.error("No browser data and no Chrome installed")
                        return False
            
            # Configurar Playwright
            setup_playwright_browser()
            
            # Extraer los paquetes si no existen
            if not os.path.exists(os.path.join(PACKAGES_DIR, "pandas")):
                packages_data = get_packages_data()
                if packages_data:
                    logger.info("Extracting Python packages...")
                    extract_packages(packages_data, PACKAGES_DIR)
            
            # Configurar variables de entorno
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = PLAYWRIGHT_DIR
            
            # Añadir el directorio de paquetes al path
            if PACKAGES_DIR not in sys.path:
                sys.path.insert(0, PACKAGES_DIR)
            
            # Crear directorios de datos necesarios
            for data_dir in ["data", "logs", "results", "omitidos"]:
                dir_path = os.path.join(APP_DIR, data_dir)
                ensure_dir(dir_path)
            
            # Guardar configuración
            config["setup_complete"] = True
            config["setup_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_config(config)
            
            return True
        except Exception as e:
            logger.error(f"Error setting up environment: {e}")
            return False

def show_setup_window():
    """Muestra una ventana de configuración mientras se configura el entorno"""
    try:
        root = tk.Tk()
        root.title("USAGov Scraper - Configuración")
        root.geometry("500x250")
        root.resizable(False, False)
        
        # Centrar la ventana
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Añadir elementos a la ventana
        label = tk.Label(root, text="Configurando el entorno (primera ejecución)...", font=("Arial", 12))
        label.pack(pady=20)
        
        progress = ttk.Progressbar(root, mode="determinate", length=400)
        progress.pack(pady=10)
        
        status_label = tk.Label(root, text="Iniciando configuración...", font=("Arial", 10))
        status_label.pack(pady=10)
        
        # Variable para controlar el estado de la configuración
        setup_complete = threading.Event()
        setup_success = [False]  # Lista para poder modificarla desde el hilo
        
        # Función para actualizar la interfaz
        def update_progress(value, text=None):
            try:
                progress["value"] = value
                if text:
                    status_label.config(text=text)
                root.update()
            except:
                pass
        
        # Función para cerrar la ventana
        def close_window():
            try:
                root.destroy()
            except:
                pass
        
        # Función para configurar el entorno en segundo plano
        def setup_thread():
            try:
                # Crear directorios necesarios
                update_progress(5, "Creando directorios temporales...")
                ensure_dir(TEMP_DIR)
                ensure_dir(BROWSER_DIR)
                ensure_dir(PLAYWRIGHT_DIR)
                ensure_dir(PACKAGES_DIR)
                
                # Verificar si Chrome está instalado
                update_progress(10, "Verificando navegador instalado...")
                chrome_installed, chrome_path = check_chrome_installed()
                
                if chrome_installed:
                    update_progress(15, f"Chrome encontrado: {chrome_path}")
                    os.environ["CHROME_EXECUTABLE_PATH"] = chrome_path
                else:
                    # Extraer el navegador
                    update_progress(15, "Extrayendo navegador web...")
                    browser_data = get_browser_data()
                    if browser_data:
                        extract_success = extract_browser(browser_data, BROWSER_DIR, 
                                                        lambda v: update_progress(v, f"Extrayendo navegador: {v}%"))
                        if not extract_success:
                            update_progress(30, "Error al extraer navegador. Intentando instalación manual...")
                            install_playwright_manually()
                    else:
                        update_progress(30, "No se encontraron datos del navegador. Intentando instalación manual...")
                        install_playwright_manually()
                
                # Configurar Playwright
                update_progress(40, "Configurando navegador para Playwright...")
                setup_playwright_browser(
                    lambda v, t: update_progress(v, t)
                )
                
                # Extraer los paquetes
                update_progress(70, "Verificando bibliotecas Python...")
                if not os.path.exists(os.path.join(PACKAGES_DIR, "pandas")):
                    packages_data = get_packages_data()
                    if packages_data:
                        update_progress(75, "Extrayendo bibliotecas Python...")
                        extract_packages(packages_data, PACKAGES_DIR,
                                        lambda v: update_progress(75 + int(v * 0.15), f"Extrayendo bibliotecas: {v}%"))
                
                # Configurar variables de entorno
                update_progress(90, "Configurando variables de entorno...")
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = PLAYWRIGHT_DIR
                
                # Añadir el directorio de paquetes al path
                if PACKAGES_DIR not in sys.path:
                    sys.path.insert(0, PACKAGES_DIR)
                
                # Crear directorios de datos necesarios
                update_progress(95, "Configurando directorios de datos...")
                for data_dir in ["data", "logs", "results", "omitidos"]:
                    dir_path = os.path.join(APP_DIR, data_dir)
                    ensure_dir(dir_path)
                
                # Guardar configuración
                config = load_config()
                config["setup_complete"]= True
                config["setup_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
                save_config(config)
                
                update_progress(100, "Configuración completada. Iniciando aplicación...")
                time.sleep(1)
                
                setup_success[0] = True
            except Exception as e:
                import traceback
                error_msg = f"Error durante la configuración: {str(e)}\n{traceback.format_exc()}"
                logger.error(error_msg)
                update_progress(100, "Error durante la configuración.")
                try:
                    messagebox.showerror("Error", error_msg)
                except:
                    pass
            finally:
                setup_complete.set()
        
        # Iniciar el hilo de configuración
        threading.Thread(target=setup_thread, daemon=True).start()
        
        # Esperar a que termine la configuración
        def check_setup_complete():
            if setup_complete.is_set():
                root.after(500, close_window)
            else:
                root.after(100, check_setup_complete)
        
        root.after(100, check_setup_complete)
        
        # Iniciar el bucle principal
        root.mainloop()
        
        return setup_success[0]
    except Exception as e:
        logger.error(f"Error in setup window: {e}")
        return False

def main():
    """Función principal del lanzador"""
    try:
        logger.info("Starting USAGov Scraper")
        
        # Verificar si se necesitan permisos de administrador
        if not is_admin():
            logger.info("Running without admin privileges")
            
            # Intentar crear/acceder a los directorios temporales
            try:
                os.makedirs(TEMP_DIR, exist_ok=True)
                
                # Probar escritura
                test_file = os.path.join(TEMP_DIR, "test_write.tmp")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
            except PermissionError:
                logger.warning("Admin privileges required to access temp directories")
                
                # Preguntar al usuario si desea ejecutar como administrador
                try:
                    if messagebox.askyesno(
                        "Permisos de Administrador",
                        "Se requieren privilegios de administrador para acceder a los directorios temporales. "
                        "¿Desea reiniciar la aplicación con privilegios de administrador?"
                    ):
                        if run_as_admin():
                            logger.info("Application restarted with admin privileges")
                            return
                        else:
                            logger.error("Failed to restart with admin privileges")
                except:
                    # Si no se puede mostrar el cuadro de diálogo, intentar reiniciar directamente
                    if run_as_admin():
                        return
        
        # Configurar el entorno
        setup_success = setup_environment()
        
        if not setup_success:
            logger.error("Failed to set up environment")
            try:
                messagebox.showerror(
                    "Error",
                    "No se pudo configurar el entorno correctamente. "
                    "La aplicación podría no funcionar correctamente."
                )
            except:
                pass
        
        # Verificar dependencias
        missing_modules = check_dependencies()
        if missing_modules:
            logger.warning(f"Missing modules: {', '.join(missing_modules)}")
            try:
                messagebox.showwarning(
                    "Dependencias Faltantes",
                    f"Faltan algunas bibliotecas Python: {', '.join(missing_modules)}.\n"
                    "La aplicación intentará continuar, pero podría no funcionar correctamente."
                )
            except:
                pass
        
        # Ejecutar la aplicación principal
        if getattr(sys, 'frozen', False):
            # Si estamos en un ejecutable congelado, ejecutar el código principal directamente
            # Importar el módulo main y ejecutar su función principal
            sys.path.insert(0, APP_DIR)
            logger.info(f"Importing main module from {APP_DIR}")
            
            # Crear directorios necesarios
            for directory in ["data", "logs", "results", "omitidos"]:
                ensure_dir(os.path.join(APP_DIR, directory))
            
            # Importar y ejecutar el módulo principal
            try:
                # Primero intentar importar el módulo main
                import main as main_module
                main_module.main()
            except ImportError:
                # Si no se puede importar, intentar cargar desde el código almacenado
                main_code = get_main_code()
                if main_code:
                    # Guardar el código en un archivo temporal
                    main_file = os.path.join(TEMP_DIR, "main.py")
                    with open(main_file, "w", encoding="utf-8") as f:
                        f.write(main_code)
                    
                    # Importar desde el archivo temporal
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("main", main_file)
                    main_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(main_module)
                    main_module.main()
                else:
                    raise ImportError("No se pudo encontrar o cargar el módulo principal")
        else:
            # Si estamos ejecutando como script, lanzar el script principal
            main_script = os.path.join(APP_DIR, "main.py")
            logger.info(f"Running main script at {main_script}")
            subprocess.run([sys.executable, main_script])
    
    except Exception as e:
        import traceback
        error_msg = f"Error al iniciar la aplicación: {str(e)}\n\n{traceback.format_exc()}"
        logger.error(error_msg)
        
        try:
            # Intentar mostrar un mensaje de error gráfico
            messagebox.showerror("Error", error_msg)
        except:
            # Si falla, mostrar en consola
            print(error_msg)
        
        # Esperar antes de salir
        print("\nPresione Enter para salir...")
        input()
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    with open("smart_launcher.py", "w", encoding="utf-8") as f:
        f.write(launcher_code)
    
    return "smart_launcher.py"

def create_packages_zip():
    """Crea un archivo zip con los paquetes Python necesarios"""
    config = load_config()
    
    # Verificar si ya se creó el paquete de bibliotecas
    packages_zip = os.path.join(TEMP_DIR, "usagov_scraper_packages.zip")
    if os.path.exists(packages_zip) and config.get("packages_created", False):
        print(f"Usando paquete de bibliotecas existente: {packages_zip}")
        with open(packages_zip, 'rb') as f:
            packages_data = f.read()
        return packages_data
    
    print("Creando paquete de bibliotecas Python...")
    
    # Crear directorio temporal para los paquetes
    packages_dir = os.path.join(tempfile.gettempdir(), "usagov_scraper_packages")
    os.makedirs(packages_dir, exist_ok=True)
    
    # Lista de paquetes requeridos
    required_packages = [
        'pandas', 'playwright', 'aiohttp', 'asyncio', 'pillow', 
        'openpyxl', 'PyPDF2', 'pdfminer.six', 'python-docx', 'python-pptx', 'chardet'
    ]
    
    # Instalar paquetes en el directorio temporal
    print("Descargando e instalando paquetes Python...")
    subprocess.run([
        sys.executable, 
        "-m", 
        "pip", 
        "install",
        "--target", packages_dir,
        "--upgrade"
    ] + required_packages)
    
    # Crear archivo zip con los paquetes
    os.makedirs(os.path.dirname(packages_zip), exist_ok=True)
    
    print(f"Comprimiendo paquetes en {packages_zip}...")
    with zipfile.ZipFile(packages_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(packages_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, packages_dir)
                zipf.write(file_path, arcname)
    
    # Leer el archivo zip
    with open(packages_zip, 'rb') as f:
        packages_data = f.read()
    
    # Actualizar configuración
    config["packages_created"] = True
    save_config(config)
    
    # Limpiar
    try:
        shutil.rmtree(packages_dir)
    except:
        print("Advertencia: No se pudieron eliminar algunos archivos temporales.")
    
    print(f"Paquete de bibliotecas creado: {len(packages_data)/1024/1024:.2f} MB")
    return packages_data

def get_browser_data():
    """Obtiene los datos binarios del navegador"""
    config = load_config()
    
    # Verificar si ya se descargó el navegador
    if os.path.exists(BROWSER_ZIP) and config.get("browser_downloaded", False):
        print(f"Usando navegador descargado existente: {BROWSER_ZIP}")
        with open(BROWSER_ZIP, 'rb') as f:
            browser_data = f.read()
        return browser_data
    
    # Descargar el navegador
    print(f"Descargando navegador desde {BROWSER_URL}...")
    os.makedirs(os.path.dirname(BROWSER_ZIP), exist_ok=True)
    
    if download_file(BROWSER_URL, BROWSER_ZIP):
        with open(BROWSER_ZIP, 'rb') as f:
            browser_data = f.read()
        
        # Actualizar configuración
        config["browser_downloaded"] = True
        save_config(config)
        
        return browser_data
    else:
        print("Error: No se pudo descargar el navegador.")
        return None

def get_main_code():
    """Obtiene el código del script principal"""
    main_file = "main.py"
    if os.path.exists(main_file):
        with open(main_file, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def create_pyinstaller_spec(launcher_path):
    """Crea un archivo spec para PyInstaller"""
    print("Creando archivo spec para PyInstaller...")
    
    # Obtener la ruta del icono si existe
    icon_path = "resources/icon.ico" if os.path.exists("resources/icon.ico") else None
    icon_option = f", icon='{icon_path}'" if icon_path else ""
    
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{launcher_path}'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'controllers',
        'controllers.scraper_controller',
        'utils',
        'utils.csv_handler',
        'utils.url_processor',
        'utils.content_analyzer',
        'utils.text_sanitizer',
        'utils.logger',
        'utils.instance_checker',
        'utils.admin_check',
        'utils.config',
        'gui',
        'gui.scraper_gui',
        'gui.components',
        'gui.components.advanced_combobox',
        'gui.components.enhanced_combobox',
        'asyncio',
        'asyncio.events',
        'asyncio.queues',
        'playwright.async_api',
        'pandas',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'threading',
        'tempfile',
        'zipfile',
        'shutil',
        'main',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'openpyxl',
        'PyPDF2',
        'pdfminer.six',
        'docx',
        'pptx',
        'chardet',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Añadir todos los archivos de datos
a.datas += [
    ('data/class5_course_list.csv', 'data/class5_course_list.csv', 'DATA'),
]

# Añadir todos los módulos Python del proyecto
import os
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.py') and not file == '{launcher_path}':
            source_path = os.path.join(root, file)
            if source_path.startswith('./'):
                source_path = source_path[2:]
            elif source_path.startswith('.\\\\'):
                source_path = source_path[2:]
            elif source_path.startswith('\\\\'):
                source_path = source_path[1:]
            
            # Normalizar la ruta para PyInstaller
            source_path = source_path.replace('\\\\', '/')
            
            # Añadir el archivo a los datos
            a.datas += [(source_path, source_path, 'DATA')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='USAGovScraper_Optimized',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None{icon_option},
)
"""
    
    with open("USAGovScraper_Optimized.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    return "USAGovScraper_Optimized.spec"

def main():
    """Función principal"""
    try:
        print("\n" + "=" * 70)
        print("COMPILANDO EJECUTABLE OPTIMIZADO".center(70))
        print("=" * 70 + "\n")
        
        # Cargar configuración
        config = load_config()
        
        # Crear directorios temporales
        print("Creando directorios temporales...")
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        # Obtener datos del navegador
        browser_data = get_browser_data()
        if not browser_data:
            print("Error: No se pudo obtener el navegador.")
            return False
        
        # Crear paquete de bibliotecas Python
        packages_data = create_packages_zip()
        
        # Obtener código del script principal
        main_code = get_main_code()
        if not main_code:
            print("Advertencia: No se pudo obtener el código del script principal.")
        
        # Crear el script de lanzamiento inteligente
        print("Creando script de lanzamiento inteligente...")
        launcher_path = create_smart_launcher()
        
        # Modificar el script de lanzamiento para incluir los datos del navegador y paquetes
        print("Modificando script de lanzamiento para incluir recursos...")
        with open(launcher_path, "r", encoding="utf-8") as f:
            launcher_code = f.read()
        
        # Reemplazar las funciones placeholder con las funciones reales
        browser_data_func = f"""
def get_browser_data():
    \"\"\"Obtiene los datos binarios del navegador\"\"\"
    return {browser_data!r}  # Datos binarios del navegador
"""
        
        packages_data_func = f"""
def get_packages_data():
    \"\"\"Obtiene los datos binarios de los paquetes Python\"\"\"
    return {packages_data!r}  # Datos binarios de los paquetes
"""
        
        main_code_func = f"""
def get_main_code():
    \"\"\"Obtiene el código del script principal\"\"\"
    return {main_code!r}  # Código del script principal
"""
        
        # Reemplazar funciones placeholder
        launcher_code = launcher_code.replace(
            "def get_browser_data():\n    \"\"\"Obtiene los datos binarios del navegador desde el recurso\"\"\"\n    # Esta función será reemplazada durante la compilación\n    # con el código real que extrae los datos del navegador\n    return b''  # Placeholder",
            browser_data_func
        )
        
        launcher_code = launcher_code.replace(
            "def get_packages_data():\n    \"\"\"Obtiene los datos binarios de los paquetes Python desde el recurso\"\"\"\n    # Esta función será reemplazada durante la compilación\n    # con el código real que extrae los datos de los paquetes\n    return b''  # Placeholder",
            packages_data_func
        )
        
        launcher_code = launcher_code.replace(
            "def get_main_code():\n    \"\"\"Obtiene el código del script principal\"\"\"\n    # Esta función será reemplazada durante la compilación\n    # con el código real del script principal\n    return \"\"  # Placeholder",
            main_code_func
        )
        
        # Guardar el script modificado
        with open(launcher_path, "w", encoding="utf-8") as f:
            f.write(launcher_code)
        
        # Crear archivo spec para PyInstaller
        spec_file = create_pyinstaller_spec(launcher_path)
        
        # Compilar el ejecutable
        print("\nCompilando ejecutable optimizado...")
        subprocess.run([
            sys.executable, 
            "-m", 
            "PyInstaller",
            spec_file,
            "--clean",
        ])
        
        # Limpiar archivos temporales
        print("\nLimpiando archivos temporales...")
        try:
            os.remove(launcher_path)
        except:
            print("Advertencia: No se pudo eliminar el script de lanzamiento temporal.")
        
        # Verificar si el ejecutable se creó correctamente
        exe_path = os.path.join("dist", "USAGovScraper_Optimized.exe")
        if os.path.exists(exe_path):
            # Actualizar configuración
            config["last_build"] = time.strftime("%Y-%m-%d %H:%M:%S")
            config["build_count"] = config.get("build_count", 0) + 1
            save_config(config)
            
            print("\n" + "=" * 70)
            print("COMPILACIÓN EXITOSA".center(70))
            print("=" * 70)
            print(f"\nEjectable optimizado creado en: {os.path.abspath(exe_path)}")
            print("\nEste ejecutable incluye:")
            print("- La aplicación completa")
            print("- Todas las bibliotecas necesarias")
            print("- El navegador web Chromium")
            print("\nCaracterísticas:")
            print("- Verifica si el navegador ya está instalado antes de reinstalarlo")
            print("- Detecta Chrome instalado en el sistema como alternativa")
            print("- Maneja permisos de administrador automáticamente")
            print("- Interfaz gráfica para la configuración inicial")
            return True
        else:
            print("\n" + "=" * 70)
            print("ERROR EN LA COMPILACIÓN".center(70))
            print("=" * 70)
            print("\nNo se pudo crear el ejecutable. Revise los mensajes de error anteriores.")
            return False
    except Exception as e:
        import traceback
        print(f"\nError inesperado: {e}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    try:
        success = main()
        
        if not success:
            print("\nHubo errores durante el proceso. Revise los mensajes anteriores.")
        
        print("\nPresione Enter para salir...")
        input()
    except Exception as e:
        print(f"\nError inesperado: {e}")
        print("\nPresione Enter para salir...")
        input()
