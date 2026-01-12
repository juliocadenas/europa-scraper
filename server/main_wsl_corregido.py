#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
import sqlite3
import csv
from datetime import datetime
import random
import shutil
import pandas as pd

# Añadir raíz del proyecto
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Europa Scraper WSL Corregido")

# Estado global para los workers (simulado)
NUM_WORKERS = 5
WORKER_STATUSES = {
    str(i): {
        "status": "idle", # idle, working
        "current_task": "Esperando tarea",
        "progress": 0.0,
        "processed_count": 0,
        "omitted_count": 0,
        "error_count": 0
    }
    for i in range(NUM_WORKERS)
}


class CorregidoScraperController:
    """Controller corregido que genera resultados realistas"""
    
    def __init__(self):
        self.results = []
    
    def generate_results(self, from_sic, to_sic, search_engine, num_results=10):
        """Genera resultados realistas simulados"""
        logger.info(f"Generando {num_results} resultados para {from_sic}-{to_sic}")
        
        # Títulos realistas para Cordis Europa
        titles = [
            f"CORDIS Results: Agricultural Innovation Project {random.randint(1000, 9999)}",
            f"European Commission Study: Sustainable Farming {random.randint(2018, 2024)}",
            f"Horizon Europe Research: Advanced Crop Management {random.randint(2019, 2024)}",
            f"EU Framework Programme: Digital Agriculture {random.randint(2020, 2024)}",
            f"European Research Council: Climate-Smart Agriculture {random.randint(2021, 2024)}",
            f"CORDIS Dataset: Precision Farming Technologies {random.randint(2022, 2024)}",
            f"EU Innovation: AgriTech Startup Analysis {random.randint(2023, 2024)}",
            f"European Study: Smart Irrigation Systems {random.randint(2020, 2024)}",
            f"CORDIS Report: Organic Farming Certification {random.randint(2019, 2024)}",
            f"EU Research: Blockchain in Agriculture {random.randint(2021, 2024)}"
        ]
        
        descriptions = [
            f"This European research project focuses on sustainable agricultural practices across member states. The study examines innovative farming techniques, environmental impact assessment, and policy recommendations for the agricultural sector. Results demonstrate significant improvements in crop yields and resource efficiency.",
            f"Comprehensive analysis of digital transformation in European agriculture, covering IoT sensor networks, machine learning applications, and precision farming technologies. The research shows 40% improvement in operational efficiency and 25% reduction in environmental impact.",
            f"Advanced study on climate adaptation strategies in European farming systems. The research covers drought-resistant crops, smart water management, and carbon-neutral farming techniques. Findings indicate successful adaptation to changing climate patterns across EU regions.",
            f"In-depth analysis of European agricultural policy and its impact on farming practices. The study examines Common Agricultural Policy reforms, subsidy effectiveness, and sustainability metrics. Results provide valuable insights for policy optimization.",
            f"Cutting-edge research on AI applications in European crop management. The study uses computer vision, machine learning, and drone imaging to optimize farming practices. Success rates show 35% improvement in crop disease detection and 20% increase in yields."
        ]
        
        results = []
        for i in range(min(num_results, len(titles))):
            results.append({
                'sic_code': from_sic,
                'course_name': f"Curso {i+1} de {from_sic}",
                'title': titles[i % len(titles)],
                'description': descriptions[i % len(descriptions)],
                'url': f"https://cordis.europa.eu/project/id/{random.randint(1000000, 9999999)}",
                'total_words': f"Total words: {random.randint(50, 200)} | Keyword matches: {random.randint(3, 15)}"
            })
        
        return results

def init_database():
    """Inicializa la base de datos si no existe"""
    try:
        # Usar ruta absoluta para la base de datos
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'courses.db')
        logger.info(f"DEBUG: Usando base de datos en: {db_path}")
        print(f"DEBUG: Usando base de datos en: {db_path}")
        
        if os.path.exists(db_path):
            print(f"DEBUG: El archivo de base de datos YA EXISTE.")
        else:
            print(f"DEBUG: El archivo de base de datos NO EXISTE.")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la tabla existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='courses'")
        if not cursor.fetchone():
            logger.info("DEBUG: Tabla 'courses' no encontrada. Creando nueva e insertando datos por defecto.")
            print("DEBUG: Tabla 'courses' no encontrada. Creando nueva e insertando datos por defecto.")
            # Crear tabla si no existe
            cursor.execute('''
CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sic_code TEXT NOT NULL,
    course_name TEXT NOT NULL,
    status TEXT DEFAULT 'disponible',
    server TEXT DEFAULT 'UNKNOWN_SERVER'
)
''')
            # Insertar datos básicos
            cursos_basicos = [
                ('01.0', 'AGRICULTURAL PRODUCTION CROPS'),
                ('011901.1', 'Pea farms'),
                ('011901.2', 'Vegetable farms'),
                ('011902.0', 'Feeder grains'),
                ('011903.0', 'Oil grains'),
                ('011904.0', 'Field seed'),
                ('011905.0', 'Cotton'),
                ('011906.0', 'Rice'),
                ('011907.0', 'Tobacco'),
                ('011908.0', 'Sugar beets')
            ]
            
            cursor.executemany("INSERT INTO courses (sic_code, course_name) VALUES (?, ?)", cursos_basicos)
            conn.commit()
            logger.info(f"Base de datos inicializada con {len(cursos_basicos)} cursos")
        else:
            print("DEBUG: La tabla 'courses' YA EXISTE. No se tocan los datos.")
            cursor.execute("SELECT COUNT(*) FROM courses")
            count = cursor.fetchone()[0]
            print(f"DEBUG: La tabla tiene {count} filas actualmente.")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error inicializando base de datos: {e}")
        print(f"ERROR CRITICO inicializando DB: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    logger.info("Iniciando aplicación...")
    print("DEBUG: Iniciando aplicación...")
    if init_database():
        logger.info("Base de datos verificada/inicializada correctamente")
    else:
        logger.error("Error al inicializar base de datos")

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {"status": "active", "message": "Europa Scraper WSL Corregido"}

@app.get("/ping")
async def ping():
    """Endpoint de ping"""
    return "EUROPA_SCRAPER_WSL_CORREGIDO_PONG"

@app.get("/get_all_courses")
async def get_all_courses():
    """Obtiene todos los cursos de la base de datos"""
    try:
        # Usar ruta absoluta para la base de datos
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'courses.db')
        print(f"DEBUG: get_all_courses leyendo de: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT sic_code, course_name FROM courses ORDER BY sic_code")
        courses = cursor.fetchall()
        conn.close()
        
        logger.info(f"Retornados {len(courses)} cursos desde la base de datos")
        print(f"DEBUG: Retornando {len(courses)} cursos.")
        # Formatear como lista de diccionarios para compatibilidad
        return [{"sic_code": sic, "course_name": name} for sic, name in courses]
    except Exception as e:
        logger.error(f"Error obteniendo cursos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_simulated_scraping_task(worker_id: str, from_sic: str, to_sic: str, search_engine: str):
    """
    Simula una tarea de scraping larga en segundo plano, actualizando el estado del worker.
    """
    task_description = f"Scraping: {from_sic} a {to_sic} con {search_engine}"
    logger.info(f"Worker {worker_id}: Iniciando tarea: {task_description}")

    # 1. Marcar como 'working'
    WORKER_STATUSES[worker_id].update({
        "status": "working",
        "current_task": task_description,
        "progress": 0.0
    })

    try:
        # 2. Simular progreso
        total_duration = random.uniform(5, 15) # Duración total de la tarea
        steps = 10
        for i in range(steps):
            await asyncio.sleep(total_duration / steps)
            progress = (i + 1) / steps * 100
            WORKER_STATUSES[worker_id]["progress"] = progress
            logger.info(f"Worker {worker_id}: Progreso: {progress:.0f}%")

        # 3. Generar resultados (la lógica de negocio)
        controller = CorregidoScraperController()
        results = controller.generate_results(from_sic, to_sic, search_engine, num_results=5)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"results/corregidos_{from_sic}_to_{to_sic}_{search_engine}_{timestamp}.csv"
        os.makedirs('results', exist_ok=True)
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['sic_code', 'course_name', 'title', 'description', 'url', 'total_words']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        logger.info(f"Worker {worker_id}: Tarea completada. Resultados en {filename}")
        
        # 4. Marcar como finalizado y resetear
        processed_count = len(results) # Asumimos que todos los resultados generados son "procesados"
        omitted_count = random.randint(0, processed_count // 2) # Simular algunos omitidos
        error_count = random.randint(0, 3) # Simular hasta 3 errores

        finished_task_description = (
            f"Tarea completada. Procesados: {processed_count}, Omitidos: {omitted_count}, Errores: {error_count}. "
            f"Resultados guardados en: {os.path.basename(filename)}"
        )
        WORKER_STATUSES[worker_id].update({
            "status": "idle",
            "current_task": finished_task_description,
            "progress": 0.0, # Resetear progreso a 0 para indicar que está libre
            "processed_count": processed_count,
            "omitted_count": omitted_count,
            "error_count": error_count
        })

    except Exception as e:
        logger.error(f"Worker {worker_id}: Error en la tarea de scraping: {e}")
        WORKER_STATUSES[worker_id].update({
            "status": "idle",
            "current_task": f"Error: {e}",
            "progress": 0.0
        })

@app.post("/start_scraping")
async def start_scraping(request_data: dict):
    """Inicia el scraping en un worker disponible."""
    
    # 1. Encontrar un worker disponible
    worker_id = None
    for i in range(NUM_WORKERS):
        if WORKER_STATUSES[str(i)]["status"] == "idle":
            worker_id = str(i)
            break
            
    if worker_id is None:
        logger.warning("No hay workers disponibles para iniciar una nueva tarea.")
        raise HTTPException(status_code=503, detail="No hay workers disponibles (todos están ocupados).")

    # 2. Extraer parámetros
    if 'job_params' in request_data:
        job_params = request_data['job_params']
        from_sic = job_params.get('from_sic', '01.0')
        to_sic = job_params.get('to_sic', '011903.0')
        search_engine = job_params.get('search_engine', 'Cordis Europa')
    else:
        from_sic = request_data.get('from_sic', '01.0')
        to_sic = request_data.get('to_sic', '011903.0')
        search_engine = request_data.get('search_engine', 'Cordis Europa')

    # 3. Iniciar la tarea en segundo plano
    asyncio.create_task(run_simulated_scraping_task(worker_id, from_sic, to_sic, search_engine))

    # 4. Devolver respuesta inmediata
    return JSONResponse(
        status_code=202,
        content={
            "message": f"Tarea de scraping iniciada en el worker {worker_id}. Monitoree /detailed_status para ver el progreso.",
            "worker_id": worker_id
        }
    )

@app.get("/detailed_status")
async def get_detailed_status():
    """Estado detallado del servidor - compatible con frontend"""
    return WORKER_STATUSES

@app.get("/worker_status")
async def get_worker_status():
    """Estado de los workers - compatible con el frontend"""
    return {
        "workers": [],
        "total_workers": 0,
        "active_workers": 0,
        "status": "no workers - simulated mode"
    }

@app.post("/upload_courses")
async def upload_courses(file: UploadFile = File(...)):
    """Sube un archivo de cursos (CSV/Excel) y reemplaza la base de datos."""
    try:
        logger.info(f"Recibiendo archivo: {file.filename}")
        print(f"DEBUG: Recibiendo archivo para upload: {file.filename}")
        
        # Guardar archivo temporalmente
        temp_file = f"temp_{file.filename}"
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Leer archivo con Pandas
        try:
            if temp_file.endswith('.csv'):
                df = pd.read_csv(temp_file, dtype=str)
            elif temp_file.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(temp_file, dtype=str)
            else:
                raise HTTPException(status_code=400, detail="Formato no soportado. Use CSV o Excel.")
        except Exception as e:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise HTTPException(status_code=400, detail=f"Error leyendo archivo: {str(e)}")
            
        # Validar columnas (mínimo 2)
        if len(df.columns) < 2:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise HTTPException(status_code=400, detail="El archivo debe tener al menos 2 columnas (Código y Nombre)")
            
        # Normalizar datos
        courses_data = []
        for _, row in df.iterrows():
            # Asumimos col 0 = sic_code, col 1 = course_name
            if pd.notna(row[0]) and pd.notna(row[1]):
                courses_data.append((str(row[0]).strip(), str(row[1]).strip()))
                
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        if not courses_data:
             raise HTTPException(status_code=400, detail="No se encontraron cursos válidos en el archivo")

        # Actualizar Base de Datos
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'courses.db')
        print(f"DEBUG: upload_courses escribiendo en: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # BORRAR DATOS ANTERIORES
        cursor.execute("DELETE FROM courses")
        print("DEBUG: Datos anteriores borrados.")
        
        # REINICIAR CONTADOR ID (Opcional, para limpieza)
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='courses'")
        
        # INSERTAR NUEVOS DATOS
        cursor.executemany("INSERT INTO courses (sic_code, course_name) VALUES (?, ?)", courses_data)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Base de datos actualizada con {len(courses_data)} cursos nuevos.")
        print(f"DEBUG: Base de datos actualizada con {len(courses_data)} cursos nuevos.")
        
        return {
            "message": f"Carga exitosa. Se han importado {len(courses_data)} cursos.",
            "count": len(courses_data)
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error en upload_courses: {e}")
        print(f"ERROR en upload_courses: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import sys
    
    # Obtener host y puerto de argumentos de línea de comandos
    host = "0.0.0.0"
    port = 8001
    
    if len(sys.argv) > 1:
        for arg in sys.argv:
            if arg.startswith("--host="):
                host = arg.split("=")[1]
            elif arg.startswith("--port="):
                port = int(arg.split("=")[1])
    
    logger.info(f"Iniciando servidor WSL corregido en {host}:{port}...")
    uvicorn.run(app, host=host, port=port, log_level="info")