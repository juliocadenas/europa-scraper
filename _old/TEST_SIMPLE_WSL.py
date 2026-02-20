#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
import traceback as traceback_module

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Añadir raíz del proyecto
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

async def test_simple_wsl():
    """Prueba simple del navegador WSL"""
    try:
        logger.info("🔄 Iniciando prueba simple WSL...")
        
        # Importar el browser manager simple
        from utils.scraper.simple_wsl_browser_manager import SimpleWSLBrowserManager
        
        # Mock server state
        class MockServerState:
            def __init__(self):
                self.captcha_solution_queue = asyncio.Queue()
            
            def set_pending_captcha_challenge(self, challenge):
                logger.info(f"CAPTCHA detectado: {challenge}")
        
        # Mock config
        class MockConfig:
            def get(self, key, default=None):
                return default
        
        # Crear browser manager
        server_state = MockServerState()
        config = MockConfig()
        browser_manager = SimpleWSLBrowserManager(config, server_state)
        
        # Inicializar
        logger.info("📦 Inicializando navegador simple...")
        await browser_manager.initialize(headless=True)
        
        # Verificar disponibilidad
        available = await browser_manager.check_playwright_browser()
        logger.info(f"✅ Navegador disponible: {available}")
        
        if available:
            # Probar crear página
            logger.info("🌐 Creando página de prueba...")
            page = await browser_manager.new_page()
            
            # Navegar a una página simple
            logger.info("🔍 Navegando a example.com...")
            await page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
            
            title = await page.title()
            logger.info(f"📄 Título obtenido: {title}")
            
            # Liberar página
            await browser_manager.release_page(page)
            
            logger.info("🎉 ¡PRUEBA SIMPLE EXITOSA!")
            return True
        else:
            logger.error("❌ Navegador no disponible")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en prueba simple WSL: {e}")
        logger.error(f"Traceback: {traceback_module.format_exc()}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_simple_wsl())
    sys.exit(0 if result else 1)
