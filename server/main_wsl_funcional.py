#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import sqlite3
import csv
from datetime import datetime
import random

# Añadir raíz del proyecto
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Europa Scraper WSL Funcional")

class MockScraperController:
    """Mock controller que genera resultados realistas"""
    
    def __init__(self):
        self.results = []
    
    def generate_results(self, from_sic, to_sic, search_engine, num_results=10):
        """Genera resultados realistas simulados"""
        logger.info(f"Generando {num_results} resultados para {from_sic}-{to_sic}")
        
        # Títulos y descripciones realistas para diferentes industrias
        titles = [
            f"Research on {search_engine} - Agricultural Innovation {random.randint(2010, 2024)}",
            f"Sustainable Farming Practices in {search_engine} Region {random.randint(2015, 2024)}",
            f"Advanced Crop Management Systems {random.randint(2018, 2024)}",
            f"Digital Agriculture Transformation {search_engine} {random.randint(2019, 2024)}",
            f"Climate-Smart Agriculture Solutions {random.randint(2020, 2024)}",
            f"Precision Farming Technologies {search_engine} {random.randint(2021, 2024)}",
            f"AgriTech Startup Funding Analysis {search_engine} {random.randint(2022, 2024)}",
            f"Smart Irrigation Management Systems {random.randint(2023, 2024)}",
            f"Organic Farming Certification {search_engine} {random.randint(2017, 2024)}",
            f"Blockchain in Agriculture Supply Chain {random.randint(2018, 2024)}",
            f"AI-Powered Crop Disease Detection {random.randint(2019, 2024)}",
            f"Vertical Farming Market Analysis {search_engine} {random.randint(2020, 2024)}"
        ]
        
        descriptions = [
            f"This comprehensive study analyzes the latest innovations in agricultural technology and their impact on crop yields. The research covers precision farming techniques, IoT integration, and sustainable practices implemented across European farms. Results show significant improvements in resource efficiency and crop quality.",
            f"An in-depth analysis of modern farming practices focusing on environmental sustainability. The study examines water conservation techniques, soil health management, and renewable energy integration in agricultural operations. Key findings include 30% reduction in water usage and 25% increase in organic certification rates.",
            f"This research presents advanced management systems for large-scale agricultural operations. The study covers automated monitoring, predictive analytics, and optimization algorithms that have demonstrated 40% improvement in operational efficiency and 20% reduction in waste.",
            f"Cutting-edge research on digital transformation in agriculture, focusing on IoT sensor networks, machine learning algorithms, and real-time decision support systems. Implementation across 500 farms showed average yield increases of 15% and cost reductions of 22%.",
            f"Comprehensive analysis of climate adaptation strategies in European agriculture. The research covers drought-resistant crops, smart water management, and carbon-neutral farming techniques. Results indicate successful adaptation to changing climate patterns.",
            f"Study on smart irrigation systems using AI and sensor networks. The research demonstrates 35% water savings while maintaining or improving crop yields through precision irrigation scheduling and leak detection.",
            f"Analysis of emerging agricultural technologies and their market potential. The study covers vertical farming, hydroponics, and alternative protein sources. Market projections indicate $50B growth by 2030.",
            f"Research on organic farming certification processes and market trends. The study analyzes certification standards, consumer preferences, and price premiums across European markets. Findings show 25% price premiums for certified products.",
            f"Comprehensive study on blockchain applications in agricultural supply chains. The research covers traceability, smart contracts, and automated quality control. Implementation shows 40% reduction in administrative costs and 60% improvement in traceability.",
            f"Advanced research on AI applications in crop disease detection and prevention. The study uses computer vision, machine learning, and drone imaging to detect diseases 7 days earlier than traditional methods. Success rate: 92%.",
            f"Market analysis of vertical farming trends and investment opportunities. The study covers controlled environment agriculture, urban farming integration, and investment patterns. Market size projected to reach $200B by 2035.",
            f"Study on IoT sensor networks in precision agriculture. The research covers soil monitoring, weather prediction, and automated irrigation systems. Results show 30% improvement in resource efficiency and 20% increase in crop yields."
        ]
        
        results = []
        for i in range(min(num_results, len(titles))):
            results.append({
                'sic_code': from_sic,
                'course_name': f"Curso {i+1} de {from_sic}",
                'title': titles[i % len(titles)],
                'description': descriptions[i % len(descriptions)],
                'url': f"https://example.com/result{i+1}",
                'total_words': f"Total words: {random.randint(50, 200)} | Keyword matches: {random.randint(3, 15)}"
            })
        
        return results

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {"status": "active", "message": "Europa Scraper WSL Funcional"}

@app.get("/ping")
async def ping():
    """Endpoint de ping"""
    return "EUROPA_SCRAPER_WSL_FUNCIONAL_PONG"

@app.get("/get_all_courses")
async def get_all_courses():
    """Obtiene todos los cursos de la base de datos"""
    try:
        conn = sqlite3.connect('courses.db')
        cursor = conn.cursor()
        cursor.execute("SELECT sic_code, course_name FROM courses ORDER BY sic_code")
        courses = cursor.fetchall()
        conn.close()
        
        logger.info(f"Retornados {len(courses)} cursos desde la base de datos")
        return courses
    except Exception as e:
        logger.error(f"Error obteniendo cursos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/start_scraping")
async def start_scraping(job_params):
    """Inicia scraping simulado"""
    try:
        from_sic = job_params.get('from_sic', '01.0')
        to_sic = job_params.get('to_sic', '011903.0')
        search_engine = job_params.get('search_engine', 'Cordis Europa')
        
        logger.info(f"Iniciando scraping simulado: {from_sic} a {to_sic} con {search_engine}")
        
        # Generar resultados simulados
        mock_controller = MockScraperController()
        results = mock_controller.generate_results(from_sic, to_sic, search_engine, num_results=5)
        
        # Crear archivo CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"results/simulados_{from_sic}_to_{to_sic}_{search_engine}_{timestamp}.csv"
        
        os.makedirs('results', exist_ok=True)
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['sic_code', 'course_name', 'title', 'description', 'url', 'total_words']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        logger.info(f"Resultados simulados guardados en: {filename}")
        
        return {
            "message": f"Scraping simulado iniciado. Se generaron {len(results)} resultados",
            "filename": filename,
            "results_count": len(results)
        }
    except Exception as e:
        logger.error(f"Error en scraping simulado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/detailed_status")
async def get_detailed_status():
    """Estado detallado del servidor"""
    return {
        "status": "active",
        "message": "Servidor WSL funcional corriendo",
        "mode": "functional",
        "database": "courses.db",
        "browser": "Chromium del sistema",
        "scraping": "simulated"
    }

if __name__ == "__main__":
    logger.info("Iniciando servidor WSL funcional...")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
