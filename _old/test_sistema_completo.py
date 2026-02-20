#!/usr/bin/env python3
"""
Prueba completa del sistema cliente-servidor con el método DuckDuckGo arreglado
"""

import asyncio
import json
import requests
import time
from datetime import datetime
import traceback

def test_servidor_disponible():
    """Verificar que el servidor está disponible"""
    try:
        response = requests.get("http://localhost:8001/ping", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor disponible y respondiendo")
            return True
        else:
            print(f"❌ Servidor respondió con código: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        return False

def test_envio_tarea_simple():
    """Enviar una tarea simple de scraping al servidor"""
    
    # Tarea de prueba simple
    tarea_prueba = {
        "sic_code": "013399.2",
        "from_sic": "013399.2",
        "to_sic": "013399.2",
        "search_engine": "duckduckgo",  # Probamos el método que arreglamos
        "max_results": 5,
        "course_name": "Sugar_beets",
        "headless": True
    }
    
    try:
        print(f"📤 Enviando tarea de scraping: {tarea_prueba['course_name']}")
        response = requests.post(
            "http://localhost:8001/start_scraping",
            json=tarea_prueba,
            timeout=10
        )
        
        if response.status_code == 200:
            resultado = response.json()
            print(f"✅ Tarea aceptada: {resultado}")
            return True
        else:
            print(f"❌ Error en tarea: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error enviando tarea: {e}")
        return False

def test_estado_servidor():
    """Verificar el estado detallado del servidor"""
    try:
        response = requests.get("http://localhost:8001/detailed_status", timeout=5)
        if response.status_code == 200:
            estado = response.json()
            print(f"📊 Estado del servidor:")
            print(f"   - Status: {estado.get('status', 'desconocido')}")
            print(f"   - Workers activos: {estado.get('worker_count', 0)}")
            print(f"   - Tareas en cola: {estado.get('queue_size', 0)}")
            print(f"   - Tareas completadas: {estado.get('completed_tasks', 0)}")
            return True
        else:
            print(f"❌ Error obteniendo estado: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error consultando estado: {e}")
        return False

async def test_busqueda_duckduckgo_directa():
    """Probar directamente el método search_duckduckgo"""
    
    print("🔍 Probando búsqueda DuckDuckGo directa...")
    
    try:
        # Importamos las clases necesarias
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from utils.scraper.browser_manager import BrowserManager
        from utils.scraper.search_engine import SearchEngine
        from utils.config import Config
        
        async def prueba_busqueda():
            try:
                # Crear un mock server state para el BrowserManager
                class MockServerState:
                    def __init__(self):
                        self.captcha_solution_queue = None
                    
                    def set_pending_captcha_challenge(self, challenge):
                        print(f"Mock CAPTCHA: {challenge}")
                
                # Inicializar config manager
                config_manager = Config()
                
                # Inicializar browser manager con los parámetros correctos
                server_state = MockServerState()
                browser_manager = BrowserManager(config_manager, server_state)
                await browser_manager.initialize(headless=True)
                
                # Crear motor de búsqueda
                search_engine = SearchEngine(browser_manager, None, config_manager)
                
                # Realizar búsqueda
                query = "Sugar_beets farming"
                results = await search_engine.search_duckduckgo(query)
                
                print(f"✅ Búsqueda DuckDuckGo completada: {len(results)} resultados")
                for i, result in enumerate(results[:3]):  # Mostrar primeros 3
                    print(f"   {i+1}. {result.get('title', 'Sin título')}")
                    print(f"      URL: {result.get('url', 'Sin URL')}")
                
                await browser_manager.cleanup()
                return len(results) > 0
                
            except Exception as e:
                print(f"❌ Error en búsqueda DuckDuckGo: {e}")
                traceback.print_exc()
                return False
        
        # Ejecutar prueba asíncrona
        return asyncio.run(prueba_busqueda())
        
    except Exception as e:
        print(f"❌ Error configurando prueba DuckDuckGo: {e}")
        traceback.print_exc()
        return False

def main():
    """Función principal de prueba"""
    print("🚀 INICIANDO PRUEBA COMPLETA DEL SISTEMA")
    print("=" * 50)
    
    pruebas = [
        ("Disponibilidad del servidor", test_servidor_disponible),
        ("Estado del servidor", test_estado_servidor),
        ("Búsqueda DuckDuckGo directa", test_busqueda_duckduckgo_directa),
        ("Envío de tarea simple", test_envio_tarea_simple),
    ]
    
    resultados = []
    
    for nombre_prueba, funcion_prueba in pruebas:
        print(f"\n🧪 {nombre_prueba}:")
        print("-" * 30)
        
        try:
            resultado = funcion_prueba()
            resultados.append((nombre_prueba, resultado))
            
            if resultado:
                print(f"✅ {nombre_prueba}: PASÓ")
            else:
                print(f"❌ {nombre_prueba}: FALLÓ")
                
        except Exception as e:
            print(f"💥 {nombre_prueba}: ERROR - {e}")
            resultados.append((nombre_prueba, False))
    
    # Resumen final
    print("\n" + "=" * 50)
    print("📋 RESUMEN DE PRUEBAS")
    print("=" * 50)
    
    aprobadas = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)
    
    for nombre_prueba, resultado in resultados:
        estado = "✅ PASÓ" if resultado else "❌ FALLÓ"
        print(f"{estado} {nombre_prueba}")
    
    print(f"\n🎯 RESULTADO: {aprobadas}/{total} pruebas aprobadas")
    
    if aprobadas == total:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON! El sistema está funcionando correctamente.")
        return True
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa los errores above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)