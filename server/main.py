#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Punto de Entrada Principal del Servidor
=======================================
Este script inicializa y ejecuta el ScraperServer.
"""

import os
import sys

# Añadir el directorio raíz al path para asegurar que las importaciones funcionen
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server.server import ScraperServer

if __name__ == "__main__":
    # Crea una instancia del servidor. El puerto puede ser sobrescrito
    # por argumentos de línea de comandos dentro de la clase ScraperServer.
    server = ScraperServer(host="0.0.0.0", port=8001)
    
    # Inicia el servidor. Esto bloqueará la ejecución aquí.
    server.run()
