#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para ejecutar el cliente del scraper Europa
===============================================
Este script inicia la interfaz gráfica del cliente
"""

import os
import sys

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.main import ClientApp

def main():
    """Función principal para iniciar el cliente"""
    print("Iniciando cliente Europa Scraper")
    print(f"Directorio de trabajo: {os.getcwd()}")
    print(f"Logs: logs/client.log")
    
    # Iniciar la aplicación cliente
    app = ClientApp()
    app.run()

if __name__ == "__main__":
    main()