#!/usr/bin/env python3
import asyncio
import logging
import os
import sys

# Añadir raíz del proyecto
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.config import Config
from utils.scraper.wsl_browser_manager import WSLBrowserManager

class MockServerState:
    def __init__(self):
        self.captcha_solution_queue = asyncio.Queue()
    
    def set_pending_captcha_challenge(self, challenge):
        print(f"CAPTCHA detectado: {challenge}")

async def test_wsl_browser():
    """Prueba el navegador en modo WSL"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print("🔄 Iniciando prueba de navegador WSL...")
    
    try:
        # Configuración
        config = Config()
        server_state = MockServerState()
        
        # Crear browser manager
        browser_manager = WSLBrowserManager(config, server_state)
        
        # Inicializar
        print("📦 Inicializando navegador...")
        await browser_manager.initialize(headless=True)
        
        # Verificar disponibilidad
        available = await browser_manager.check_playwright_browser()
        print(f"✅ Navegador disponible: {available}")
        
        # Probar crear página
        print("🌐 Creando página de prueba...")
        page = await browser_manager.new_page()
        
        # Navegar a una página simple
        print("🔍 Navegando a example.com...")
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
        
        title = await page.title()
        print(f"📄 Título de la página: {title}")
        
        # Liberar página
        await browser_manager.release_page(page)
        
        # Cerrar navegador
        print("🔒 Cerrando navegador...")
        await browser_manager.close()
        
        print("✅ Prueba WSL completada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba WSL: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_wsl_browser())
    sys.exit(0 if result else 1)
