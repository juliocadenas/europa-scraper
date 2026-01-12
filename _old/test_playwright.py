#!/usr/bin/env python3
"""
Script para probar si Playwright está funcionando correctamente
"""

import asyncio
import logging
from playwright.async_api import async_playwright

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_playwright():
    """Prueba básica de Playwright"""
    try:
        logger.info("Iniciando prueba de Playwright...")
        
        async with async_playwright() as p:
            # Probar con diferentes navegadores
            browsers = ['chromium', 'firefox', 'webkit']
            
            for browser_name in browsers:
                try:
                    logger.info(f"Probando navegador: {browser_name}")
                    
                    if browser_name == 'chromium':
                        browser = await p.chromium.launch(headless=True)
                    elif browser_name == 'firefox':
                        browser = await p.firefox.launch(headless=True)
                    elif browser_name == 'webkit':
                        browser = await p.webkit.launch(headless=True)
                    
                    # Crear página y navegar
                    page = await browser.new_page()
                    await page.goto('https://www.example.com')
                    
                    # Obtener título
                    title = await page.title()
                    logger.info(f"✅ {browser_name}: Título de la página: {title}")
                    
                    # Cerrar navegador
                    await browser.close()
                    
                except Exception as e:
                    logger.error(f"❌ {browser_name}: Error - {str(e)}")
        
        logger.info("✅ Prueba de Playwright completada exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error general en prueba de Playwright: {str(e)}")
        return False

async def test_browser_manager():
    """Prueba del BrowserManager del proyecto"""
    try:
        logger.info("Probando BrowserManager del proyecto...")
        
        from utils.scraper.browser_manager import BrowserManager
        from utils.config import Config
        
        # Cargar configuración
        config = Config()
        config.load_config('client/config.json')
        
        # Crear BrowserManager
        browser_manager = BrowserManager(config)
        
        # Probar check_playwright_browser
        result = await browser_manager.check_playwright_browser()
        logger.info(f"Resultado de check_playwright_browser: {result}")
        
        if result:
            logger.info("✅ BrowserManager funcionando correctamente")
        else:
            logger.error("❌ BrowserManager no funciona correctamente")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error probando BrowserManager: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("PRUEBA DE PLAYWRIGHT")
    print("=" * 60)
    
    # Probar Playwright básico
    result1 = asyncio.run(test_playwright())
    
    print("\n" + "=" * 60)
    print("PRUEBA DE BROWSERMANAGER")
    print("=" * 60)
    
    # Probar BrowserManager del proyecto
    result2 = asyncio.run(test_browser_manager())
    
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Playwright básico: {'✅ OK' if result1 else '❌ ERROR'}")
    print(f"BrowserManager: {'✅ OK' if result2 else '❌ ERROR'}")
    
    if result1 and result2:
        print("\n🎉 Todo está funcionando correctamente!")
    else:
        print("\n⚠️ Hay problemas que necesitan ser resueltos")