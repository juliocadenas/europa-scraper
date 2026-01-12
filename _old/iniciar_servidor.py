#!/usr/bin/env python3
"""
Script para iniciar el servidor Europa Scraper
"""
import os
import sys
import subprocess

def get_wsl_ip():
    """Obtiene la IP de WSL ejecutando un comando de shell."""
    if 'linux' in sys.platform:
        try:
            command = "ip route show | grep -i default | awk '{ print $3}'"
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            ip_address = result.stdout.strip()
            return ip_address
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"No se pudo obtener la IP de WSL: {e}")
            return "localhost"
    return "localhost"

def print_server_info():
    """Imprime la información del servidor, incluyendo la IP de WSL si está disponible."""
    print("====================================================")
    print("      INICIANDO SERVIDOR EUROPA SCRAPER")
    print("====================================================")
    wsl_ip = get_wsl_ip()
    print(f"✅ IP del servidor detectada: {wsl_ip}")
    print(f"   Usa esta dirección en el cliente: {wsl_ip}:8001")
    print("----------------------------------------------------")

print_server_info()

# Cambiar al directorio server
# Asegurarse de que la ruta al directorio 'server' sea correcta
server_dir = os.path.join(os.path.dirname(__file__), 'server')
if os.path.isdir(server_dir):
    os.chdir(server_dir)
    # Añadir el directorio del servidor al path para asegurar importaciones correctas
    sys.path.insert(0, os.path.abspath(os.getcwd()))
else:
    print(f"❌ Error: No se encuentra el directorio 'server' en {os.path.dirname(__file__)}")
    sys.exit(1)


# Importar y ejecutar el servidor
if __name__ == "__main__":
    from main import ScraperServer
    server = ScraperServer()
    server.run()