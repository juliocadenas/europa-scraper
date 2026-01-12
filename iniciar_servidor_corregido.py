#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de inicio unificado para el servidor corregido
=================================================
Este script inicia el servidor main_wsl_corregido.py en el puerto 8001
asegurándose de que no haya conflictos con otros procesos.
"""

import os
import sys
import subprocess
import time
import socket
import signal
import sys

# Importación opcional de psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil no disponible - usando métodos alternativos para limpieza de procesos")

def check_port(port):
    """Verifica si un puerto está en uso"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            return result == 0
    except:
        return False

def kill_processes_on_port(port):
    """Mata todos los procesos usando el puerto especificado"""
    if PSUTIL_AVAILABLE:
        try:
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    for conn in proc.info['connections'] or []:
                        if conn.laddr.port == port:
                            print(f"🔪 Terminando proceso {proc.info['pid']} ({proc.info['name']}) usando puerto {port}")
                            proc.kill()
                            time.sleep(1)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            print(f"⚠️  Error limpiando procesos con psutil: {e}")
    else:
        # Método alternativo sin psutil
        try:
            print(f"🔪 Usando método alternativo para liberar puerto {port}")
            # Usar fuser o lsof para encontrar y matar procesos en el puerto
            subprocess.run(['fuser', '-k', f'{port}/tcp'], check=False, capture_output=True)
            time.sleep(1)
            # Intentar con lsof si fuser no está disponible
            subprocess.run(['lsof', '-ti', f':{port}', '|', 'xargs', 'kill'],
                         shell=True, check=False, capture_output=True)
            time.sleep(1)
        except Exception as e:
            print(f"⚠️  Error limpiando procesos con método alternativo: {e}")

def start_server():
    """Inicia el servidor corregido"""
    print("🚀 Iniciando Servidor Europa Scraper Corregido")
    print("=" * 50)
    
    # Cambiar al directorio server
    server_dir = os.path.join(os.path.dirname(__file__), 'server')
    os.chdir(server_dir)
    print(f"📁 Directorio de trabajo: {os.getcwd()}")
    
    # Verificar y limpiar puerto 8001
    port = 8001
    if check_port(port):
        print(f"⚠️  Puerto {port} está en uso. Limpiando procesos...")
        kill_processes_on_port(port)
        time.sleep(2)
        
        if check_port(port):
            print(f"❌ No se pudo liberar el puerto {port}. Por favor, manualmente termine los procesos.")
            return False
    
    # Verificar que el archivo main_wsl_corregido.py existe
    server_file = 'main_wsl_corregido.py'
    if not os.path.exists(server_file):
        print(f"❌ No se encuentra el archivo: {server_file}")
        return False
    
    print(f"✅ Iniciando servidor desde: {server_file}")
    print(f"🌐 Servidor disponible en: http://localhost:{port}")
    print(f"🏓 Endpoint de ping: http://localhost:{port}/ping")
    print(f"📊 Endpoint de scraping: http://localhost:{port}/start_scraping")
    print("=" * 50)
    print("📝 Presione Ctrl+C para detener el servidor")
    print()
    
    try:
        # Iniciar el servidor
        cmd = [sys.executable, server_file]
        process = subprocess.Popen(cmd, 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.STDOUT,
                               universal_newlines=True,
                               bufsize=1)
        
        # Manejar señales para cerrado limpio
        def signal_handler(sig, frame):
            print("\n🛑 Deteniendo servidor...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Mostrar salida del servidor en tiempo real
        for line in process.stdout:
            print(line.rstrip())
            
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido por el usuario")
    except Exception as e:
        print(f"❌ Error iniciando servidor: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = start_server()
    if not success:
        sys.exit(1)