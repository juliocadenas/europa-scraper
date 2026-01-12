
import asyncio
import logging
import os
import sys

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Añadir raíz del proyecto
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

async def test_browser():
    try:
        from playwright.async_api import async_playwright
        
        logger.info("Iniciando Playwright...")
        playwright = await async_playwright().start()
        
        # Argumentos para WSL
        args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--headless'
        ]
        
        logger.info("Lanzando Chromium con argumentos WSL...")
        browser = await playwright.chromium.launch(headless=True, args=args)
        
        logger.info("Creando contexto...")
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            viewport={'width': 1366, 'height': 768}
        )
        
        logger.info("Creando página...")
        page = await context.new_page()
        
        logger.info("Navegando a example.com...")
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
        
        title = await page.title()
        logger.info(f"Título obtenido: {title}")
        
        logger.info("Cerrando navegador...")
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()
        
        logger.info("✅ Prueba de navegador exitosa")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en prueba de navegador: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_browser())
    sys.exit(0 if result else 1)
