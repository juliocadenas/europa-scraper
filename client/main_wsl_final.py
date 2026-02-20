#!/usr/bin/env python3
import os
import sys
import requests
import json
import time
from datetime import datetime

# Añadir raíz del proyecto
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class FinalWSLClient:
    """Cliente final compatible con el frontend"""
    
    def __init__(self, server_url="http://localhost:8001"):
        self.server_url = server_url
        self.session = requests.Session()
    
    def test_connection(self):
        """Prueba la conexión con el servidor"""
        try:
            response = self.session.get(f"{self.server_url}/ping")
            if response.status_code == 200 and "PONG" in response.text:
                print("✅ Conexión con servidor exitosa")
                return True
            else:
                print(f"❌ Respuesta inesperada: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return False
    
    def get_courses(self):
        """Obtiene la lista de cursos"""
        try:
            response = self.session.get(f"{self.server_url}/get_all_courses")
            if response.status_code == 200:
                courses = response.json()
                print(f"✅ Obtenidos {len(courses)} cursos")
                return courses
            else:
                print(f"❌ Error obteniendo cursos: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error obteniendo cursos: {e}")
            return []
    
    def start_scraping(self, from_sic="01.0", to_sic="011903.0", search_engine="Cordis Europa"):
        """Inicia una tarea de scraping"""
        try:
            job_params = {
                'from_sic': from_sic,
                'to_sic': to_sic,
                'search_engine': search_engine,
                'is_headless': True,
                'min_words': 3
            }
            
            response = self.session.post(f"{self.server_url}/start_scraping", json=job_params)
            
            if response.status_code == 202:
                result = response.json()
                print(f"✅ Scraping iniciado: {result['message']}")
                print(f"   Resultados: {result['results_count']}")
                print(f"   Archivo: {result['filename']}")
                return True
            else:
                print(f"❌ Error iniciando scraping: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error iniciando scraping: {e}")
            return False
    
    def get_worker_status(self):
        """Obtiene estado de workers - compatible con frontend"""
        try:
            response = self.session.get(f"{self.server_url}/worker_status")
            if response.status_code == 200:
                status = response.json()
                return status
            else:
                return {"workers": [], "total_workers": 0, "active_workers": 0}
        except Exception as e:
            return {"workers": [], "total_workers": 0, "active_workers": 0}

def main():
    """Función principal del cliente"""
    print("🚀 Cliente WSL Final")
    print("=" * 50)
    
    client = FinalWSLClient()
    
    # Probar conexión
    if not client.test_connection():
        print("❌ No se puede conectar con el servidor")
        return
    
    # Obtener cursos
    courses = client.get_courses()
    if not courses:
        print("❌ No se pueden obtener los cursos")
        return
    
    # Mostrar primeros cursos
    print(f"\n📋 Cursos disponibles (primeros 10):")
    for i, course in enumerate(courses[:10]):
        if isinstance(course, dict):
            sic_code = course.get('sic_code', 'N/A')
            course_name = course.get('course_name', 'N/A')
        else:
            # Si es una tupla
            sic_code, course_name = course
        print(f"   {i+1}. {sic_code} - {course_name}")
    
    # Iniciar scraping de prueba con Cordis Europa
    print(f"\n🔄 Iniciando scraping con Cordis Europa...")
    if client.start_scraping():
        print("✅ Scraping con Cordis Europa iniciado exitosamente")
        
        # Mostrar estado de workers
        print("\n📊 Estado de workers:")
        worker_status = client.get_worker_status()
        print(f"   Workers activos: {worker_status.get('active_workers', 0)}")
        print(f"   Total workers: {worker_status.get('total_workers', 0)}")
    else:
        print("❌ Error iniciando scraping con Cordis Europa")

if __name__ == "__main__":
    main()
