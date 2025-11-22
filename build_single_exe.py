#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build Single Executable
-----------------------
Este script compila la aplicación en un único archivo ejecutable (.exe)
que incluye todas las dependencias y el navegador web.
"""

import os
import sys
import shutil
import subprocess
import urllib.request
import zipfile
import tempfile
import time
from pathlib import Path

def download_file(url, output_path):
    """Descarga un archivo con barra de progreso simple"""
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

def create_self_extracting_launcher():
    """Crea un script de lanzamiento que extrae el navegador si es necesario"""
    launcher_code = '''#!/usr/bin/env python3
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
from pathlib import Path
import threading
import logging
import importlib.util
import site
import json

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
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Directorio temporal para extracciones
TEMP_DIR = os.path.join(tempfile.gettempdir(), "usagov_scraper")
BROWSER_DIR = os.path.join(TEMP_DIR, "browser")
PLAYWRIGHT_DIR = os.path.join(TEMP_DIR, "playwright_browsers")
PACKAGES_DIR = os.path.join(TEMP_DIR, "packages")
CONFIG_FILE = os.path.join(TEMP_DIR, "config.json")

def ensure_dir(directory):
    """Asegura que un directorio exista"""
    os.makedirs(directory, exist_ok=True)
    return directory

def extract_browser(zip_data, target_dir, progress_callback=None):
    """Extrae el navegador desde los datos binarios del zip"""
    try:
        temp_zip = os.path.join(tempfile.gettempdir(), "chromium_temp.zip")
        
        with open(temp_zip, 'wb') as f:
            f.write(zip_data)
        
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            total_files = len(zip_ref.infolist())
            extracted_files = 0
            
            for file in zip_ref.infolist():
                zip_ref.extract(file, target_dir)
                extracted_files += 1
                if progress_callback:
                    progress = int((extracted_files / total_files) * 100)
                    progress_callback(progress)
        
        os.remove(temp_zip)
        return True
    except Exception as e:
        logger.error(f"Error extracting browser: {e}")
        return False

def extract_packages(packages_data, target_dir, progress_callback=None):
    """Extrae los paquetes Python desde los datos binarios del zip"""
    try:
        temp_zip = os.path.join(tempfile.gettempdir(), "packages_temp.zip")
        
        with open(temp_zip, 'wb') as f:
            f.write(packages_data)
        
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            total_files = len(zip_ref.infolist())
            extracted_files = 0
            
            for file in zip_ref.infolist():
                zip_ref.extract(file, target_dir)
                extracted_files += 1
                if progress_callback:
                    progress = int((extracted_files / total_files) * 100)
                    progress_callback(progress)
        
        os.remove(temp_zip)
        return True
    except Exception as e:
        logger.error(f"Error extracting packages: {e}")
        return False

def setup_browser():
    """Configura el navegador para Playwright"""
    playwright_chrome = os.path.join(PLAYWRIGHT_DIR, "chromium-1161", "chrome-win", "chrome.exe")
    
    config = load_config()
    
    if os.path.exists(playwright_chrome) and config.get("browser_setup_complete", False):
        logger.info(f"Browser already set up at: {playwright_chrome}")
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = PLAYWRIGHT_DIR
        return True
    
    root = tk.Tk()
    root.title("Configurando USAGov Scraper")
    root.geometry("500x200")
    root.resizable(False, False)
    
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    # LÍNEA ARREGLADA - SIN CARACTERES ESPECIALES Y CORRECTAMENTE CERRADA
    mensaje_texto = "Configurando el entorno (primera ejecucion)..." + chr(10) + "Esto puede tardar unos minutos."
    label = tk.Label(root, text=mensaje_texto, wraplength=480, justify="center", padx=10, pady=10, font=("Arial", 12))
    label.pack(pady=10)
    
    status_label = tk.Label(root, text="Preparando...", wraplength=480, justify="center", font=("Arial", 10))
    status_label.pack(pady=5)
    
    progress = ttk.Progressbar(root, orient="horizontal", length=450, mode="determinate")
    progress.pack(pady=10)
    
    def update_progress(value, status_text=None):
        progress["value"] = value
        if status_text:
            status_label.config(text=status_text)
        root.update()
    
    ensure_dir(TEMP_DIR)
    ensure_dir(BROWSER_DIR)
    ensure_dir(PLAYWRIGHT_DIR)
    ensure_dir(PACKAGES_DIR)
    ensure_dir(os.path.join(PLAYWRIGHT_DIR, "chromium-1161"))
    
    def setup_thread():
        try:
            setup_success = True
            
            update_progress(0, "Extrayendo navegador web...")
            browser_data = get_browser_data()
            if browser_data:
                browser_success = extract_browser(browser_data, BROWSER_DIR, 
                                                lambda v: update_progress(v, f"Extrayendo navegador: {v}%"))
                if not browser_success:
                    setup_success = False
                    update_progress(100, "Error al extraer el navegador.")
                    root.after(3000, root.destroy)
                    return
            else:
                setup_success = False
                update_progress(100, "Error: No se encontraron datos del navegador.")
                root.after(3000, root.destroy)
                return
            
            update_progress(0, "Configurando navegador para Playwright...")
            playwright_success = setup_playwright_browser(
                lambda v, t: update_progress(v, t)
            )
            if not playwright_success:
                setup_success = False
                update_progress(100, "Error al configurar Playwright.")
                root.after(3000, root.destroy)
                return
            
            packages_data = get_packages_data()
            if packages_data:
                update_progress(0, "Extrayendo bibliotecas Python...")
                packages_success = extract_packages(packages_data, PACKAGES_DIR,
                                                  lambda v: update_progress(v, f"Extrayendo bibliotecas: {v}%"))
                if not packages_success:
                    setup_success = False
                    update_progress(100, "Error al extraer bibliotecas Python.")
                    root.after(3000, root.destroy)
                    return
            
            update_progress(90, "Configurando directorios de datos...")
            for data_dir in ["data", "logs", "results", "omitidos"]:
                ensure_dir(os.path.join(APP_DIR, data_dir))
            
            if setup_success:
                config["browser_setup_complete"] = True
                config["packages_setup_complete"] = True
                config["setup_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
                save_config(config)
                
                update_progress(100, "Configuracion completada. Iniciando aplicacion...")
                root.after(2000, root.destroy)
            
        except Exception as e:
            logger.error(f"Error in setup thread: {e}")
            update_progress(100, f"Error inesperado: {str(e)}")
            root.after(5000, root.destroy)
    
    threading.Thread(target=setup_thread, daemon=True).start()
    root.mainloop()
    
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = PLAYWRIGHT_DIR
    
    if os.path.exists(PACKAGES_DIR):
        if PACKAGES_DIR not in sys.path:
            sys.path.insert(0, PACKAGES_DIR)
    
    return config.get("browser_setup_complete", False)

def setup_playwright_browser(progress_callback=None):
    """Configura Playwright para usar el navegador extraído"""
    try:
        if progress_callback:
            progress_callback(10, "Preparando directorios...")
        
        chromium_dir = os.path.join(PLAYWRIGHT_DIR, "chromium-1161")
        os.makedirs(chromium_dir, exist_ok=True)
        
        chromium_headless_dir = os.path.join(PLAYWRIGHT_DIR, "chromium_headless_shell-1161")
        os.makedirs(chromium_headless_dir, exist_ok=True)
        
        if progress_callback:
            progress_callback(20, "Copiando archivos del navegador...")
        
        chrome_win_source = os.path.join(BROWSER_DIR, "chrome-win")
        
        chrome_win_target1 = os.path.join(chromium_dir, "chrome-win")
        chrome_win_target2 = os.path.join(chromium_headless_dir, "chrome-win")
        
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
        
        if progress_callback:
            progress_callback(30, "Copiando archivos a ubicacion principal...")
        
        total_files = sum([len(files) for _, _, files in os.walk(chrome_win_source)])
        
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
                    progress = 30 + int((copied_files / total_files) * 30)
                    progress_callback(progress, f"Copiando archivos: {copied_files}/{total_files}")
        
        if progress_callback:
            progress_callback(60, "Copiando archivos a ubicacion alternativa...")
        
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
                    progress = 60 + int((copied_files / total_files) * 30)
                    progress_callback(progress, f"Copiando archivos alternativos: {copied_files}/{total_files}")
        
        if progress_callback:
            progress_callback(90, "Configurando ejecutables...")
        
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
        
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = PLAYWRIGHT_DIR
        logger.info(f"Set PLAYWRIGHT_BROWSERS_PATH to {PLAYWRIGHT_DIR}")
        
        if progress_callback:
            progress_callback(100, "Configuracion de navegador completada.")
        
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

def get_browser_data():
    """Obtiene los datos binarios del navegador desde el recurso"""
    return b''

def get_packages_data():
    """Obtiene los datos binarios de los paquetes Python desde el recurso"""
    return b''

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

def main():
    """Función principal"""
    try:
        logger.info("Starting USAGov Scraper")
        
        setup_success = setup_browser()
        
        if not setup_success:
            logger.error("Failed to set up browser. Application may not work correctly.")
            messagebox.showwarning(
                "Advertencia",
                "No se pudo configurar correctamente el navegador. La aplicacion podria no funcionar correctamente."
            )
        
        missing_modules = check_dependencies()
        if missing_modules:
            logger.warning(f"Missing modules: {', '.join(missing_modules)}")
            messagebox.showwarning(
                "Dependencias Faltantes",
                f"Faltan algunas bibliotecas Python: {', '.join(missing_modules)}.\\n"
                "La aplicacion intentara continuar, pero podria no funcionar correctamente."
            )
        
        if getattr(sys, 'frozen', False):
            sys.path.insert(0, APP_DIR)
            logger.info(f"Importing main module from {APP_DIR}")
            
            for directory in ["data", "logs", "results", "omitidos"]:
                ensure_dir(os.path.join(APP_DIR, directory))
            
            import main as main_module
            main_module.main()
        else:
            main_script = os.path.join(APP_DIR, "main.py")
            logger.info(f"Running main script at {main_script}")
            subprocess.run([sys.executable, main_script])
    
    except Exception as e:
        import traceback
        error_msg = f"Error al iniciar la aplicacion: {str(e)}\\n\\n{traceback.format_exc()}"
        logger.error(error_msg)
        
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Error", error_msg)
        except:
            print(error_msg)
        
        print("\\nPresione Enter para salir...")
        input()
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    with open("launcher.py", "w", encoding="utf-8") as f:
        f.write(launcher_code)
    
    return "launcher.py"

def create_packages_zip():
    """Crea un archivo zip con los paquetes Python necesarios"""
    print("Creando paquete de bibliotecas Python...")
    
    packages_dir = os.path.join(tempfile.gettempdir(), "usagov_scraper_packages")
    os.makedirs(packages_dir, exist_ok=True)
    
    required_packages = [
        'pandas', 'playwright', 'aiohttp', 'asyncio', 'pillow', 
        'openpyxl', 'PyPDF2', 'pdfminer.six', 'python-docx', 'python-pptx', 'chardet'
    ]
    
    print("Descargando e instalando paquetes Python...")
    subprocess.run([
        sys.executable, 
        "-m", 
        "pip", 
        "install",
        "--target", packages_dir,
        "--upgrade"
    ] + required_packages)
    
    packages_zip = os.path.join(tempfile.gettempdir(), "usagov_scraper_packages.zip")
    
    print(f"Comprimiendo paquetes en {packages_zip}...")
    with zipfile.ZipFile(packages_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(packages_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, packages_dir)
                zipf.write(file_path, arcname)
    
    with open(packages_zip, 'rb') as f:
        packages_data = f.read()
    
    try:
        shutil.rmtree(packages_dir)
        os.remove(packages_zip)
    except:
        print("Advertencia: No se pudieron eliminar algunos archivos temporales.")
    
    print(f"Paquete de bibliotecas creado: {len(packages_data)/1024/1024:.2f} MB")
    return packages_data

def main():
    """Función principal para compilar el ejecutable único"""
    print("\n" + "=" * 70)
    print("COMPILANDO EJECUTABLE TODO-EN-UNO".center(70))
    print("=" * 70 + "\n")
    
    print("Creando directorios temporales...")
    temp_dir = tempfile.mkdtemp(prefix="usagov_scraper_build_")
    os.makedirs(os.path.join(temp_dir, "browser"), exist_ok=True)
    
    chromium_zip = os.path.join(temp_dir, "browser", "chromium-win64.zip")
    if not os.path.exists(chromium_zip):
        print("Descargando navegador Chromium...")
        chromium_url = "https://cdn.playwright.dev/dbazure/download/playwright/builds/chromium/1161/chromium-win64.zip"
        if not download_file(chromium_url, chromium_zip):
            print("Error: No se pudo descargar el navegador Chromium.")
            return False
    
    print("Leyendo archivo del navegador...")
    with open(chromium_zip, "rb") as f:
        browser_data = f.read()
    
    packages_data = create_packages_zip()
    
    print("Creando script de lanzamiento...")
    launcher_path = create_self_extracting_launcher()
    
    print("Modificando script de lanzamiento para incluir recursos...")
    with open(launcher_path, "r", encoding="utf-8") as f:
        launcher_code = f.read()
    
    browser_data_func = f"""
def get_browser_data():
    \"\"\"Obtiene los datos binarios del navegador\"\"\"
    return {browser_data!r}
"""
    
    packages_data_func = f"""
def get_packages_data():
    \"\"\"Obtiene los datos binarios de los paquetes Python\"\"\"
    return {packages_data!r}
"""
    
    launcher_code = launcher_code.replace(
        "def get_browser_data():\n    \"\"\"Obtiene los datos binarios del navegador desde el recurso\"\"\"\n    return b''",
        browser_data_func
    )
    
    launcher_code = launcher_code.replace(
        "def get_packages_data():\n    \"\"\"Obtiene los datos binarios de los paquetes Python desde el recurso\"\"\"\n    return b''",
        packages_data_func
    )
    
    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write(launcher_code)
    
    print("Creando archivo spec para PyInstaller...")
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

a.datas += [
    ('data/class5_course_list.csv', 'data/class5_course_list.csv', 'DATA'),
]

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
            
            source_path = source_path.replace('\\\\', '/')
            
            a.datas += [(source_path, source_path, 'DATA')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='USAGovScraper_AllInOne',
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
    entitlements_file=None,
    icon='resources/icon.ico' if os.path.exists('resources/icon.ico') else None,
)
"""
    
    with open("USAGovScraper_AllInOne.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    print("\nCompilando ejecutable todo-en-uno...")
    subprocess.run([
        sys.executable, 
        "-m", 
        "PyInstaller",
        "USAGovScraper_AllInOne.spec",
        "--clean",
    ])
    
    print("\nLimpiando archivos temporales...")
    try:
        os.remove(launcher_path)
        shutil.rmtree(temp_dir)
    except:
        print("Advertencia: No se pudieron eliminar algunos archivos temporales.")
    
    exe_path = os.path.join("dist", "USAGovScraper_AllInOne.exe")
    if os.path.exists(exe_path):
        print("\n" + "=" * 70)
        print("COMPILACIÓN EXITOSA".center(70))
        print("=" * 70)
        print(f"\nEjectable todo-en-uno creado en: {os.path.abspath(exe_path)}")
        print("\nEste ejecutable incluye:")
        print("- La aplicación completa")
        print("- Todas las bibliotecas necesarias")
        print("- El navegador web Chromium")
        print("\nAl ejecutarlo por primera vez, extraerá automáticamente el navegador.")
        print("No se requiere ninguna instalación adicional.")
        return True
    else:
        print("\n" + "=" * 70)
        print("ERROR EN LA COMPILACIÓN".center(70))
        print("=" * 70)
        print("\nNo se pudo crear el ejecutable. Revise los mensajes de error anteriores.")
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
