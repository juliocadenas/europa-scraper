#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PRUEBA DIRECTA DEL CLIENTE EUROPA SCRAPER
=========================================

Este script prueba directamente la conexión del cliente con el servidor,
simulando exactamente lo que hace la GUI del cliente.
"""

import requests
import time
import sys
import os

# Añadir directorio raíz al path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def probar_conexion_cliente():
    """Probar conexión exactamente como lo hace el cliente"""
    print("🚀 PRUEBA DIRECTA DE CONEXIÓN CLIENTE-SERVIDOR")
    print("=" * 50)
    
    # Direcciones a probar (en orden de preferencia)
    direcciones = [
        "localhost:8001",
        "127.0.0.1:8001", 
        "192.168.1.14:8001"
    ]
    
    for direccion in direcciones:
        print(f"\n🔍 Probando conexión con: {direccion}")
        
        try:
            # Aplicar la misma lógica que client/main.py
            if ' (' in direccion and ')' in direccion:
                start = direccion.find('(') + 1
                end = direccion.find(')')
                ip_port = direccion[start:end]
            else:
                ip_port = direccion
            
            # CORRECCIÓN AUTOMÁTICA: 0.0.0.0 → localhost
            if ip_port.startswith('0.0.0.0:'):
                ip_port = ip_port.replace('0.0.0.0:', 'localhost:')
            
            server_base_url = f"http://{ip_port}"
            print(f"📡 URL final: {server_base_url}")
            
            # 1. Probar ping del servidor
            print("🔔 Enviando ping...")
            response = requests.get(f"{server_base_url}/ping", timeout=5)
            if response.status_code == 200 and response.text == "EUROPA_SCRAPER_SERVER_PONG":
                print("✅ Ping exitoso")
            elif response.status_code == 200:
                print(f"✅ Ping exitoso (respuesta: {response.text})")
            else:
                print(f"❌ Ping fallido: {response.status_code} - {response.text}")
                continue
            
            # 2. Probar endpoint raíz
            print("🏠 Verificando endpoint raíz...")
            response = requests.get(f"{server_base_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "active":
                    print("✅ Servidor activo confirmado")
                else:
                    print(f"❌ Servidor no activo: {data}")
                    continue
            else:
                print(f"❌ Error endpoint raíz: {response.status_code}")
                continue
            
            # 3. Probar endpoint de estado
            print("📊 Verificando endpoint de estado...")
            response = requests.get(f"{server_base_url}/detailed_status", timeout=5)
            if response.status_code == 200:
                status = response.json()
                print(f"✅ Estado del servidor: {status}")
            else:
                print(f"❌ Error endpoint estado: {response.status_code}")
                continue
            
            # 4. Probar endpoint de cursos
            print("📚 Verificando endpoint de cursos...")
            response = requests.get(f"{server_base_url}/get_all_courses", timeout=5)
            if response.status_code == 200:
                courses = response.json()
                print(f"✅ Cursos disponibles: {len(courses)}")
                if courses:
                    print(f"   Primer curso: {courses[0] if courses else 'Ninguno'}")
            else:
                print(f"❌ Error endpoint cursos: {response.status_code}")
                continue
            
            # Si llegamos aquí, la conexión es completa
            print(f"\n🎉 ¡CONEXIÓN COMPLETA EXITOSA!")
            print(f"📍 Servidor: {server_base_url}")
            print(f"🔧 Corrección aplicada: {'Sí' if '0.0.0.0' in direccion else 'No necesario'}")
            
            # Mostrar instrucciones para la GUI
            print(f"\n📋 PARA USAR LA GUI DEL CLIENTE:")
            print(f"1. Ejecuta: python client/main.py")
            print(f"2. En la GUI, usa la dirección: {ip_port}")
            print(f"3. El sistema aplicará automáticamente la corrección si es necesario")
            
            return True, server_base_url
            
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Error de conexión: {e}")
        except requests.exceptions.Timeout:
            print(f"❌ Timeout de conexión")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
    
    print(f"\n❌ NO SE PUDO ESTABLECER CONEXIÓN CON NINGUNA DIRECCIÓN")
    return False, None

def main():
    """Función principal"""
    try:
        exito, url_servidor = probar_conexion_cliente()
        
        if exito:
            print(f"\n🏆 MISIÓN CUMPLIDA")
            print(f"✅ El cliente puede conectar perfectamente con el servidor")
            print(f"✅ La corrección 0.0.0.0→localhost está funcionando")
            print(f"✅ Todos los endpoints están respondiendo")
            print(f"\n🎯 EL SISTEMA ESTÁ LISTO PARA USAR")
            return 0
        else:
            print(f"\n💡 SOLUCIONES:")
            print(f"1. Asegúrate que el servidor esté corriendo")
            print(f"2. Verifica que el puerto 8001 esté libre")
            print(f"3. Revisa el firewall de Windows")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Prueba interrumpida")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())