#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para ejecutar el servidor del scraper Europa
===============================================
Este script inicia el servidor FastAPI para el procesamiento distribuido de scraping
"""

import os
import sys
import argparse
import uvicorn

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Función principal para iniciar el servidor"""
    parser = argparse.ArgumentParser(description="Servidor del scraper Europa")
    parser.add_argument("--host", default="0.0.0.0", help="Host para el servidor (por defecto: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8001, help="Puerto para el servidor (por defecto: 8001)")
    parser.add_argument("--workers", type=int, default=1, help="Número de workers (por defecto: 1)")
    parser.add_argument("--reload", action="store_true", help="Activar recarga automática")
    
    args = parser.parse_args()
    
    # Crear directorios necesarios
    os.makedirs("logs", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    os.makedirs("omitidos", exist_ok=True)
    
    print(f"Iniciando servidor Europa Scraper en {args.host}:{args.port}")
    print(f"Directorio de trabajo: {os.getcwd()}")
    print(f"Logs: logs/server.log")
    
    # Actualizar el puerto del servidor antes de iniciar
    import server.main
    server.main.SERVER_PORT = args.port
    
    # Iniciar servidor
    uvicorn.run(
        "server.main:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=args.reload,
        log_level="info"
    )

if __name__ == "__main__":
    main()