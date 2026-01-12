#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para iniciar la GUI con conexión automática al servidor corregido
=================================================================
Este script inicia la GUI del scraper configurada para conectarse
automáticamente al servidor corregido en el puerto 8001.
"""

import os
import sys
import subprocess
import time
import requests
import threading
from pathlib import Path

def verificar_servidor():
    """Verifica si el servidor corregido está corriendo"""
    try:
        response = requests.get("http://localhost:8001/ping", timeout=5)
        if response.text.strip('"') == "EUROPA_SCRAPER_WSL_CORREGIDO_PONG":
            print("✅ Servidor corregido detectado y funcionando")
            return True
        else:
            print("❌ El servidor no responde correctamente")
            return False
    except requests.exceptions.RequestException:
        print("❌ No se puede conectar al servidor corregido")
        return False

def iniciar_servidor_si_no_existe():
    """Inicia el servidor corregido si no está corriendo"""
    print("🔍 Verificando servidor corregido...")
    
    if not verificar_servidor():
        print("🚀 Iniciando servidor corregido...")
        try:
            # Iniciar servidor en segundo plano
            server_script = os.path.join(os.path.dirname(__file__), 'iniciar_servidor_corregido.py')
            subprocess.Popen([sys.executable, server_script], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
            
            # Esperar a que el servidor inicie
            print("⏳ Esperando que el servidor inicie...")
            for i in range(10):  # Esperar máximo 10 segundos
                time.sleep(1)
                if verificar_servidor():
                    print("✅ Servidor iniciado correctamente")
                    return True
                print(f"⏳ Esperando... ({i+1}/10)")
            
            print("❌ El servidor no pudo iniciarse en el tiempo esperado")
            return False
            
        except Exception as e:
            print(f"❌ Error iniciando servidor: {e}")
            return False
    else:
        return True

def iniciar_gui():
    """Inicia la GUI del scraper"""
    try:
        # Buscar el script principal de la GUI
        gui_paths = [
            os.path.join('gui', 'scraper_gui.py'),
            'gui/scraper_gui.py',
            'scraper_gui.py'
        ]
        
        gui_script = None
        for path in gui_paths:
            if os.path.exists(path):
                gui_script = path
                break
        
        if not gui_script:
            print("❌ No se encuentra el script de la GUI")
            return False
        
        print(f"🖥️  Iniciando GUI desde: {gui_script}")
        
        # Iniciar la GUI
        subprocess.run([sys.executable, gui_script])
        return True
        
    except Exception as e:
        print(f"❌ Error iniciando GUI: {e}")
        return False

def main():
    """Función principal"""
    print("🎯 Europa Scraper - Sistema Completo")
    print("=" * 50)
    
    # Paso 1: Iniciar/verificar servidor
    if not iniciar_servidor_si_no_existe():
        print("❌ No se pudo iniciar el servidor. Abortando...")
        sys.exit(1)
    
    print()
    print("🌐 Servidor disponible en: http://localhost:8001")
    print("📊 Endpoint de scraping: http://localhost:8001/start_scraping")
    print("📋 Lista de cursos: http://localhost:8001/get_all_courses")
    print()
    
    # Paso 2: Iniciar GUI
    print("🚀 Iniciando interfaz gráfica...")
    if not iniciar_gui():
        print("❌ No se pudo iniciar la GUI")
        sys.exit(1)
    
    print("👋 Sistema finalizado")

if __name__ == "__main__":
    main()