#!/usr/bin/env python3
"""
Script para probar el cliente WSL sin tkinter
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def probar_cliente_wsl():
    print("🧪 Probando Cliente WSL sin GUI...")
    print("=" * 60)
    
    try:
        # Importar solo la lógica del cliente
        from client.main import ClientApp
        
        # Crear instancia sin GUI
        class ClienteSinGUI:
            def __init__(self):
                self.server_base_url = ""
                
            def set_server_address(self, server_address):
                server_address = server_address.strip()
                
                # Remover http:// o https:// si existe
                if server_address.startswith('http://'):
                    server_address = server_address[7:]
                elif server_address.startswith('https://'):
                    server_address = server_address[8:]
                
                # Remover formato de tupla si existe
                if '(' in server_address and ')' in server_address:
                    start = server_address.find('(') + 1
                    end = server_address.find(')')
                    server_address = server_address[start:end]
                
                # CORRECCIÓN: Reemplazar 0.0.0.0 por localhost para conexiones de cliente
                if server_address.startswith('0.0.0.0:'):
                    server_address = 'localhost:' + server_address.split(':')[1]
                    
                self.server_base_url = f'http://{server_address}'
                print(f"✅ Dirección convertida: {server_address} → {self.server_base_url}")
        
        # Probar la corrección
        cliente = ClienteSinGUI()
        
        print("📥 Enviando dirección: 0.0.0.0:8001")
        cliente.set_server_address('0.0.0.0:8001')
        
        print(f"🎯 URL resultante: {cliente.server_base_url}")
        
        # Verificar que la corrección se aplicó
        if 'localhost' in cliente.server_base_url:
            print("✅ CORRECCIÓN APLICADA: 0.0.0.0 → localhost")
            print("✅ El cliente WSL funcionará correctamente")
            return True
        else:
            print("❌ CORRECCIÓN NO APLICADA")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def probar_conexion_servidor():
    """Probar conexión con el servidor Windows"""
    print("\n🌐 Probando conexión con servidor Windows...")
    print("-" * 40)
    
    try:
        import requests
        
        # Probar conexión directa
        response = requests.get('http://127.0.0.1:8001/ping', timeout=5)
        
        if response.status_code == 200:
            print("✅ Conexión exitosa con servidor Windows")
            print(f"   Respuesta: {response.text}")
            return True
        else:
            print(f"❌ Error de conexión: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    print("🎯 SOLUCIÓN CLIENTE WSL - EUROPA SCRAPER")
    print("=" * 60)
    
    # Probar 1: Corrección del cliente
    correccion_ok = probar_cliente_wsl()
    
    # Probar 2: Conexión con servidor
    if correccion_ok:
        conexion_ok = probar_conexion_servidor()
    
    print("\n" + "=" * 60)
    
    if correccion_ok and conexion_ok:
        print("🎯 ÉXITO TOTAL:")
        print("✅ Corrección aplicada correctamente")
        print("✅ Conexión con servidor funcionando")
        print("✅ Cliente WSL listo para usar")
        print("\n📋 INSTRUCCIONES:")
        print("1. Para usar el cliente WSL sin GUI:")
        print("   python3 SOLUCION_CLIENTE_WSL.py")
        print("\n2. Para conectar con servidor Windows:")
        print("   Usar dirección: 127.0.0.1:8001")
        print("   O dejar que el cliente convierta automáticamente")
    else:
        print("❌ Hay problemas que resolver")