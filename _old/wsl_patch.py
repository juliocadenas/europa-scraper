
# Patch WSL para browser_manager
import os
import sys

# Detectar WSL
def is_wsl():
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower()
    except:
        return False

if is_wsl():
    print("🔧 Aplicando configuración WSL para browser_manager...")
    
    # Forzar headless en WSL
    os.environ['PLAYWRIGHT_HEADLESS'] = 'true'
    
    # Configurar display virtual
    if not os.environ.get('DISPLAY'):
        os.environ['DISPLAY'] = ':99'
    
    # Parchear BrowserManager para WSL
    original_init = None
    
    def wsl_browser_init(self, *args, **kwargs):
        # Forzar configuración WSL
        if 'headless' not in kwargs or kwargs['headless'] is None:
            kwargs['headless'] = True
        
        # Llamar al original
        return original_init(self, *args, **kwargs)
    
    # Aplicar patch si el módulo está cargado
    try:
        from utils.scraper import browser_manager
        if hasattr(browser_manager, 'BrowserManager'):
            original_init = browser_manager.BrowserManager.__init__
            browser_manager.BrowserManager.__init__ = wsl_browser_init
            print("✅ Patch WSL aplicado a BrowserManager")
    except ImportError:
        print("⚠️ Módulo browser_manager no encontrado para aplicar patch")
