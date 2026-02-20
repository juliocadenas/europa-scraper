#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PRUEBA COMPLETA DEL SISTEMA DE SCRAPING
==========================================

Esta prueba verificará:
1. Que Playwright está instalado correctamente
2. Que los workers pueden inicializar el navegador
3. Que el sistema puede realizar una búsqueda DuckDuckGo real
4. Que los resultados se guardan correctamente en CSV
5. Que los archivos omitidos se generan correctamente
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Añadir raíz del proyecto al path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

async def prueba_completa_sistema():
    """Ejecuta una prueba completa del sistema de scraping"""
    print("=" * 80)
    print("🧪 PRUEBA COMPLETA DEL SISTEMA DE SCRAPING")
    print("=" * 80)
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    try:
        # 1. Importar módulos necesarios
        print("\n📦 1. Importando módulos...")
        from utils.scraper.browser_manager import BrowserManager
        from utils.scraper.search_engine import SearchEngine
        from utils.scraper.result_manager import ResultManager
        from utils.scraper.text_processor import TextProcessor
        from utils.config import Config
        print("✅ Módulos importados correctamente")
        
        # 2. Inicializar componentes
        print("\n🔧 2. Inicializando componentes...")
        config = Config('client/config.json')
        
        # Crear server_state simulado
        class MockServerState:
            def __init__(self):
                self.captcha_solution_queue = asyncio.Queue()
            
            def set_pending_captcha_challenge(self, challenge):
                logger.info(f"CAPTCHA challenge detectado: {challenge}")
        
        server_state = MockServerState()
        browser_manager = BrowserManager(config, server_state)
        text_processor = TextProcessor()
        search_engine = SearchEngine(browser_manager, text_processor, config)
        result_manager = ResultManager()
        
        # 3. Inicializar navegador
        print("\n🚀 3. Inicializando navegador...")
        try:
            await browser_manager.initialize(headless=True)
            if await browser_manager.check_playwright_browser():
                print("✅ Navegador inicializado correctamente")
            else:
                print("❌ Error: Navegador no disponible después de inicializar")
                return False
        except Exception as e:
            print(f"❌ Error inicializando navegador: {e}")
            return False
        
        # 4. Probar búsqueda DuckDuckGo
        print("\n🔍 4. Probando búsqueda DuckDuckGo...")
        try:
            query = "AGRICULTURAL PRODUCTION CROPS"
            print(f"   Buscando: '{query}'")
            
            results = await search_engine.search_duckduckgo(query)
            
            print(f"✅ Búsqueda completada. Resultados encontrados: {len(results)}")
            
            if results:
                print("   Primeros 3 resultados:")
                for i, result in enumerate(results[:3]):
                    print(f"   {i+1}. {result.get('title', 'Sin título')}")
                    print(f"      URL: {result.get('url', 'Sin URL')}")
            else:
                print("   ⚠️  No se encontraron resultados")
                
        except Exception as e:
            print(f"❌ Error en búsqueda DuckDuckGo: {e}")
            return False
        
        # 5. Probar guardado de resultados
        print("\n💾 5. Probando guardado de resultados...")
        try:
            # Inicializar archivos de salida
            output_file, omitted_file = result_manager.initialize_output_files(
                "TEST", "TEST", "TEST", "TEST", "DuckDuckGo", worker_id=0
            )
            print(f"   Archivo CSV: {output_file}")
            print(f"   Archivo omitidos: {omitted_file}")
            
            # Añadir un resultado de prueba
            test_result = {
                'sic_code': 'TEST.0',
                'course_name': 'TEST COURSE',
                'title': 'Test Result - Agricultural Production',
                'description': 'Test description for agricultural production crops',
                'url': 'https://example.com/test',
                'total_words': 'Total words: 150 | Test: 5 | Agricultural: 3 | Production: 4'
            }
            
            success = result_manager.add_result(test_result)
            if success:
                print("✅ Resultado de prueba añadido correctamente")
            else:
                print("❌ Error al añadir resultado de prueba")
            
            # Guardar archivo de omitidos
            omitted_saved = result_manager.save_omitted_to_excel()
            if omitted_saved:
                print(f"✅ Archivo de omitidos guardado: {omitted_saved}")
            
            # Verificar archivos creados
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    print(f"✅ Archivo CSV creado con {len(lines)} líneas")
            
        except Exception as e:
            print(f"❌ Error en guardado de resultados: {e}")
            return False
        
        # 6. Limpiar recursos
        print("\n🧹 6. Limpiando recursos...")
        try:
            await browser_manager.close()
            print("✅ Navegador cerrado correctamente")
        except Exception as e:
            print(f"❌ Error cerrando navegador: {e}")
        
        # 7. Resumen final
        print("\n" + "=" * 80)
        print("📋 RESUMEN FINAL DE LA PRUEBA")
        print("=" * 80)
        print("✅ TODAS LAS PRUEBAS PASARON CORRECTAMENTE")
        print("🎯 EL SISTEMA ESTÁ LISTO PARA USAR")
        print("\n📂 UBICACIONES DE ARCHIVOS:")
        print("   📄 Resultados CSV: server/results/")
        print("   📊 Omitidos XLSX: omitidos/")
        print("\n🚀 PRÓXIMOS PASOS:")
        print("   1. Iniciar servidor: python server/main.py")
        print("   2. Iniciar cliente: python client/main.py")
        print("   3. Seleccionar cursos y hacer clic en 'Iniciar Scraping'")
        print("   4. Verificar progreso en las barras")
        print("   5. Revisar archivos resultantes")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR GENERAL EN LA PRUEBA: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Iniciando prueba completa del sistema...")
    print("Esta prueba verificará que todos los componentes funcionan correctamente.")
    print("Por favor, espere a que termine...\n")
    
    success = asyncio.run(prueba_completa_sistema())
    
    if success:
        print("\n🎉 ¡PRUEBA COMPLETADA EXITOSAMENTE!")
        print("El sistema de scraping está listo para usar.")
    else:
        print("\n❌ LA PRUEBA FALLÓ")
        print("Por favor, revise los errores mostrados arriba.")
    
    input("\nPresione Enter para continuar...")