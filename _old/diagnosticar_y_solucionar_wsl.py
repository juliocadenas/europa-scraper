#!/usr/bin/env python3
"""
DIAGNÓSTICO Y SOLUCIÓN AUTOMÁTICA PARA WSL
================================================

Este script:
1. Diagnostica los problemas del navegador en WSL
2. Aplica las correcciones necesarias
3. Verifica que todo funcione correctamente
"""

import os
import sys
import subprocess
import shutil
import asyncio
import logging
from pathlib import Path

def run_command(cmd, check=True, capture_output=True):
    """Ejecuta un comando y maneja errores"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, 
                              capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def print_status(message, status="INFO"):
    """Imprime mensajes con formato"""
    status_colors = {
        "INFO": "🔵",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "STEP": "🔄",
        "DIAG": "🔍"
    }
    print(f"{status_colors.get(status, '🔹')} {message}")

def check_wsl_environment():
    """Verifica el entorno WSL"""
    print_status("Verificando entorno WSL...", "DIAG")
    
    # Detectar WSL
    try:
        with open('/proc/version', 'r') as f:
            version = f.read().lower()
            if 'microsoft' in version:
                print_status("✅ Entorno WSL detectado", "SUCCESS")
                return True
    except:
        pass
    
    print_status("❌ Entorno WSL no detectado", "ERROR")
    return False

def check_display_environment():
    """Verifica el entorno display"""
    print_status("Verificando entorno DISPLAY...", "DIAG")
    
    display = os.environ.get('DISPLAY', '')
    if display:
        print_status(f"DISPLAY encontrado: {display}", "SUCCESS")
    else:
        print_status("DISPLAY no configurado", "WARNING")
        print_status("Configurando DISPLAY=:99 para WSL", "INFO")
        os.environ['DISPLAY'] = ':99'
    
    return os.environ.get('DISPLAY', '')

def check_dependencies():
    """Verifica dependencias críticas"""
    print_status("Verificando dependencias críticas...", "DIAG")
    
    deps = {
        'python3': 'python3 --version',
        'pip': 'pip --version',
        'playwright': './venv_wsl/bin/python -c "import playwright; print(playwright.__version__)"',
        'pyee': './venv_wsl/bin/python -c "import pyee; print(pyee.__version__)"',
        'greenlet': './venv_wsl/bin/python -c "import greenlet; print(greenlet.__version__)"'
    }
    
    missing_deps = []
    for dep, cmd in deps.items():
        success, stdout, stderr = run_command(cmd)
        if success:
            print_status(f"✅ {dep}: {stdout.strip()}", "SUCCESS")
        else:
            print_status(f"❌ {dep}: No encontrado", "ERROR")
            missing_deps.append(dep)
    
    return missing_deps

def install_missing_dependencies(missing_deps):
    """Instala dependencias faltantes"""
    if not missing_deps:
        return True
    
    print_status("Instalando dependencias faltantes...", "STEP")
    
    # Instalar dependencias Python
    python_deps = ['playwright', 'pyee', 'greenlet', 'typing-extensions']
    for dep in missing_deps:
        if dep in python_deps:
            print_status(f"Instalando {dep}...", "INFO")
            success, stdout, stderr = run_command(f"./venv_wsl/bin/pip install {dep}")
            if success:
                print_status(f"✅ {dep} instalado", "SUCCESS")
            else:
                print_status(f"❌ Error instalando {dep}: {stderr}", "ERROR")
                return False
    
    return True

def check_browser_installation():
    """Verifica instalación de navegadores Playwright"""
    print_status("Verificando instalación de navegadores Playwright...", "DIAG")
    
    success, stdout, stderr = run_command("./venv_wsl/bin/playwright install --help")
    if not success:
        print_status("❌ Playwright CLI no disponible", "ERROR")
        return False
    
    # Verificar si Chromium está instalado
    browser_path = "./venv_wsl/lib/python3.12/site-packages/playwright/driver"
    if os.path.exists(browser_path):
        print_status("✅ Directorio de drivers Playwright encontrado", "SUCCESS")
        
        # Buscar Chromium
        chromium_files = list(Path(browser_path).glob("**/chromium*"))
        if chromium_files:
            print_status(f"✅ Chromium encontrado: {len(chromium_files)} archivos", "SUCCESS")
        else:
            print_status("❌ Chromium no encontrado", "ERROR")
            return False
    else:
        print_status("❌ Directorio de drivers Playwright no encontrado", "ERROR")
        return False
    
    return True

def install_browsers():
    """Instala los navegadores Playwright"""
    print_status("Instalando navegadores Playwright...", "STEP")
    
    commands = [
        "./venv_wsl/bin/playwright install chromium",
        "./venv_wsl/bin/playwright install-deps"
    ]
    
    for cmd in commands:
        print_status(f"Ejecutando: {cmd}", "INFO")
        success, stdout, stderr = run_command(cmd)
        if success:
            print_status(f"✅ Comando exitoso: {cmd}", "SUCCESS")
        else:
            print_status(f"❌ Error en comando: {cmd}", "ERROR")
            print_status(f"Stderr: {stderr}", "ERROR")
            return False
    
    return True

async def test_browser_functionality():
    """Prueba la funcionalidad del navegador"""
    print_status("Probando funcionalidad del navegador...", "DIAG")
    
    test_script = '''
import asyncio
import logging
import os
import sys

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Añadir raíz del proyecto
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

async def test_browser():
    try:
        from playwright.async_api import async_playwright
        
        logger.info("Iniciando Playwright...")
        playwright = await async_playwright().start()
        
        # Argumentos para WSL
        args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--headless'
        ]
        
        logger.info("Lanzando Chromium con argumentos WSL...")
        browser = await playwright.chromium.launch(headless=True, args=args)
        
        logger.info("Creando contexto...")
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            viewport={'width': 1366, 'height': 768}
        )
        
        logger.info("Creando página...")
        page = await context.new_page()
        
        logger.info("Navegando a example.com...")
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
        
        title = await page.title()
        logger.info(f"Título obtenido: {title}")
        
        logger.info("Cerrando navegador...")
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()
        
        logger.info("✅ Prueba de navegador exitosa")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en prueba de navegador: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_browser())
    sys.exit(0 if result else 1)
'''
    
    with open("test_browser_simple.py", "w") as f:
        f.write(test_script)
    
    os.chmod("test_browser_simple.py", 0o755)
    
    success, stdout, stderr = run_command("./venv_wsl/bin/python test_browser_simple.py")
    if success:
        print_status("✅ Prueba de navegador exitosa", "SUCCESS")
        return True
    else:
        print_status("❌ Prueba de navegador fallida", "ERROR")
        print_status(f"Error: {stderr}", "ERROR")
        return False

def create_wsl_optimized_config():
    """Crea configuración optimizada para WSL"""
    print_status("Creando configuración optimizada para WSL...", "STEP")
    
    config_content = '''{
    "headless_mode": true,
    "wsl_mode": true,
    "disable_gpu": true,
    "no_sandbox": true,
    "disable_dev_shm_usage": true,
    "browser_args": [
        "--no-sandbox",
        "--disable-setuid-sandbox", 
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-features=TranslateUI",
        "--enable-features=UseOzonePlatform",
        "--ozone-platform=headless",
        "--disable-extensions",
        "--disable-plugins",
        "--disable-default-apps"
    ],
    "viewport": {
        "width": 1366,
        "height": 768
    },
    "locale": "en-US",
    "timezone": "America/New_York"
}'''
    
    with open("wsl_config.json", "w") as f:
        f.write(config_content)
    
    print_status("✅ Configuración WSL creada: wsl_config.json", "SUCCESS")

def apply_wsl_patches():
    """Aplica parches específicos para WSL"""
    print_status("Aplicando parches específicos para WSL...", "STEP")
    
    # Crear patch para browser_manager
    patch_content = '''
# Patch WSL para browser_manager
import os
import sys

# Detectar WSL
def is_wsl():
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower()
    except:
        return False

if is_wsl():
    print("🔧 Aplicando configuración WSL para browser_manager...")
    
    # Forzar headless en WSL
    os.environ['PLAYWRIGHT_HEADLESS'] = 'true'
    
    # Configurar display virtual
    if not os.environ.get('DISPLAY'):
        os.environ['DISPLAY'] = ':99'
    
    # Parchear BrowserManager para WSL
    original_init = None
    
    def wsl_browser_init(self, *args, **kwargs):
        # Forzar configuración WSL
        if 'headless' not in kwargs or kwargs['headless'] is None:
            kwargs['headless'] = True
        
        # Llamar al original
        return original_init(self, *args, **kwargs)
    
    # Aplicar patch si el módulo está cargado
    try:
        from utils.scraper import browser_manager
        if hasattr(browser_manager, 'BrowserManager'):
            original_init = browser_manager.BrowserManager.__init__
            browser_manager.BrowserManager.__init__ = wsl_browser_init
            print("✅ Patch WSL aplicado a BrowserManager")
    except ImportError:
        print("⚠️ Módulo browser_manager no encontrado para aplicar patch")
'''
    
    with open("wsl_patch.py", "w") as f:
        f.write(patch_content)
    
    print_status("✅ Patch WSL creado: wsl_patch.py", "SUCCESS")

async def main():
    """Función principal de diagnóstico y solución"""
    print("=" * 70)
    print("   DIAGNÓSTICO Y SOLUCIÓN AUTOMÁTICA PARA WSL")
    print("=" * 70)
    print()
    
    # Paso 1: Verificar entorno
    is_wsl = check_wsl_environment()
    check_display_environment()
    
    # Paso 2: Verificar dependencias
    missing_deps = check_dependencies()
    if missing_deps:
        if not install_missing_dependencies(missing_deps):
            print_status("❌ No se pudieron instalar dependencias", "ERROR")
            return False
    
    # Paso 3: Verificar instalación de navegadores
    if not check_browser_installation():
        print_status("Instalando navegadores Playwright...", "INFO")
        if not install_browsers():
            print_status("❌ Error instalando navegadores", "ERROR")
            return False
    
    # Paso 4: Probar funcionalidad
    if not await test_browser_functionality():
        print_status("❌ La prueba del navegador falló", "ERROR")
        return False
    
    # Paso 5: Crear configuración optimizada
    create_wsl_optimized_config()
    apply_wsl_patches()
    
    print()
    print("=" * 70)
    print("   ✅ DIAGNÓSTICO COMPLETADO - WSL CONFIGURADO")
    print("=" * 70)
    print()
    print("📋 Próximos pasos:")
    print("   1. Ejecutar: ./iniciar_servidor_wsl_definitivo.sh")
    print("   2. El servidor debería iniciar sin problemas de navegador")
    print("   3. Los workers crearán sus logs correctamente")
    print()
    print("🎉 ¡El problema del navegador en WSL está resuelto!")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Ejecutar diagnóstico
    result = asyncio.run(main())
    sys.exit(0 if result else 1)