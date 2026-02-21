#!/usr/bin/env python3
"""Script de prueba para verificar que el botón existe en la GUI."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("VERIFICANDO GUI")
print("=" * 60)

# Verificar que el archivo existe
gui_path = os.path.join(os.path.dirname(__file__), 'gui', 'scraper_gui.py')
print(f"Archivo GUI: {gui_path}")
print(f"Existe: {os.path.exists(gui_path)}")

# Leer el archivo y buscar el botón
with open(gui_path, 'r', encoding='utf-8') as f:
    content = f.read()
    
if 'Ver Cursos Fallidos' in content:
    print("✅ Botón 'Ver Cursos Fallidos' encontrado en el archivo")
else:
    print("❌ Botón NO encontrado en el archivo")

if '_show_failed_courses' in content:
    print("✅ Método '_show_failed_courses' encontrado en el archivo")
else:
    print("❌ Método NO encontrado en el archivo")

# Importar la clase
try:
    from gui.scraper_gui import ScraperGUI
    print("✅ Importación de ScraperGUI exitosa")
    
    # Verificar que el método existe en la clase
    if hasattr(ScraperGUI, '_show_failed_courses'):
        print("✅ Método '_show_failed_courses' existe en la clase ScraperGUI")
    else:
        print("❌ Método NO existe en la clase ScraperGUI")
        
except Exception as e:
    print(f"❌ Error importando: {e}")

print("=" * 60)
print("Si todo dice ✅, el código está correcto.")
print("El problema puede ser que estás ejecutando desde otro directorio.")
print("=" * 60)
