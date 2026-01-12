#!/usr/bin/env python3
"""
Script para probar y arreglar el BrowserManager del proyecto
"""

import asyncio
import logging
from playwright.async_api import async_playwright

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_browser_manager_complete():
    """Prueba completa del BrowserManager del proyecto"""
    try:
        logger.info("Probando BrowserManager completo del proyecto...")
        
        from utils.scraper.browser_manager import BrowserManager
        from utils.config import Config
        
        # Crear server state mock
        class MockServerState:
            def __init__(self):
                self.captcha_solution_queue = asyncio.Queue()
            
            def set_pending_captcha_challenge(self, challenge):
                logger.info(f"CAPTCHA challenge detectado: {challenge}")
        
        server_state = MockServerState()
        
        # Cargar configuración
        config = Config()
        config_file = 'client/config.json'
        try:
            config.load_config(config_file)
            logger.info(f"Configuración cargada desde: {config_file}")
        except Exception as e:
            logger.warning(f"No se pudo cargar config desde {config_file}: {e}")
            logger.info("Usando configuración por defecto")
        
        # Crear BrowserManager
        browser_manager = BrowserManager(config, server_state)
        logger.info("BrowserManager creado")
        
        # Inicializar el navegador
        logger.info("Inicializando navegador...")
        await browser_manager.initialize(headless=True)
        logger.info("Navegador inicializado")
        
        # Probar check_playwright_browser
        result = await browser_manager.check_playwright_browser()
        logger.info(f"Resultado de check_playwright_browser: {result}")
        
        if result:
            logger.info("✅ BrowserManager funcionando correctamente")
            
            # Probar crear una página
            logger.info("Creando página de prueba...")
            page = await browser_manager.new_page()
            
            # Navegar a una página
            logger.info("Navegando a example.com...")
            await page.goto('https://www.example.com')
            
            # Obtener título
            title = await page.title()
            logger.info(f"Título de la página: {title}")
            
            # Liberar página
            await browser_manager.release_page(page)
            logger.info("Página liberada")
            
        else:
            logger.error("❌ BrowserManager no funciona correctamente")
        
        # Cerrar navegador
        await browser_manager.close()
        logger.info("Navegador cerrado")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error probando BrowserManager: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("PRUEBA COMPLETA DE BROWSERMANAGER")
    print("=" * 60)
    
    result = asyncio.run(test_browser_manager_complete())
    
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"BrowserManager completo: {'✅ OK' if result else '❌ ERROR'}")
    
    if result:
        print("\n🎉 El BrowserManager funciona correctamente!")
        print("El problema debe estar en cómo se inicializa en los workers.")
    else:
        print("\n⚠️ Hay problemas fundamentales en el BrowserManager")