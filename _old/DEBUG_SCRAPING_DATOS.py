#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SCRIPT DE DIAGNÓSTICO COMPLETO DEL PROBLEMA DE EXTRACCIÓN DE DATOS
=================================================================

Este script va a diagnosticar POR QUÉ los archivos CSV no tienen datos reales
y va a identificar exactamente dónde está el problema en el flujo de scraping.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'diagnostico_scraping_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Añadir directorio raíz al path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def diagnosticar_buscador_duckduckgo():
    """Diagnosticar específicamente el buscador DuckDuckGo"""
    logger.info("🔍 DIAGNÓSTICO ESPECÍFICO: DuckDuckGo")
    
    try:
        from utils.scraper.browser_manager import BrowserManager
        from utils.scraper.text_processor import TextProcessor
        from utils.scraper.search_engine import SearchEngine
        
        # Inicializar componentes
        browser_manager = BrowserManager()
        text_processor = TextProcessor()
        search_engine = SearchEngine(browser_manager, text_processor)
        
        # Verificar navegador
        logger.info("🌐 Verificando navegador Playwright...")
        browser_ok = await browser_manager.check_playwright_browser()
        logger.info(f"   Estado del navegador: {'✅ OK' if browser_ok else '❌ ERROR'}")
        
        if not browser_ok:
            logger.error("❌ Navegador no disponible - ESTE ES EL PROBLEMA")
            return False
        
        # Probar búsqueda simple
        logger.info("🔍 Probando búsqueda simple en DuckDuckGo...")
        test_query = "agricultural production crops"
        
        try:
            results = await search_engine.search_duckduckgo(test_query)
            logger.info(f"   Resultados obtenidos: {len(results)}")
            
            if results:
                logger.info("✅ Búsqueda DuckDuckGo funcionando:")
                for i, result in enumerate(results[:3]):
                    logger.info(f"   Resultado {i+1}: {result.get('title', 'No title')}")
                    logger.info(f"   URL: {result.get('url', 'No URL')}")
                    logger.info(f"   Descripción: {result.get('description', 'No desc')[:100]}...")
                return True
            else:
                logger.error("❌ Búsqueda DuckDuckGo no devolvió resultados")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en búsqueda DuckDuckGo: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    except Exception as e:
        logger.error(f"❌ Error general en diagnóstico DuckDuckGo: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def diagnosticar_extraccion_contenido():
    """Diagnosticar la extracción de contenido de URLs"""
    logger.info("📄 DIAGNÓSTICO DE EXTRACCIÓN DE CONTENIDO")
    
    try:
        from utils.scraper.content_extractor import ContentExtractor
        from utils.scraper.browser_manager import BrowserManager
        
        browser_manager = BrowserManager()
        content_extractor = ContentExtractor(browser_manager)
        
        # URL de prueba
        test_url = "https://example.com"
        logger.info(f"🔍 Probando extracción de contenido de: {test_url}")
        
        try:
            content = await content_extractor.extract_content(test_url)
            logger.info(f"   Título extraído: {content.get('title', 'No title')}")
            logger.info(f"   Longitud del texto: {len(content.get('text', ''))}")
            logger.info(f"   Palabras totales: {content.get('word_count', 0)}")
            
            if content.get('text'):
                logger.info("✅ Extracción de contenido funcionando")
                return True
            else:
                logger.error("❌ No se pudo extraer texto del contenido")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en extracción de contenido: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    except Exception as e:
        logger.error(f"❌ Error general en diagnóstico de extracción: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def diagnosticar_workflow_completo():
    """Diagnosticar el workflow completo de scraping"""
    logger.info("🔄 DIAGNÓSTICO DEL WORKFLOW COMPLETO")
    
    try:
        from utils.scraper.controller import ScraperController
        
        # Crear controller de prueba
        controller = ScraperController()
        
        # Datos de prueba
        test_data = {
            'sic_code': '01.0',
            'course_name': 'AGRICULTURAL PRODUCTION CROPS',
            'search_engine': 'DuckDuckGo',
            'max_results': 5
        }
        
        logger.info(f"🔍 Probando workflow completo con: {test_data}")
        
        try:
            results = await controller.scrape_course(test_data)
            logger.info(f"   Resultados del workflow: {len(results)}")
            
            if results:
                logger.info("✅ Workflow completo funcionando:")
                for i, result in enumerate(results[:3]):
                    logger.info(f"   Resultado {i+1}:")
                    for key, value in result.items():
                        logger.info(f"     {key}: {str(value)[:100]}...")
                return True
            else:
                logger.error("❌ Workflow completo no devolvió resultados")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en workflow completo: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    except Exception as e:
        logger.error(f"❌ Error general en diagnóstico workflow: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def diagnosticar_archivos_resultados():
    """Diagnosticar archivos de resultados existentes"""
    logger.info("📁 DIAGNÓSTICO DE ARCHIVOS DE RESULTADOS")
    
    import glob
    import csv
    
    # Buscar archivos CSV recientes
    csv_files = glob.glob("results/*.csv")
    logger.info(f"   Archivos CSV encontrados: {len(csv_files)}")
    
    for csv_file in csv_files[-5:]:  # Últimos 5 archivos
        logger.info(f"   Analizando: {csv_file}")
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                logger.info(f"     Filas totales: {len(rows)}")
                
                if rows:
                    sample_row = rows[0]
                    logger.info("     Columnas:")
                    for col in sample_row.keys():
                        value = sample_row.get(col, '')
                        logger.info(f"       {col}: {str(value)[:50]}...")
                        
                    # Verificar si los datos son de prueba
                    if 'example.com' in str(sample_row.get('url', '')):
                        logger.warning("     ⚠️  DATOS DE PRUEBA DETECTADOS")
                    elif len(sample_row.get('description', '')) < 50:
                        logger.warning("     ⚠️  DESCRIPCIÓN MUY CORTA - POSIBLE ERROR")
                    else:
                        logger.info("     ✅ DATOS PARECEN REALES")
                else:
                    logger.warning("     ⚠️  ARCHIVO SIN DATOS")
                    
        except Exception as e:
            logger.error(f"     ❌ Error leyendo archivo: {str(e)}")

async def main():
    """Función principal de diagnóstico"""
    logger.info("🚀 INICIANDO DIAGNÓSTICO COMPLETO DEL PROBLEMA DE SCRAPING")
    logger.info("="*80)
    
    # Diagnóstico 1: Buscador DuckDuckGo
    duckduckgo_ok = await diagnosticar_buscador_duckduckgo()
    logger.info("="*80)
    
    # Diagnóstico 2: Extracción de contenido
    contenido_ok = await diagnosticar_extraccion_contenido()
    logger.info("="*80)
    
    # Diagnóstico 3: Workflow completo
    workflow_ok = await diagnosticar_workflow_completo()
    logger.info("="*80)
    
    # Diagnóstico 4: Archivos de resultados
    diagnosticar_archivos_resultados()
    logger.info("="*80)
    
    # Resumen del diagnóstico
    logger.info("📋 RESUMEN DEL DIAGNÓSTICO:")
    logger.info(f"   DuckDuckGo: {'✅ OK' if duckduckgo_ok else '❌ ERROR'}")
    logger.info(f"   Extracción contenido: {'✅ OK' if contenido_ok else '❌ ERROR'}")
    logger.info(f"   Workflow completo: {'✅ OK' if workflow_ok else '❌ ERROR'}")
    
    if not duckduckgo_ok:
        logger.error("🔥 PROBLEMA IDENTIFICADO: El buscador DuckDuckGo no está funcionando")
        logger.error("   Solución: Revisar configuración del navegador y conexión")
    elif not contenido_ok:
        logger.error("🔥 PROBLEMA IDENTIFICADO: La extracción de contenido no está funcionando")
        logger.error("   Solución: Revisar ContentExtractor y procesamiento de HTML")
    elif not workflow_ok:
        logger.error("🔥 PROBLEMA IDENTIFICADO: El workflow completo no está funcionando")
        logger.error("   Solución: Revisar ScraperController y flujo de procesamiento")
    else:
        logger.info("✅ TODOS LOS COMPONENTES ESTÁN FUNCIONANDO")
        logger.info("   El problema podría estar en la configuración o en los datos de entrada")

if __name__ == "__main__":
    asyncio.run(main())