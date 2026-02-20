#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para ejecutar el cliente del scraper Europa
===============================================
Este script inicia la interfaz gráfica del cliente
"""

import os
import sys
import traceback

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    print("Importando ClientApp...")
    from client.main import ClientApp
    print("Importación exitosa")
    
    print("Creando instancia de ClientApp...")
    app = ClientApp()
    print("Instancia creada exitosamente")
    
    print("Iniciando bucle principal...")
    app.run()
    print("Bucle principal finalizado")
    
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()