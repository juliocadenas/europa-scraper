#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Añadir raíz del proyecto
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Europa Scraper WSL Minimal")

class MockScraperController:
    """Mock controller que simula el scraping sin navegador"""
    
    def __init__(self):
        self.results = []
    
    async def run_scraping(self, params: dict, progress_callback=None, worker_id: int = 0):
        """Simula el scraping para WSL"""
        logger.info(f"Simulando scraping para {params}")
        
        from_sic = params.get('from_sic', '01.0')
        to_sic = params.get('to_sic', '011903.0')
        search_engine = params.get('search_engine', 'Cordis Europa')
        
        # Generar resultados simulados
        mock_results = []
        for i in range(5):  # 5 resultados simulados
            mock_results.append({
                'sic_code': from_sic,
                'course_name': f'Curso Simulado {i+1}',
                'title': f'Resultado Simulado {i+1} para {search_engine}',
                'description': f'Descripción simulada para el curso {i+1}',
                'url': f'https://example.com/result{i+1}',
                'total_words': f'Total words: {50+i*10} | Keyword matches: 5'
            })
        
        self.results = mock_results
        
        if progress_callback:
            progress_callback(100, f"Scraping simulado completado para {from_sic}-{to_sic}")
        
        return mock_results

# Crear instancia del mock controller
mock_controller = MockScraperController()

@app.post("/start_scraping")
async def start_scraping(job_params):
    """Endpoint para iniciar scraping simulado"""
    try:
        logger.info(f"Iniciando scraping simulado: {job_params}")
        
        # Simular procesamiento
        results = await mock_controller.run_scraping(job_params.dict())
        
        return {"message": f"Scraping simulado iniciado. Se generaron {len(results)} resultados mock"}
    except Exception as e:
        logger.error(f"Error en scraping simulado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/detailed_status")
async def get_detailed_status():
    """Endpoint para verificar estado"""
    return {
        "status": "active",
        "message": "Servidor WSL minimal funcionando",
        "mock_mode": True
    }

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {"status": "active", "message": "Europa Scraper WSL Minimal Server"}

@app.get("/ping")
async def ping():
    """Endpoint de ping"""
    return "EUROPA_SCRAPER_WSL_MINIMAL_PONG"

if __name__ == "__main__":
    logger.info("Iniciando servidor WSL minimal...")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
