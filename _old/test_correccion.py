#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from client.main import ClientApp

print("🧪 Probando corrección del cliente...")
print("=" * 50)

try:
    app = ClientApp()
    
    # Probar la corrección
    print("📥 Enviando dirección: 0.0.0.0:8001")
    app.set_server_address('0.0.0.0:8001')
    
    print(f"✅ URL resultante: {app.server_base_url}")
    
    # Verificar que se aplicó la corrección
    if "localhost" in app.server_base_url:
        print("✅ CORRECCIÓN APLICADA: 0.0.0.0 → localhost")
    else:
        print("❌ CORRECCIÓN NO APLICADA")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("=" * 50)