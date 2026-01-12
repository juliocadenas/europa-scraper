#!/usr/bin/env python3
"""
EUROPA SCRAPER - SOLUCIÓN DEFINITIVA WSL/LINUX
UN SOLO ARCHIVO PARA RESOLVER TODOS LOS PROBLEMAS
"""

import os
import sys
import subprocess
import shutil
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
        "STEP": "🔄"
    }
    print(f"{status_colors.get(status, '🔹')} {message}")

def clean_previous_installations():
    """Limpia instalaciones anteriores"""
    print_status("Limpiando instalaciones anteriores...", "STEP")
    
    # Eliminar entorno virtual si existe
    if os.path.exists("venv_wsl"):
        shutil.rmtree("venv_wsl")
        print_status("Entorno virtual anterior eliminado", "SUCCESS")
    
    # Eliminar archivos basura
    basura_files = ["__pycache__", "*.pyc", ".pytest_cache"]
    for pattern in basura_files:
        if "*" in pattern:
            for file in Path(".").glob(pattern):
                if file.is_dir():
                    shutil.rmtree(file)
                else:
                    file.unlink()
        else:
            if os.path.exists(pattern):
                if os.path.isdir(pattern):
                    shutil.rmtree(pattern)
                else:
                    os.remove(pattern)

def create_virtual_environment():
    """Crea el entorno virtual"""
    print_status("Creando entorno virtual aislado...", "STEP")
    
    success, stdout, stderr = run_command("python3 -m venv venv_wsl")
    if not success:
        print_status(f"Error creando entorno virtual: {stderr}", "ERROR")
        return False
    
    print_status("Entorno virtual creado exitosamente", "SUCCESS")
    return True

def activate_and_update_pip():
    """Activa el entorno y actualiza pip"""
    print_status("Activando entorno virtual y actualizando pip...", "STEP")
    
    # Actualizar pip
    success, stdout, stderr = run_command("./venv_wsl/bin/pip install --upgrade pip")
    if not success:
        print_status(f"Error actualizando pip: {stderr}", "ERROR")
        return False
    
    print_status("pip actualizado exitosamente", "SUCCESS")
    return True

def install_dependencies():
    """Instala todas las dependencias necesarias"""
    print_status("Instalando dependencias del proyecto...", "STEP")
    
    # Lista de dependencias CORREGIDA (sin sqlite3)
    dependencies = [
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "requests>=2.31.0",
        "pandas>=2.0.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "openpyxl>=3.1.0",
        "python-multipart>=0.0.6",
        "aiofiles>=23.2.0",
        "python-dotenv>=1.0.0",
        "selenium>=4.15.0",
        "webdriver-manager>=4.0.0",
        "playwright>=1.40.0",
        "pyee>=13.0.0",
        "greenlet>=3.0.0",
        "typing-extensions>=4.8.0",
        "httpx>=0.25.0"
    ]
    
    # Instalar dependencias en lotes para evitar errores
    batch_size = 5
    for i in range(0, len(dependencies), batch_size):
        batch = dependencies[i:i + batch_size]
        deps_str = " ".join(batch)
        
        print_status(f"Instalando lote {i//batch_size + 1}: {deps_str}", "INFO")
        success, stdout, stderr = run_command(f"./venv_wsl/bin/pip install {deps_str}")
        
        if not success:
            print_status(f"Error instalando lote: {stderr}", "WARNING")
            # Intentar instalar individualmente si falla el lote
            for dep in batch:
                print_status("Intentando instalar individualmente...", "WARNING")
                success, stdout, stderr = run_command(f"./venv_wsl/bin/pip install {dep}")
                if not success:
                    print_status(f"No se pudo instalar {dep}: {stderr}", "ERROR")
                else:
                    print_status(f"✅ {dep} instalado", "SUCCESS")
        else:
            print_status(f"Lote {i//batch_size + 1} instalado exitosamente", "SUCCESS")
    
    return True

def install_playwright_browsers():
    """Instala los navegadores de Playwright"""
    print_status("Instalando navegadores de Playwright...", "STEP")
    
    success, stdout, stderr = run_command("./venv_wsl/bin/playwright install")
    if not success:
        print_status(f"Error instalando navegadores: {stderr}", "WARNING")
        # Intentar instalación manual
        success, stdout, stderr = run_command("./venv_wsl/bin/playwright install chromium")
        if not success:
            print_status("No se pudieron instalar los navegadores", "ERROR")
            return False
    
    print_status("Navegadores instalados exitosamente", "SUCCESS")
    return True

def verify_installation():
    """Verifica que todo esté instalado correctamente"""
    print_status("Verificando instalación...", "STEP")
    
    # Lista de módulos a verificar
    modules_to_check = [
        "fastapi", "uvicorn", "requests", "pandas",
        "beautifulsoup4", "lxml", "openpyxl", "playwright", "httpx"
    ]
    
    failed_modules = []
    success_modules = []
    
    for module in modules_to_check:
        # Corregir nombres de importación específicos
        import_name = module.replace('-', '_')
        if import_name == 'beautifulsoup4':
            import_name = 'bs4'
        
        success, stdout, stderr = run_command(f"./venv_wsl/bin/python -c \"import {import_name}; print('{module}: OK')\"")
        if success:
            success_modules.append(module)
        else:
            failed_modules.append(module)
    
    # Mostrar resultados
    for module in success_modules:
        print_status(f"{module} - OK", "SUCCESS")
    
    for module in failed_modules:
        print_status(f"{module} - ERROR", "ERROR")
    
    if failed_modules:
        print_status(f"Módulos fallidos: {failed_modules}", "ERROR")
        return False
    else:
        print_status("Todos los módulos instalados correctamente", "SUCCESS")
        return True

def create_start_script():
    """Crea un script para iniciar el servidor fácilmente"""
    script_content = """#!/bin/bash
echo "========================================="
echo "  INICIANDO SERVIDOR EUROPA SCRAPER"
echo "========================================="
echo "Activando entorno virtual..."
source venv_wsl/bin/activate
echo "Iniciando servidor..."
cd server
python main.py
"""
    
    with open("iniciar_servidor_wsl_final.sh", "w") as f:
        f.write(script_content)
    
    os.chmod("iniciar_servidor_wsl_final.sh", 0o755)
    print_status("Script de inicio creado: iniciar_servidor_wsl_final.sh", "SUCCESS")

def create_windows_launcher():
    """Crea un launcher para Windows"""
    launcher_content = """@echo off
echo ========================================
echo   EUROPA SCRAPER - INICIAR SERVIDOR WSL
echo ========================================
echo.
wsl -d Ubuntu bash -c "cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX && ./iniciar_servidor_wsl_final.sh"
echo.
pause
"""
    
    with open("INICIAR_SERVIDOR.bat", "w") as f:
        f.write(launcher_content)
    
    print_status("Launcher para Windows creado: INICIAR_SERVIDOR.bat", "SUCCESS")

def create_client_launcher():
    """Crea un launcher para el cliente"""
    client_content = """@echo off
echo ========================================
echo   INICIANDO CLIENTE EUROPA SCRAPER
echo ========================================
echo.
echo Asegúrate de que el servidor esté corriendo
echo en otra terminal antes de iniciar el cliente.
echo.

cd client
python main.py

echo.
echo ========================================
echo   CLIENTE DETENIDO
echo ========================================
pause
"""
    
    with open("INICIAR_CLIENTE.bat", "w") as f:
        f.write(client_content)
    
    print_status("Launcher para cliente creado: INICIAR_CLIENTE.bat", "SUCCESS")

def cleanup_old_files():
    """Limpia archivos viejos innecesarios"""
    print_status("Limpiando archivos viejos...", "STEP")
    
    old_files = [
        "solucion_definitiva_wsl.sh", "solucion_definitiva_wsl.bat",
        "iniciar_servidor_wsl.bat", "prueba_final_wsl.py", "probar_final_wsl.bat",
        "INSTRUCCIONES_FINALES_WSL.md", "solucion_directa_wsl.sh",
        "solucion_directa_wsl.bat"
    ]
    
    for file in old_files:
        if os.path.exists(file):
            os.remove(file)
            print_status(f"Eliminado: {file}", "INFO")

def main():
    """Función principal"""
    print("=" * 60)
    print("   EUROPA SCRAPER - SOLUCIÓN DEFINITIVA WSL/LINUX")
    print("=" * 60)
    print()
    
    # Paso 1: Limpiar instalaciones anteriores
    clean_previous_installations()
    
    # Paso 2: Crear entorno virtual
    if not create_virtual_environment():
        print_status("Fallo al crear entorno virtual", "ERROR")
        sys.exit(1)
    
    # Paso 3: Activar y actualizar pip
    if not activate_and_update_pip():
        print_status("Fallo al actualizar pip", "ERROR")
        sys.exit(1)
    
    # Paso 4: Instalar dependencias
    if not install_dependencies():
        print_status("Fallo al instalar dependencias", "ERROR")
        sys.exit(1)
    
    # Paso 5: Instalar navegadores
    if not install_playwright_browsers():
        print_status("Advertencia: No se pudieron instalar los navegadores", "WARNING")
    
    # Paso 6: Verificar instalación
    if not verify_installation():
        print_status("La instalación tuvo errores", "ERROR")
        sys.exit(1)
    
    # Paso 7: Crear scripts de inicio
    create_start_script()
    create_windows_launcher()
    
    # Paso 8: Limpiar archivos viejos
    cleanup_old_files()
    
    print()
    print("=" * 60)
    print("   ¡INSTALACIÓN COMPLETADA CON ÉXITO!")
    print("=" * 60)
    print()
    print("📋 Para usar el sistema:")
    print("   1. Iniciar servidor:")
    print("      • Desde Windows: INICIAR_SERVIDOR.bat")
    print("      • Desde WSL: ./iniciar_servidor_wsl_final.sh")
    print()
    print("   2. Iniciar cliente (desde Windows):")
    print("      cd client && python main.py")
    print()
    print("🎉 ¡El problema de dependencias está resuelto!")
    print("=" * 60)

if __name__ == "__main__":
    main()