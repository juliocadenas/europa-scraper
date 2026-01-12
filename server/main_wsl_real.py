#!/usr/bin/env python3
import os
import sys
import logging
import uvicorn
from fastapi import FastAPI

# Añadir raíz del proyecto
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importar el servidor REAL
from server.server import ScraperServer

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Obtener host y puerto de argumentos de línea de comandos
    host = "0.0.0.0"
    port = 8002
    
    if len(sys.argv) > 1:
        for arg in sys.argv:
            if arg.startswith("--host="):
                host = arg.split("=")[1]
            elif arg.startswith("--port="):
                port = int(arg.split("=")[1])
    
    logger.info(f"Iniciando SERVIDOR REAL (PRODUCCIÓN) en {host}:{port}...")
    
    # Instanciar el servidor real
    server_instance = ScraperServer(host=host, port=port)
    
    # Asegurar que la ruta de la base de datos sea absoluta (Parche crítico)
    # Aunque server.py usa project_root, vamos a verificarlo
    db_path = os.path.join(project_root, 'courses.db')
    logger.info(f"DEBUG CRITICO: La base de datos se buscará en: {db_path}")
    
    if os.path.exists(db_path):
        logger.info("✅ Archivo de base de datos encontrado.")
    else:
        logger.warning("⚠️ Archivo de base de datos NO encontrado. Se creará al subir un archivo.")

    # Ejecutar
    server_instance.run()
