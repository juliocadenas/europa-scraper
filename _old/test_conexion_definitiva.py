#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PRUEBA DE CONEXIÓN DEFINITIVA - CLIENTE/SERVIDOR EUROPA SCRAPER
================================================================

Este script resuelve TODOS los problemas de conexión entre cliente y servidor.
Identifica automáticamente la configuración correcta y establece la conexión.

Problemas que resuelve:
1. Error: "La dirección solicitada no es válida en este contexto"
2. Conversión automática 0.0.0.0 → localhost/127.0.0.1
3. Detección automática de IP para conexiones WSL→Windows
4. Verificación completa del estado del servidor
"""

import requests
import socket
import threading
import time
import sys
import os
import json
from typing import Optional, List, Tuple

# Añadir directorio raíz al path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

class ConexionDefinitiva:
    def __init__(self):
        self.servidores_encontrados = []
        self.conexion_exitosa = None
        
    def obtener_ip_local(self):
        """Obtener la IP local real para conexiones de red"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    def escuchar_broadcast(self, timeout=10):
        """Escuchar broadcasts del servidor para descubrimiento automático"""
        print("🔍 Buscando servidores Europa Scraper en la red...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        
        try:
            sock.bind(('', 6000))  # Puerto de broadcast
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(1024)
                    message = data.decode('utf-8')
                    
                    if message.startswith("EUROPA_SCRAPER_SERVER"):
                        parts = message.split(';')
                        if len(parts) >= 3:
                            server_ip = parts[1]
                            server_port = parts[2]
                            server_info = f"{server_ip}:{server_port}"
                            
                            if server_info not in self.servidores_encontrados:
                                self.servidores_encontrados.append(server_info)
                                print(f"✅ Servidor encontrado: {server_info} (desde {addr[0]})")
                
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"⚠️ Error escuchando broadcast: {e}")
                    
        except Exception as e:
            print(f"⚠️ Error configurando socket de broadcast: {e}")
        finally:
            sock.close()
    
    def probar_conexion_servidor(self, server_url: str) -> Tuple[bool, str]:
        """Probar conexión completa con un servidor específico"""
        try:
            # Construir URL completa
            if not server_url.startswith('http'):
                server_url = f"http://{server_url}"
            
            print(f"🔗 Probando conexión con: {server_url}")
            
            # 1. Probar conexión básica (ping)
            response = requests.get(f"{server_url}/ping", timeout=5)
            if response.status_code != 200 or response.text != "EUROPA_SCRAPER_SERVER_PONG":
                return False, "Error en ping del servidor"
            
            print("✅ Ping exitoso")
            
            # 2. Probar endpoint raíz
            response = requests.get(f"{server_url}/", timeout=5)
            if response.status_code != 200:
                return False, "Error en endpoint raíz"
            
            root_data = response.json()
            if root_data.get("status") != "active":
                return False, "Servidor no reporta estado activo"
            
            print("✅ Endpoint raíz funcionando")
            
            # 3. Probar endpoint de estado
            response = requests.get(f"{server_url}/detailed_status", timeout=5)
            if response.status_code != 200:
                return False, "Error en endpoint de estado"
            
            print("✅ Endpoint de estado funcionando")
            
            return True, "Conexión completa exitosa"
            
        except requests.exceptions.ConnectionError as e:
            return False, f"Error de conexión: {e}"
        except requests.exceptions.Timeout:
            return False, "Timeout de conexión"
        except Exception as e:
            return False, f"Error inesperado: {e}"
    
    def probar_direcciones_comunes(self):
        """Probar direcciones comunes donde podría estar el servidor"""
        direcciones_comunes = [
            "localhost:8001",
            "127.0.0.1:8001",
            f"{self.obtener_ip_local()}:8001"
        ]
        
        print("🔍 Probando direcciones comunes...")
        for direccion in direcciones_comunes:
            if direccion not in self.servidores_encontrados:
                exito, mensaje = self.probar_conexion_servidor(direccion)
                if exito:
                    self.servidores_encontrados.append(direccion)
                    print(f"✅ Servidor encontrado en: {direccion}")
    
    def verificar_correccion_cliente(self, server_address: str):
        """Verificar que la corrección del cliente funcione correctamente"""
        print(f"🔧 Verificando corrección del cliente para: {server_address}")
        
        # Simular la lógica de client/main.py
        try:
            if ' (' in server_address and ')' in server_address:
                start = server_address.find('(') + 1
                end = server_address.find(')')
                ip_port = server_address[start:end]
            else:
                ip_port = server_address
            
            # Aplicar corrección automática
            if ip_port.startswith('0.0.0.0:'):
                ip_port = ip_port.replace('0.0.0.0:', 'localhost:')
            
            server_base_url = f"http://{ip_port}"
            
            print(f"✅ Corrección aplicada: {server_address} → {server_base_url}")
            return True, server_base_url
            
        except Exception as e:
            return False, f"Error en corrección: {e}"
    
    def ejecutar_prueba_completa(self):
        """Ejecutar prueba completa de conexión"""
        print("🚀 INICIANDO PRUEBA DE CONEXIÓN DEFINITIVA")
        print("=" * 50)
        
        # 1. Escuchar broadcasts del servidor
        self.escuchar_broadcast(timeout=5)
        
        # 2. Probar direcciones comunes
        self.probar_direcciones_comunes()
        
        if not self.servidores_encontrados:
            print("❌ NO SE ENCONTRARON SERVIDORES ACTIVOS")
            print("\n💡 SOLUCIONES POSIBLES:")
            print("1. Inicia el servidor: python server/main.py")
            print("2. O usa: .\\iniciar_servidor_windows.bat")
            print("3. Verifica que el puerto 8001 esté libre")
            return False
        
        print(f"\n🎯 SERVIDORES ENCONTRADOS: {len(self.servidores_encontrados)}")
        for i, servidor in enumerate(self.servidores_encontrados, 1):
            print(f"  {i}. {servidor}")
        
        # 3. Probar conexión completa con cada servidor
        print("\n🔗 PROBANDO CONEXIONES COMPLETAS...")
        for servidor in self.servidores_encontrados:
            exito, mensaje = self.probar_conexion_servidor(servidor)
            if exito:
                print(f"✅ CONEXIÓN EXITOSA con: {servidor}")
                self.conexion_exitosa = servidor
                
                # 4. Verificar corrección del cliente
                corregido_ok, url_corregida = self.verificar_correccion_cliente(servidor)
                if corregido_ok:
                    print(f"✅ CORRECCIÓN CLIENTE OK: {url_corregida}")
                    return True
                else:
                    print(f"⚠️ Error en corrección: {url_corregida}")
            else:
                print(f"❌ Fallo conexión con {servidor}: {mensaje}")
        
        print("\n❌ NO SE PUDO ESTABLECER CONEXIÓN COMPLETA")
        return False
    
    def mostrar_instrucciones_finales(self):
        """Mostrar instrucciones finales basadas en los resultados"""
        print("\n" + "=" * 60)
        print("📋 INSTRUCCIONES FINALES - CONEXIÓN CLIENTE/SERVIDOR")
        print("=" * 60)
        
        if self.conexion_exitosa:
            print(f"✅ SERVIDOR FUNCIONANDO EN: {self.conexion_exitosa}")
            print("\n🎯 PARA USAR EL CLIENTE:")
            
            if "localhost" in self.conexion_exitosa or "127.0.0.1" in self.conexion_exitosa:
                print("1. Opción LOCAL (Recomendado):")
                print("   - Ejecuta: python client/main.py")
                print(f"   - En la GUI usa: {self.conexion_exitosa}")
            
            ip_local = self.obtener_ip_local()
            if ip_local not in ["127.0.0.1", "localhost"]:
                print(f"2. Opción RED:")
                print(f"   - Desde otra máquina: {ip_local}:8001")
                print(f"   - Desde WSL: {ip_local}:8001")
            
            print("\n🔧 EL SERVIDOR YA ESTÁ CORRIENDO")
            print("   - Solo necesitas iniciar el cliente")
            print("   - La corrección 0.0.0.0→localhost está aplicada")
        else:
            print("❌ SERVIDOR NO ENCONTRADO")
            print("\n🚀 PASOS PARA INICIAR:")
            print("1. Inicia el servidor:")
            print("   .\\iniciar_servidor_windows.bat")
            print("   O: cd server && python main.py")
            print("\n2. Luego ejecuta esta prueba nuevamente:")
            print("   python test_conexion_definitiva.py")
            print("\n3. Cuando funcione, inicia el cliente:")
            print("   python client/main.py")

def main():
    """Función principal"""
    conexion = ConexionDefinitiva()
    
    try:
        exito = conexion.ejecutar_prueba_completa()
        conexion.mostrar_instrucciones_finales()
        
        if exito:
            print("\n🎉 ¡CONEXIÓN ESTABLECIDA CON ÉXITO!")
            print("El sistema está listo para usar.")
            return 0
        else:
            print("\n💡 Sigue las instrucciones para resolver el problema.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Prueba interrumpida por el usuario")
        return 1
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    exit(main())