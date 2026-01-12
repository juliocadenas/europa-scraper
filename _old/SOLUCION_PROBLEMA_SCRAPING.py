#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SOLUCIÓN DEFINITIVA PARA LOS PROBLEMAS DE SCRAPING
===================================================

PROBLEMAS IDENTIFICADOS:
1. Los archivos CSV están vacíos (solo encabezados)
2. El scraping termina demasiado rápido (2 minutos en lugar de 1+ hora)
3. Error: 'NoneType' object has no attribute 'send'
4. Error: 'SearchEngine' object has no attribute 'search_duckduckgo'

ANÁLISIS:
- Los workers se inicializan correctamente
- El navegador se lanza pero el contexto se pierde
- Las búsquedas fallan inmediatamente
- No se genera ningún resultado real

SOLUCIONES A IMPLEMENTAR:
"""

import os
import sys
import logging
import asyncio

# Añadir raíz del proyecto al path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

async def test_duckduckgo_search():
    """Prueba directa del método DuckDuckGo"""
    print("🔍 Probando búsqueda DuckDuckGo directamente...")
    
    try:
        from utils.scraper.browser_manager import BrowserManager
        from utils.scraper.search_engine import SearchEngine
        from utils.scraper.text_processor import TextProcessor
        from utils.config import Config
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Inicializar componentes
        config = Config('client/config.json')
        
        # Crear server_state simulado
        class MockServerState:
            def __init__(self):
                self.captcha_solution_queue = asyncio.Queue()
            
            def set_pending_captcha_challenge(self, challenge):
                logger.info(f"CAPTCHA challenge detectado: {challenge}")
        
        server_state = MockServerState()
        browser_manager = BrowserManager(config, server_state)
        
        # Inicializar navegador
        print("🚀 Inicializando navegador...")
        await browser_manager.initialize(headless=True)
        
        # Verificar disponibilidad
        if await browser_manager.check_playwright_browser():
            print("✅ Navegador disponible")
        else:
            print("❌ Navegador no disponible")
            return False
        
        # Inicializar motor de búsqueda
        text_processor = TextProcessor()
        search_engine = SearchEngine(browser_manager, text_processor, config)
        
        # Probar búsqueda
        print("🔍 Realizando búsqueda de prueba...")
        query = "AGRICULTURAL PRODUCTION CROPS"
        results = await search_engine.search_duckduckgo(query)
        
        print(f"📊 Resultados encontrados: {len(results)}")
        for i, result in enumerate(results[:3]):  # Mostrar primeros 3
            print(f"  {i+1}. {result.get('title', 'Sin título')}")
            print(f"     URL: {result.get('url', 'Sin URL')}")
            print(f"     Descripción: {result.get('description', 'Sin descripción')[:100]}...")
        
        # Cerrar navegador
        await browser_manager.close()
        
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_result_manager():
    """Prueba del gestor de resultados"""
    print("📁 Probando gestor de resultados...")
    
    try:
        from utils.scraper.result_manager import ResultManager
        
        result_manager = ResultManager()
        
        # Crear archivo de prueba
        output_file, omitted_file = result_manager.initialize_output_files(
            "01.0", "011903.0", "AGRICULTURAL PRODUCTION", "Oil grains", "DuckDuckGo", worker_id=0
        )
        
        print(f"✅ Archivo CSV creado: {output_file}")
        print(f"✅ Archivo omitidos creado: {omitted_file}")
        
        # Añadir resultado de prueba
        test_result = {
            'sic_code': '01.0',
            'course_name': 'AGRICULTURAL PRODUCTION CROPS',
            'title': 'Test Result',
            'description': 'Test description for agricultural production',
            'url': 'https://example.com/test',
            'total_words': 'Total words: 150 | Test: 5 | Agricultural: 3 | Production: 4'
        }
        
        success = result_manager.add_result(test_result)
        if success:
            print("✅ Resultado de prueba añadido correctamente")
        else:
            print("❌ Error al añadir resultado de prueba")
        
        # Guardar omitidos
        omitted_saved = result_manager.save_omitted_to_excel()
        if omitted_saved:
            print(f"✅ Archivo de omitidos guardado: {omitted_saved}")
        
        # Verificar archivos
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"📄 Archivo CSV final: {len(lines)} líneas")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba de resultados: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_file_locations():
    """Verifica dónde se guardan los archivos"""
    print("📂 Verificando ubicaciones de archivos...")
    
    locations = [
        "results",
        "server/results", 
        "omitidos",
        "server/omitidos"
    ]
    
    for location in locations:
        if os.path.exists(location):
            files = os.listdir(location)
            print(f"📁 {location}/: {len(files)} archivos")
            for file in files[:3]:  # Mostrar primeros 3
                size = os.path.getsize(os.path.join(location, file))
                print(f"   📄 {file} ({size} bytes)")
        else:
            print(f"📁 {location}/: (no existe)")

async def main():
    """Función principal de diagnóstico"""
    print("=" * 60)
    print("🔧 DIAGNÓSTICO COMPLETO DEL SISTEMA DE SCRAPING")
    print("=" * 60)
    
    # 1. Verificar ubicaciones de archivos
    check_file_locations()
    print()
    
    # 2. Probar gestor de resultados
    result_test = await test_result_manager()
    print(f"📊 Prueba de resultados: {'✅ OK' if result_test else '❌ ERROR'}")
    print()
    
    # 3. Probar búsqueda DuckDuckGo
    search_test = await test_duckduckgo_search()
    print(f"🔍 Prueba de búsqueda: {'✅ OK' if search_test else '❌ ERROR'}")
    print()
    
    # 4. Resumen
    print("=" * 60)
    print("📋 RESUMEN DEL DIAGNÓSTICO")
    print("=" * 60)
    
    if result_test and search_test:
        print("✅ Todas las pruebas pasaron correctamente")
        print("💡 El sistema debería funcionar ahora")
    else:
        print("❌ Hay problemas que deben ser resueltos:")
        if not result_test:
            print("   - Problema con el gestor de resultados")
        if not search_test:
            print("   - Problema con la búsqueda DuckDuckGo")
    
    print("\n📂 UBICACIONES DE ARCHIVOS RESULTANTES:")
    print("   - Resultados CSV: server/results/")
    print("   - Omitidos XLSX: omitidos/")
    print("\n💡 RECOMENDACIONES:")
    print("   1. Verificar que los archivos se guarden en las ubicaciones correctas")
    print("   2. Revisar los logs de workers para ver errores específicos")
    print("   3. Asegurar que el navegador se inicialice correctamente")
    print("   4. Probar con tareas pequeñas antes de ejecutar tareas grandes")

if __name__ == "__main__":
    asyncio.run(main())