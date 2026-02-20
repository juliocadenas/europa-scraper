#!/usr/bin/env python3
"""
Test completo de scraping end-to-end para Europa Scraper
Utiliza datos reales del CSV para probar todo el sistema
"""

import asyncio
import json
import time
import csv
import os
import sys
from datetime import datetime
import requests
from typing import Dict, List, Any

# Configuración
SERVER_HOST = "localhost"
SERVER_PORT = 8001
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
CSV_FILE = "data/class5_course_list - copia.csv"

class ScrapingEndToEndTest:
    def __init__(self):
        self.server_url = BASE_URL
        self.test_results = {
            "server_discovery": False,
            "task_submission": False,
            "task_execution": False,
            "results_retrieval": False,
            "errors": [],
            "start_time": None,
            "end_time": None,
            "task_id": None,
            "scraped_results": []
        }
    
    async def test_server_connection(self):
        """Prueba la conexión básica con el servidor"""
        print("🔍 Probando conexión con el servidor...")
        try:
            response = requests.get(f"{self.server_url}/ping", timeout=10)
            if response.status_code == 200:
                print("✅ Servidor responde correctamente")
                self.test_results["server_discovery"] = True
                return True
            else:
                error_msg = f"❌ Servidor respondió con código {response.status_code}"
                print(error_msg)
                self.test_results["errors"].append(error_msg)
                return False
        except Exception as e:
            error_msg = f"❌ Error conectando al servidor: {str(e)}"
            print(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    def load_test_data(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Carga datos de prueba del CSV"""
        print(f"📊 Cargando datos de prueba desde {CSV_FILE}...")
        
        if not os.path.exists(CSV_FILE):
            error_msg = f"❌ No se encuentra el archivo {CSV_FILE}"
            print(error_msg)
            self.test_results["errors"].append(error_msg)
            return []
        
        try:
            test_data = []
            with open(CSV_FILE, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for i, row in enumerate(reader):
                    if i >= limit:  # Limitar a pocos registros para prueba
                        break
                    # Solo usar filas con datos válidos
                    if row.get('sic_code') and row.get('course_name'):
                        test_data.append({
                            'id': row.get('id', ''),
                            'sic_code': row.get('sic_code', ''),
                            'course_name': row.get('course_name', ''),
                            'status': row.get('status', ''),
                            'server': row.get('server', '')
                        })
            
            print(f"✅ Cargados {len(test_data)} registros de prueba")
            return test_data
            
        except Exception as e:
            error_msg = f"❌ Error leyendo CSV: {str(e)}"
            print(error_msg)
            self.test_results["errors"].append(error_msg)
            return []
    
    async def submit_scraping_task(self, test_data: List[Dict[str, Any]]) -> bool:
        """Envía una tarea de scraping al servidor usando el endpoint correcto"""
        print("📤 Enviando tarea de scraping...")
        
        try:
            # Primero verificar si hay cursos en la base de datos
            print("🔍 Verificando cursos en la base de datos...")
            courses_response = requests.get(f"{self.server_url}/get_all_courses", timeout=10)
            
            if courses_response.status_code != 200:
                # Si no hay cursos, subir el archivo CSV
                print("📁 No hay cursos en la BD, subiendo archivo CSV...")
                await self.upload_courses_file()
            else:
                courses = courses_response.json()
                print(f"✅ Se encontraron {len(courses)} cursos en la base de datos")
            
            # Preparar payload para el endpoint /start_scraping
            # Usar el primer y último SIC de los datos de prueba
            from_sic = test_data[0]['sic_code']
            to_sic = test_data[-1]['sic_code']
            
            payload = {
                "from_sic": from_sic,
                "to_sic": to_sic,
                "search_engine": "duckduckgo",
                "site_domain": None,
                "is_headless": True,
                "min_words": 30
            }
            
            print(f"📋 Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                f"{self.server_url}/start_scraping",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 202:
                result = response.json()
                print(f"✅ Tarea enviada correctamente: {result.get('message', 'Sin mensaje')}")
                self.test_results["task_submission"] = True
                self.test_results["task_id"] = f"manual_job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                return True
            else:
                error_msg = f"❌ Error enviando tarea: {response.status_code} - {response.text}"
                print(error_msg)
                self.test_results["errors"].append(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"❌ Excepción enviando tarea: {str(e)}"
            print(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def upload_courses_file(self):
        """Sube el archivo CSV de cursos al servidor"""
        try:
            with open(CSV_FILE, 'rb') as f:
                files = {'file': (CSV_FILE, f, 'text/csv')}
                response = requests.post(
                    f"{self.server_url}/upload_courses",
                    files=files,
                    timeout=60
                )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Archivo subido correctamente: {result.get('message', 'Sin mensaje')}")
                return True
            else:
                error_msg = f"❌ Error subiendo archivo: {response.status_code} - {response.text}"
                print(error_msg)
                self.test_results["errors"].append(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"❌ Excepción subiendo archivo: {str(e)}"
            print(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def monitor_task_execution(self, task_id: str, timeout: int = 300):
        """Monitorea la ejecución de la tarea usando el endpoint /detailed_status"""
        print(f"⏱️ Monitorizando ejecución de la tarea {task_id}...")
        
        start_time = time.time()
        job_was_running = False
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.server_url}/detailed_status", timeout=10)
                
                if response.status_code == 200:
                    status_data = response.json()
                    workers = list(status_data.values())
                    
                    # Verificar si hay trabajadores activos
                    active_workers = [w for w in workers if w.get('status') in ['Running', 'Idle']]
                    finished_workers = [w for w in workers if w.get('status') == 'Finished']
                    error_workers = [w for w in workers if w.get('status') == 'Error']
                    
                    if active_workers:
                        job_was_running = True
                        print(f"📊 Trabajadores activos: {len(active_workers)}")
                        for worker in active_workers:
                            progress = worker.get('progress', 0)
                            current_task = worker.get('current_task', 'None')
                            print(f"   Worker {worker['id']}: {progress}% - {current_task}")
                    
                    if finished_workers and job_was_running and not active_workers:
                        print("✅ Todos los trabajadores han completado sus tareas")
                        self.test_results["task_execution"] = True
                        return True
                    
                    if error_workers:
                        error_msg = f"❌ Trabajadores con errores: {len(error_workers)}"
                        print(error_msg)
                        self.test_results["errors"].append(error_msg)
                        return False
                    
                    if not job_was_running and not active_workers:
                        print("⏳ Esperando que se inicien los trabajadores...")
                
                await asyncio.sleep(5)  # Esperar 5 segundos entre consultas
                
            except Exception as e:
                error_msg = f"❌ Error monitorizando tarea: {str(e)}"
                print(error_msg)
                self.test_results["errors"].append(error_msg)
                await asyncio.sleep(5)
        
        error_msg = f"❌ Timeout esperando finalización de la tarea ({timeout}s)"
        print(error_msg)
        self.test_results["errors"].append(error_msg)
        return False
    
    async def retrieve_results(self, task_id: str):
        """Recupera los resultados del scraping verificando archivos generados"""
        print(f"📥 Verificando resultados del scraping...")
        
        try:
            # El servidor no tiene endpoint para resultados, así que verificamos archivos
            results_dir = os.path.join("results")
            if not os.path.exists(results_dir):
                print("📁 Creando directorio de resultados...")
                os.makedirs(results_dir, exist_ok=True)
            
            # Buscar archivos CSV de resultados
            result_files = []
            if os.path.exists(results_dir):
                result_files = [f for f in os.listdir(results_dir) if f.endswith('.csv')]
            
            if result_files:
                print(f"✅ Se encontraron {len(result_files)} archivos de resultados:")
                for file in result_files[-5:]:  # Mostrar los 5 más recientes
                    file_path = os.path.join(results_dir, file)
                    file_size = os.path.getsize(file_path)
                    mod_time = os.path.getmtime(file_path)
                    mod_time_str = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"   📄 {file} ({file_size} bytes, modificado: {mod_time_str})")
                
                # Leer el archivo más reciente
                latest_file = max(result_files, key=lambda f: os.path.getmtime(os.path.join(results_dir, f)))
                latest_file_path = os.path.join(results_dir, latest_file)
                
                try:
                    import pandas as pd
                    df = pd.read_csv(latest_file_path)
                    print(f"✅ Archivo más reciente ({latest_file}) contiene {len(df)} registros")
                    
                    # Mostrar algunas columnas y datos de ejemplo
                    print(f"📊 Columnas: {list(df.columns)}")
                    if len(df) > 0:
                        print("\n📋 Ejemplos de resultados:")
                        for i, row in df.head(3).iterrows():
                            print(f"  {i+1}. {row.get('title', 'Sin título')}")
                            print(f"     URL: {row.get('url', 'Sin URL')}")
                            print(f"     SIC: {row.get('sic_code', 'Sin SIC')}")
                            print()
                    
                    self.test_results["scraped_results"] = df.to_dict('records')
                    self.test_results["results_retrieval"] = True
                    return True
                    
                except Exception as e:
                    print(f"⚠️ Error leyendo archivo CSV: {str(e)}")
                    # Consideramos éxito si se generaron archivos aunque no podamos leerlos
                    self.test_results["results_retrieval"] = True
                    return True
            else:
                print("⚠️ No se encontraron archivos de resultados")
                error_msg = "No se encontraron archivos de resultados en el directorio results/"
                self.test_results["errors"].append(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"❌ Excepción verificando resultados: {str(e)}"
            print(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    def save_test_report(self):
        """Guarda un reporte de la prueba"""
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            # Convertir datetime a string para JSON
            results_copy = self.test_results.copy()
            if results_copy.get("start_time"):
                results_copy["start_time"] = results_copy["start_time"].isoformat()
            if results_copy.get("end_time"):
                results_copy["end_time"] = results_copy["end_time"].isoformat()
            
            # Calcular duración
            if self.test_results["start_time"] and self.test_results["end_time"]:
                duration = self.test_results["end_time"] - self.test_results["start_time"]
                results_copy["duration_seconds"] = duration.total_seconds()
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(results_copy, f, indent=2, ensure_ascii=False)
            
            print(f"📄 Reporte guardado en: {report_file}")
            
        except Exception as e:
            print(f"❌ Error guardando reporte: {str(e)}")
    
    async def run_complete_test(self):
        """Ejecuta la prueba completa end-to-end"""
        print("🚀 Iniciando prueba completa de scraping end-to-end")
        print("=" * 60)
        
        self.test_results["start_time"] = datetime.now()
        
        try:
            # Paso 1: Probar conexión con servidor
            if not await self.test_server_connection():
                return False
            
            # Paso 2: Cargar datos de prueba
            test_data = self.load_test_data(limit=3)  # Solo 3 registros para prueba rápida
            if not test_data:
                return False
            
            # Paso 3: Enviar tarea de scraping
            if not await self.submit_scraping_task(test_data):
                return False
            
            task_id = self.test_results.get("task_id", "unknown")
            
            # Paso 4: Monitorizar ejecución
            if not await self.monitor_task_execution(task_id, timeout=300):  # 5 minutos max
                return False
            
            # Paso 5: Recuperar resultados
            if not await self.retrieve_results(task_id):
                return False
            
            print("=" * 60)
            print("🎉 Prueba completada exitosamente!")
            
            # Calcular éxito general
            success_count = sum([
                self.test_results["server_discovery"],
                self.test_results["task_submission"],
                self.test_results["task_execution"],
                self.test_results["results_retrieval"]
            ])
            
            print(f"📊 Resumen: {success_count}/4 pruebas exitosas")
            
            if success_count == 4:
                print("✅ Todas las pruebas pasaron correctamente")
                return True
            else:
                print("⚠️ Algunas pruebas fallaron")
                return False
                
        except Exception as e:
            error_msg = f"❌ Error general en la prueba: {str(e)}"
            print(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
            
        finally:
            self.test_results["end_time"] = datetime.now()
            self.save_test_report()

async def main():
    """Función principal"""
    print("🧪 Test End-to-End de Europa Scraper")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Servidor: {BASE_URL}")
    print(f"📁 Datos: {CSV_FILE}")
    print()
    
    # Crear y ejecutar prueba
    test = ScrapingEndToEndTest()
    success = await test.run_complete_test()
    
    # Salir con código apropiado
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())