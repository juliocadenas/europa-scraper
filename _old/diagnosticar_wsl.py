#!/usr/bin/env python3
"""
Script de diagnóstico para WSL - Europa Scraper
Verifica dependencias y entorno del sistema
"""

import sys
import subprocess
import os

def run_command(cmd, description):
    """Ejecuta un comando y muestra el resultado"""
    print(f"\n🔍 {description}")
    print(f"Comando: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        print(f"Salida (stdout): {result.stdout}")
        if result.stderr:
            print(f"Error (stderr): {result.stderr}")
        print(f"Código de salida: {result.returncode}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT: El comando tardó demasiado tiempo")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("=" * 60)
    print("🔧 DIAGNÓSTICO WSL - EUROPA SCRAPER")
    print("=" * 60)
    
    # 1. Verificar versión de Python
    print(f"\n📍 Versión de Python: {sys.version}")
    print(f"📍 Ruta de Python: {sys.executable}")
    
    # 2. Verificar pip
    success = run_command("python3 -m pip --version", "Verificando pip...")
    
    # 3. Verificar módulos críticos
    critical_modules = [
        "fastapi",
        "uvicorn", 
        "requests",
        "pandas",
        "playwright"
    ]
    
    print(f"\n🔍 Verificando módulos críticos...")
    for module in critical_modules:
        success = run_command(f"python3 -c 'import {module}; print(\"✅ {module} disponible\")'", f"Verificando {module}...")
        if not success:
            print(f"❌ {module} NO DISPONIBLE")
    
    # 4. Verificar playwright browsers
    print(f"\n🔍 Verificando navegadores Playwright...")
    run_command("python3 -m playwright install --dry-run chromium", "Verificando instalación de Chromium...")
    
    # 5. Verificar entorno virtual
    print(f"\n🔍 Verificando entorno virtual...")
    venv_path = os.path.join(os.path.dirname(__file__), 'venv_windows')
    if os.path.exists(venv_path):
        print(f"❌ Detectado entorno virtual Windows: {venv_path}")
        print("⚠️  WSL debería usar su propio entorno virtual")
        print("💡 Recomendación: Crea un entorno virtual en WSL:")
        print("   python3 -m venv venv_wsl")
        print("   source venv_wsl/bin/activate")
        print("   pip install -r requirements.txt")
    else:
        print("✅ No se detectó entorno virtual Windows (correcto)")
    
    # 6. Verificar si estamos en WSL
    try:
        with open('/proc/version', 'r') as f:
            if 'Microsoft' in f.read():
                print("✅ Detectado WSL (correcto)")
            else:
                print("❌ No se detectó WSL")
    except:
        print("⚠️  No se pudo verificar WSL")
    
    # 7. Mostrar PATH de Python
    print(f"\n🔍 PATH de Python:")
    run_command("echo $PATH", "Mostrando PATH...")
    
    # 8. Verificar ubicación de módulos
    print(f"\n🔍 Verificando ubicación de módulos Python...")
    run_command("python3 -c 'import sys; print(\"\\n\".join(sys.path))'", "Mostrando sys.path...")
    
    print("\n" + "=" * 60)
    print("🎯 RECOMENDACIONES:")
    print("=" * 60)
    print("1. Si faltan módulos, ejecuta:")
    print("   python3 -m pip install fastapi uvicorn[standard] requests pandas playwright")
    print("2. Para crear entorno virtual en WSL:")
    print("   python3 -m venv venv_wsl")
    print("   source venv_wsl/bin/activate")
    print("3. Para instalar navegadores:")
    print("   python3 -m playwright install chromium")
    print("=" * 60)

if __name__ == "__main__":
    main()