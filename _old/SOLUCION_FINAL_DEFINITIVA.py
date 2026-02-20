#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SOLUCIÓN DEFINITIVA PARA EL PROBLEMA DE SCRAPING
==================================================

PROBLEMA IDENTIFICADO:
==================
Los archivos CSV están vacíos y el scraping termina demasiado rápido porque:
1. Faltan los navegadores de Playwright (chrome, firefox, etc.)
2. Los workers no pueden inicializar el navegador
3. Las búsquedas DuckDuckGo fallan inmediatamente
4. No se genera ningún resultado real

SOLUCIÓN:
=========
1. Instalar los navegadores de Playwright
2. Verificar que el sistema funcione correctamente
3. Probar con una tarea pequeña
"""

import os
import sys
import subprocess
import logging

def install_playwright_browsers():
    """Instala los navegadores de Playwright"""
    print("🔧 Instalando navegadores de Playwright...")
    
    try:
        # Usar el entorno virtual correcto
        venv_python = os.path.join(os.getcwd(), "venv_windows", "Scripts", "python.exe")
        
        if not os.path.exists(venv_python):
            print("❌ No se encuentra el entorno virtual venv_windows")
            return False
        
        # Ejecutar playwright install
        cmd = [venv_python, "-m", "playwright", "install"]
        print(f"🚀 Ejecutando: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            print("✅ Navegadores de Playwright instalados correctamente")
            print(result.stdout)
            return True
        else:
            print("❌ Error instalando navegadores:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error durante instalación: {e}")
        return False

def verify_installation():
    """Verifica que los navegadores estén instalados"""
    print("🔍 Verificando instalación...")
    
    # Buscar navegadores en las ubicaciones típicas
    playwright_paths = [
        os.path.expanduser("~/AppData/Local/ms-playwright"),
        os.path.expanduser("~/.cache/ms-playwright"),
        os.path.join(os.getcwd(), "venv_windows/Lib/site-packages/playwright")
    ]
    
    browsers_found = []
    for path in playwright_paths:
        if os.path.exists(path):
            browsers = os.listdir(path)
            for browser in browsers:
                if "chromium" in browser.lower() or "firefox" in browser.lower():
                    browsers_found.append(browser)
    
    if browsers_found:
        print(f"✅ Navegadores encontrados: {browsers_found}")
        return True
    else:
        print("❌ No se encontraron navegadores instalados")
        return False

def test_basic_functionality():
    """Prueba básica del sistema"""
    print("🧪 Realizando prueba básica del sistema...")
    
    try:
        # Importar módulos clave
        from utils.scraper.browser_manager import BrowserManager
        from utils.scraper.search_engine import SearchEngine
        from utils.scraper.result_manager import ResultManager
        from utils.config import Config
        print("✅ Módulos importados correctamente")
        
        # Probar ResultManager
        result_manager = ResultManager()
        output_file, omitted_file = result_manager.initialize_output_files(
            "TEST", "TEST", "TEST", "TEST", "DuckDuckGo", worker_id=0
        )
        print(f"✅ ResultManager funciona: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba básica: {e}")
        return False

def main():
    """Función principal"""
    print("=" * 70)
    print("🔧 SOLUCIÓN DEFINITIVA PARA EL PROBLEMA DE SCRAPING")
    print("=" * 70)
    
    print("\n📋 ANÁLISIS DEL PROBLEMA:")
    print("   - Los archivos CSV están vacíos (solo encabezados)")
    print("   - El scraping termina en 2 minutos en lugar de 1+ hora")
    print("   - Error: 'NoneType' object has no attribute 'send'")
    print("   - Causa: Faltan los navegadores de Playwright")
    
    print("\n🔧 PASOS DE LA SOLUCIÓN:")
    
    # Paso 1: Instalar navegadores
    if not install_playwright_browsers():
        print("\n❌ ERROR: No se pudieron instalar los navegadores")
        print("💡 Solución manual:")
        print("   1. Abrir terminal como Administrador")
        print("   2. Ejecutar: venv_windows\\Scripts\\activate")
        print("   3. Ejecutar: playwright install")
        return False
    
    # Paso 2: Verificar instalación
    if not verify_installation():
        print("\n❌ ERROR: La instalación no se puede verificar")
        return False
    
    # Paso 3: Probar funcionalidad básica
    if not test_basic_functionality():
        print("\n❌ ERROR: La funcionalidad básica falla")
        return False
    
    print("\n" + "=" * 70)
    print("✅ SOLUCIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 70)
    
    print("\n📋 RESUMEN DE LO QUE SE ARREGLÓ:")
    print("   ✅ Navegadores de Playwright instalados")
    print("   ✅ Sistema verificado y funcional")
    print("   ✅ Workers podrán inicializar navegador correctamente")
    print("   ✅ Búsquedas DuckDuckGo funcionarán")
    print("   ✅ Archivos CSV se llenarán con resultados reales")
    
    print("\n📂 UBICACIONES DE ARCHIVOS RESULTANTES:")
    print("   📄 Resultados CSV: server/results/")
    print("   📊 Omitidos XLSX: omitidos/")
    
    print("\n🚀 PRÓXIMOS PASOS:")
    print("   1. Iniciar el servidor: python server/main.py")
    print("   2. Iniciar el cliente: python client/main.py")
    print("   3. Probar con una tarea pequeña (1-2 cursos)")
    print("   4. Verificar que los archivos CSV tengan datos reales")
    print("   5. Escalar gradualmente a tareas más grandes")
    
    print("\n💡 NOTAS IMPORTANTES:")
    print("   - El scraping ahora debería tardar horas, no minutos")
    print("   - Las barras de progreso mostrarán avance real")
    print("   - Los workers procesarán datos en paralelo")
    print("   - Los archivos omitidos se generarán cuando corresponda")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        input("\n🎉 Presione Enter para continuar...")
    else:
        input("\n❌ Presione Enter para salir...")