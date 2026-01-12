#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fix Main Script
--------------
Este script modifica el archivo main.py para que funcione correctamente
cuando se ejecuta desde un ejecutable compilado con PyInstaller.
"""

import os
import sys
import shutil
import re

def main():
    """Función principal"""
    print("\n" + "=" * 70)
    print("ARREGLANDO SCRIPT PRINCIPAL".center(70))
    print("=" * 70 + "\n")
    
    # Verificar que exista el archivo main.py
    if not os.path.exists("main.py"):
        print("Error: No se encontró el archivo main.py")
        return False
    
    # Hacer una copia de seguridad
    backup_file = "main.py.bak"
    if not os.path.exists(backup_file):
        shutil.copy2("main.py", backup_file)
        print(f"Copia de seguridad creada: {backup_file}")
    
    # Leer el contenido del archivo
    with open("main.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Modificar el contenido para que funcione con PyInstaller
    modified_content = content
    
    # Añadir código para manejar la ejecución desde un ejecutable
    if "if getattr(sys, 'frozen', False):" not in content:
        # Buscar la importación de sys
        if "import sys" not in content:
            modified_content = "import sys\n" + modified_content
        
        # Buscar el punto de entrada principal
        if "if __name__ == \"__main__\":" in modified_content:
            # Añadir código antes del punto de entrada
            pattern = r"if __name__ == \"__main__\":"
            replacement = """# Configurar rutas para PyInstaller
if getattr(sys, 'frozen', False):
    # Ejecutando como ejecutable compilado
    bundle_dir = os.path.dirname(sys.executable)
    # Añadir el directorio del ejecutable al path
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)
    # Cambiar al directorio del ejecutable
    os.chdir(bundle_dir)

if __name__ == "__main__":"""
            modified_content = re.sub(pattern, replacement, modified_content)
    
    # Guardar el archivo modificado
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(modified_content)
    
    print("Archivo main.py modificado correctamente para funcionar con PyInstaller.")
    return True

if __name__ == "__main__":
    try:
        success = main()
        
        if success:
            print("\nEl archivo main.py ha sido modificado correctamente.")
            print("Ahora puedes compilar la aplicación con PyInstaller.")
        else:
            print("\nHubo errores durante el proceso. Revise los mensajes anteriores.")
        
        print("\nPresione Enter para salir...")
        input()
    except Exception as e:
        print(f"\nError inesperado: {e}")
        print("\nPresione Enter para salir...")
        input()
