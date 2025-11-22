import os
import sys
import pandas as pd
import sqlite3
import logging

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

def migrate_csv_to_sqlite(csv_path, db_path):
    """
    Migra los datos de un archivo CSV a una base de datos SQLite.
    """
    if not os.path.exists(csv_path):
        logger.error(f"El archivo CSV no se encuentra en: {csv_path}")
        return

    try:
        # Leer el archivo CSV
        df = pd.read_csv(csv_path)
        logger.info(f"Leídas {len(df)} filas del archivo CSV.")

        # Conectar a la base de datos SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Crear la tabla si no existe
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course TEXT,
            name TEXT,
            status TEXT,
            server TEXT
        )
        ''')

        # Insertar los datos en la tabla
        for _, row in df.iterrows():
            cursor.execute("INSERT INTO courses (course, name) VALUES (?, ?)", (row['sic_code'], row['course']))

        conn.commit()
        logger.info(f"Se han insertado {len(df)} filas en la tabla 'courses' de la base de datos.")

    except Exception as e:
        logger.error(f"Error durante la migración de CSV a SQLite: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Obtener la ruta del directorio actual
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construir las rutas a los archivos CSV y de base de datos
    csv_file = os.path.join(current_dir, '..', 'data', '---class5_course_list.csv')
    db_file = os.path.join(current_dir, '..', 'client', 'courses.db')

    # Ejecutar la migración
    migrate_csv_to_sqlite(csv_file, db_file)