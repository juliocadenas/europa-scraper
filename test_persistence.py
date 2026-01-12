
import sys
import os
import sqlite3

# Añadir path para importar el módulo del servidor
sys.path.insert(0, os.path.abspath('server'))

try:
    from main_wsl_corregido import init_database
    
    print("Checking DB before init_database...")
    conn = sqlite3.connect('courses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM courses")
    print(f"Rows: {cursor.fetchone()[0]}")
    conn.close()
    
    print("Running init_database()...")
    init_database()
    
    print("Checking DB after init_database...")
    conn = sqlite3.connect('courses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM courses")
    print(f"Rows: {cursor.fetchone()[0]}")
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
