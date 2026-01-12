#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar el servidor actual (server.py) con la corrección aplicada
"""

import requests
import json
import time

def probar_servidor():
    """Prueba el servidor server.py con el formato del frontend"""
    
    servidor_url = "http://localhost:8001"
    
    print("🧪 Probando servidor server.py corregido...")
    
    # 1. Probar conexión básica
    try:
        response = requests.get(f"{servidor_url}/ping", timeout=5)
        if response.text.strip('"') == "EUROPA_SCRAPER_WSL_CORREGIDO_PONG":
            print("✅ Conexión básica exitosa")
        else:
            print("❌ Respuesta inesperada en ping")
            print(f"   Esperado: EUROPA_SCRAPER_WSL_CORREGIDO_PONG")
            recibido = response.text.strip('"')
            print(f"   Recibido: {recibido}")
            return
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("🚀 Asegúrate de que el servidor está corriendo:")
        print("   cd server && python server.py")
        return
    
    # 2. Probar formato anidado (el que causa el error)
    print("\n📋 Probando formato anidado (el que envía el frontend)...")
    datos_anidados = {
        'query': '600 a 604',
        'job_params': {
            'from_sic': '600',
            'to_sic': '604',
            'min_words': 30,
            'search_engine': 'DuckDuckGo',
            'output_format': 'CSV',
            'is_headless': True
        }
    }
    
    try:
        response = requests.post(f"{servidor_url}/start_scraping", json=datos_anidados, timeout=10)
        print(f"📊 Código de estado: {response.status_code}")
        
        if response.status_code == 202:
            resultado = response.json()
            print(f"✅ Formato anidado funciona: {resultado.get('message', 'OK')}")
        else:
            print(f"❌ Error en formato anidado: {response.status_code}")
            print(f"📄 Respuesta: {response.text}")
            
            # Intentar analizar el error
            try:
                error_json = response.json()
                print(f"🔍 Error detallado: {json.dumps(error_json, indent=2)}")
            except:
                pass
                
    except Exception as e:
        print(f"❌ Error probando formato anidado: {e}")
    
    # 3. Probar formato directo (compatibilidad)
    print("\n📋 Probando formato directo (compatibilidad)...")
    datos_directos = {
        'from_sic': '01.0',
        'to_sic': '011903.0',
        'search_engine': 'Cordis Europa',
        'min_words': 50,
        'is_headless': True
    }
    
    try:
        response = requests.post(f"{servidor_url}/start_scraping", json=datos_directos, timeout=10)
        print(f"📊 Código de estado: {response.status_code}")
        
        if response.status_code == 202:
            resultado = response.json()
            print(f"✅ Formato directo funciona: {resultado.get('message', 'OK')}")
        else:
            print(f"❌ Error en formato directo: {response.status_code}")
            print(f"📄 Respuesta: {response.text}")
            
    except Exception as e:
        print(f"❌ Error probando formato directo: {e}")
    
    print("\n🎉 Prueba completada.")
    print("📝 Si ves '✅ Formato anidado funciona', el problema está resuelto.")
    print("🔄 Reinicia el servidor y vuelve a intentar desde el frontend.")

if __name__ == "__main__":
    probar_servidor()