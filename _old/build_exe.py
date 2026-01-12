# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
from datetime import datetime

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

def create_launcher_py():
    """Crea el archivo launcher.py sin errores de sintaxis"""
    launcher_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Launcher para USA.gov CSV Scraper
---------------------------------
Launcher que maneja la instalación inicial y configuración del entorno.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
import time
import threading
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_dependencies():
    """Verifica e instala las dependencias necesarias."""
    try:
        import requests
        import playwright
        return True
    except ImportError:
        return False

def install_dependencies():
    """Instala las dependencias necesarias."""
    try:
        dependencies = [
            "playwright>=1.40.0",
            "requests>=2.31.0",
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "openpyxl>=3.1.0",
            "aiohttp>=3.8.0"
        ]
        
        for dep in dependencies:
            print(f"Instalando {dep}...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", dep, "--upgrade"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Instalado correctamente: {dep}")
            else:
                print(f"Advertencia instalando: {dep}")
        
        print("Instalando navegadores Playwright...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                      capture_output=True, text=True)
        
        return True
    except Exception as e:
        print(f"Error instalando dependencias: {e}")
        return False

def create_directories():
    """Crea los directorios necesarios."""
    try:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        required_dirs = ["data", "logs", "results", "omitidos", "temp"]
        
        for dir_name in required_dirs:
            dir_path = os.path.join(app_dir, dir_name)
            os.makedirs(dir_path, exist_ok=True)
            print(f"Directorio creado: {dir_name}")
        
        return True
    except Exception as e:
        print(f"Error creando directorios: {e}")
        return False

def launch_main_app():
    """Lanza la aplicación principal."""
    try:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        main_py_path = os.path.join(app_dir, "main.py")
        
        if os.path.exists(main_py_path):
            subprocess.Popen([sys.executable, main_py_path])
            return True
        else:
            print(f"No se encontró main.py en: {main_py_path}")
            return False
    except Exception as e:
        print(f"Error iniciando aplicación: {e}")
        return False

class SimpleLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("USA.gov CSV Scraper - Launcher")
        self.root.geometry("500x300")
        self.root.resizable(False, False)
        self.setup_ui()
        
    def setup_ui(self):
        """Configura la interfaz de usuario."""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(main_frame, text="USA.gov CSV Scraper", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        self.status_label = ttk.Label(main_frame, text="Verificando configuracion...")
        self.status_label.pack(pady=(0, 20))
        
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 20))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(20, 0))
        
        self.setup_button = ttk.Button(button_frame, text="Configurar", 
                                      command=self.setup_environment)
        self.setup_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.launch_button = ttk.Button(button_frame, text="Iniciar Aplicacion", 
                                       command=self.launch_app, state="disabled")
        self.launch_button.pack(side=tk.LEFT, padx=(10, 0))
        
        self.check_initial_state()
    
    def check_initial_state(self):
        """Verifica el estado inicial de la aplicación."""
        if check_dependencies():
            self.status_label.config(text="Configuracion completa - Listo para usar")
            self.setup_button.config(state="disabled")
            self.launch_button.config(state="normal")
        else:
            self.status_label.config(text="Necesita configuracion inicial")
    
    def setup_environment(self):
        """Configura el entorno en un hilo separado."""
        self.setup_button.config(state="disabled")
        self.progress.start()
        self.status_label.config(text="Configurando entorno...")
        
        def setup_thread():
            try:
                if not create_directories():
                    raise Exception("Error creando directorios")
                
                if not install_dependencies():
                    raise Exception("Error instalando dependencias")
                
                self.root.after(0, self.setup_complete)
                
            except Exception as e:
                self.root.after(0, lambda: self.setup_error(str(e)))
        
        threading.Thread(target=setup_thread, daemon=True).start()
    
    def setup_complete(self):
        """Llamado cuando la configuración se completa."""
        self.progress.stop()
        self.status_label.config(text="Configuracion completada exitosamente!")
        self.launch_button.config(state="normal")
        messagebox.showinfo("Exito", "Configuracion completada correctamente")
    
    def setup_error(self, error_msg):
        """Llamado cuando hay un error en la configuración."""
        self.progress.stop()
        self.status_label.config(text="Error en la configuracion")
        self.setup_button.config(state="normal")
        messagebox.showerror("Error", f"Error durante la configuracion: {error_msg}")
    
    def launch_app(self):
        """Lanza la aplicación principal."""
        if launch_main_app():
            self.root.quit()
        else:
            messagebox.showerror("Error", "No se pudo iniciar la aplicacion principal")

def main():
    """Función principal del launcher."""
    try:
        root = tk.Tk()
        app = SimpleLauncher(root)
        
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")
        
        root.mainloop()
        
    except Exception as e:
        print(f"Error fatal en launcher: {e}")
        messagebox.showerror("Error Fatal", f"Error iniciando launcher: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    # Escribir el archivo launcher.py
    with open("launcher.py", "w", encoding="utf-8") as f:
        f.write(launcher_content)
    
    print("✓ Archivo launcher.py creado correctamente")
    return True

def main():
    print("\n" + "=" * 70)
    print("CREANDO EJECUTABLE CON CONSOLA VISIBLE".center(70))
    print("=" * 70 + "\n")
    
    # Crear el archivo launcher.py sin errores
    print("Creando archivo launcher.py...")
    if not create_launcher_py():
        print("Error: No se pudo crear launcher.py")
        return False
    
    # Crear directorios necesarios
    print("Creando directorios necesarios...")
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("dist", exist_ok=True)
    
    # Verificar y crear directorios que podrían faltar
    for directory in ["data", "logs", "results", "omitidos"]:
        os.makedirs(directory, exist_ok=True)
    
    # Asegurarse de que existan los archivos __init__.py en cada directorio
    for directory in ["controllers", "utils", "gui", "gui/components"]:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        init_file = os.path.join(directory, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("# Este archivo es necesario para que Python reconozca el directorio como un paquete\n")
    
    # Descargar Chromium si no existe
    chromium_zip = os.path.join("downloads", "chromium-win64.zip")
    if not os.path.exists(chromium_zip):
        print("Descargando navegador Chromium...")
        chromium_url = "https://cdn.playwright.dev/dbazure/download/playwright/builds/chromium/1161/chromium-win64.zip"
        if not download_file(chromium_url, chromium_zip):
            print("Error: No se pudo descargar el navegador Chromium.")
            return False
    else:
        print(f"Usando archivo existente: {chromium_zip}")
    
    # Verificar si PyInstaller está instalado
    try:
        import PyInstaller
        print("PyInstaller está instalado.")
    except ImportError:
        print("PyInstaller no está instalado. Instalando...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("PyInstaller instalado correctamente.")
        except Exception as e:
            print(f"Error al instalar PyInstaller: {e}")
            return False
    
    # Crear archivo spec personalizado para PyInstaller
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

# Lista de directorios a incluir si existen
data_dirs = []
if os.path.exists('data'):
    data_dirs.append(('data', 'data'))
if os.path.exists('resources'):
    data_dirs.append(('resources', 'resources'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=data_dirs + [
        ('controllers', 'controllers'),
        ('utils', 'utils'),
        ('gui', 'gui'),
    ],
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
        'platform',
        'tkinter',
        'tkinter.messagebox',
        'tkinter.ttk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher, level=1)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='USAGovScraper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='USAGovScraper',
)
"""
    
    with open("USAGovScraper.spec", "w") as f:
        f.write(spec_content)
    
    # Compilar ejecutable principal usando el archivo spec
    print("\nCompilando ejecutable principal...")
    try:
        result = subprocess.run([
            sys.executable, 
            "-m", 
            "PyInstaller",
            "USAGovScraper.spec"
        ], check=True)
        print("Compilación completada exitosamente.")
    except subprocess.CalledProcessError as e:
        print(f"Error durante la compilación: {e}")
        return False
    
    # Verificar que el ejecutable se haya creado
    exe_path = os.path.join("dist", "USAGovScraper", "USAGovScraper.exe")
    if not os.path.exists(exe_path):
        print(f"Error: No se encontró el ejecutable compilado en {exe_path}")
        return False
    
    # Crear paquete final
    print("\nCreando paquete final...")
    
    # Crear estructura de directorios
    final_dir = os.path.join(os.getcwd(), "dist_final")
    if os.path.exists(final_dir):
        print(f"Eliminando directorio existente: {final_dir}")
        try:
            shutil.rmtree(final_dir)
        except Exception as e:
            print(f"Error al eliminar directorio: {e}")
    
    os.makedirs(final_dir, exist_ok=True)
    os.makedirs(os.path.join(final_dir, "browser"), exist_ok=True)
    os.makedirs(os.path.join(final_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(final_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(final_dir, "results"), exist_ok=True)
    os.makedirs(os.path.join(final_dir, "omitidos"), exist_ok=True)
    
    # Copiar archivos
    print("Copiando archivos al paquete final...")
    
    # Copiar todo el directorio dist/USAGovScraper al directorio final
    dist_dir = os.path.join("dist", "USAGovScraper")
    for item in os.listdir(dist_dir):
        src = os.path.join(dist_dir, item)
        dst = os.path.join(final_dir, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    
    # Copiar el navegador
    shutil.copy(chromium_zip, os.path.join(final_dir, "browser", "chromium-win64.zip"))
    print(f"Navegador copiado a {os.path.join(final_dir, 'browser')}")
    
    # Copiar archivos de datos
    if os.path.exists("data"):
        for item in os.listdir("data"):
            src = os.path.join("data", item)
            dst = os.path.join(final_dir, "data", item)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
    
    # Crear un archivo README
    with open(os.path.join(final_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write("""# USA.gov CSV Scraper - Versión con Consola Visible

Esta versión incluye todo lo necesario para ejecutar la aplicación, incluyendo el navegador Chromium.
Además, muestra una ventana de consola donde se pueden ver los logs en tiempo real.

## Instrucciones

1. Simplemente ejecute USAGovScraper.exe
2. La primera vez que se ejecute, se verificará si los componentes necesarios ya están instalados
3. Si es necesario, se descargarán e instalarán automáticamente (esto puede tardar unos momentos)
4. La aplicación se iniciará automáticamente con una ventana de consola adicional
5. La ventana de consola mostrará los logs en tiempo real

## Estructura de Archivos
- USAGovScraper.exe: Ejecutable principal de la aplicación
- browser/chromium-win64.zip: Navegador Chromium empaquetado
- data/: Archivos de datos
- logs/: Archivos de registro
- results/: Resultados generados
- omitidos/: Archivos omitidos durante el proceso

## Notas

- Los resultados se guardarán en la carpeta "results"
- Los registros se guardarán en la carpeta "logs" y también se mostrarán en la consola
- No elimine ningún archivo o carpeta creado por la aplicación
- La primera ejecución puede tardar más tiempo mientras se configuran los componentes
""")
    
    # Crear un archivo batch para ejecutar la aplicación
    with open(os.path.join(final_dir, "Ejecutar_USAGovScraper.bat"), "w") as f:
        f.write("""@echo off
echo Iniciando CORDIS Europa CSV Scraper...
start "" "USAGovScraper.exe"
""")
    
    print("\n" + "=" * 70)
    print("PROCESO COMPLETADO EXITOSAMENTE".center(70))
    print("=" * 70)
    print(f"\nEl ejecutable con consola visible se ha creado en: {final_dir}")
    print("Ahora puede distribuir esta carpeta completa a los usuarios.")
    
    return True

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
