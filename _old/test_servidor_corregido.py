#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar el servidor corregido con el formato de parámetros del frontend
"""

import requests
import json
import time

def test_servidor():
    """Prueba el servidor con ambos formatos de parámetros"""
    
    servidor_url = "http://localhost:8001"
    
    print("🧪 Probando servidor corregido...")
    
    # 1. Probar conexión básica
    try:
        response = requests.get(f"{servidor_url}/ping", timeout=5)
        if response.text == "EUROPA_SCRAPER_WSL_CORREGIDO_PONG":
            print("✅ Conexión básica exitosa")
        else:
            print("❌ Respuesta inesperada en ping")
            return
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("🚀 Asegúrate de que el servidor está corriendo:")
        print("   cd server && python main_wsl_corregido.py")
        return
    
    # 2. Probar formato anidado (el que envía el frontend)
    print("\n📋 Probando formato anidado (frontend)...")
    datos_anidados = {
        'query': '600 a 604',
        'job_params': {
            'from_sic': '600',
            'to_sic': '604',
            'min_words': 30,
            'search_engine': 'DuckDuckGo',
            'output_format': 'CSV'
        }
    }
    
    try:
        response = requests.post(f"{servidor_url}/start_scraping", json=datos_anidados, timeout=10)
        if response.status_code == 200:
            resultado = response.json()
            print(f"✅ Formato anidado funciona: {resultado.get('message', 'OK')}")
            print(f"📁 Archivo generado: {resultado.get('filename', 'N/A')}")
        else:
            print(f"❌ Error en formato anidado: {response.status_code}")
            print(f"📄 Detalles: {response.text}")
    except Exception as e:
        print(f"❌ Error probando formato anidado: {e}")
    
    # 3. Probar formato directo (compatibilidad)
    print("\n📋 Probando formato directo (compatibilidad)...")
    datos_directos = {
        'from_sic': '01.0',
        'to_sic': '011903.0',
        'search_engine': 'Cordis Europa',
        'min_words': 50,
        'output_format': 'CSV'
    }
    
    try:
        response = requests.post(f"{servidor_url}/start_scraping", json=datos_directos, timeout=10)
        if response.status_code == 200:
            resultado = response.json()
            print(f"✅ Formato directo funciona: {resultado.get('message', 'OK')}")
            print(f"📁 Archivo generado: {resultado.get('filename', 'N/A')}")
        else:
            print(f"❌ Error en formato directo: {response.status_code}")
            print(f"📄 Detalles: {response.text}")
    except Exception as e:
        print(f"❌ Error probando formato directo: {e}")
    
    # 4. Probar obtención de cursos
    print("\n📚 Probando obtención de cursos...")
    try:
        response = requests.get(f"{servidor_url}/get_all_courses", timeout=10)
        if response.status_code == 200:
            cursos = response.json()
            print(f"✅ Cursos obtenidos: {len(cursos)} cursos")
            if cursos:
                print(f"📝 Primer curso: {cursos[0]}")
        else:
            print(f"❌ Error obteniendo cursos: {response.status_code}")
    except Exception as e:
        print(f"❌ Error obteniendo cursos: {e}")
    
    print("\n🎉 Prueba completada. El servidor debería funcionar ahora con el frontend.")

if __name__ == "__main__":
    test_servidor()