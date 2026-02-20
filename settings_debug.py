#!/usr/bin/env python3
"""
Debug script to check if the minimum words setting is being applied correctly.
This helps verify that the configuration is being passed through the entire pipeline.
"""

import json
import os

def check_current_settings():
    """Check the current minimum words settings in the configuration."""

    # Check if config.json exists
    config_path = os.path.join(os.path.dirname(__file__), 'client', 'config.json')

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Look for minimum words setting
            if 'scraping' in config:
                scraping_config = config['scraping']
                if 'minimum_words_per_page' in scraping_config:
                    min_words = scraping_config['minimum_words_per_page']
                    print(f"✅ Configuración encontrada:")
                    print(f"   - Archivo: {config_path}")
                    print(f"   - Palabras mínimas por página: {min_words}")
                    return min_words
                else:
                    print(f"❌ No se encontró 'minimum_words_per_page' en scraping config")
            else:
                print(f"❌ No se encontró sección 'scraping' en config")
        except Exception as e:
            print(f"❌ Error leyendo configuración: {e}")
    else:
        print(f"❌ Archivo de configuración no encontrado: {config_path}")

    return None

def show_params_examples():
    """Show examples of how parameters are passed to the scraper."""

    print("\n" + "="*60)
    print("EJEMPLOS DE PARÁMETROS PASADOS AL SCRAPER:")
    print("="*60)

    examples = [
        {
            "name": "Cotton search with min_words=3",
            "params": {
                "from_sic": "013199.0",
                "to_sic": "013199.0",
                "from_course": "Cotton",
                "to_course": "Cotton",
                "min_words": 3,
                "search_engine": "Google",
                "site_domain": "usa.gov"
            },
            "expected": "URLs con menos de 3 palabras deben ir a omitted"
        },
        {
            "name": "Cotton search with min_words=30",
            "params": {
                "from_sic": "013199.0",
                "to_sic": "013199.0",
                "from_course": "Cotton",
                "to_course": "Cotton",
                "min_words": 30,
                "search_engine": "Google",
                "site_domain": "usa.gov"
            },
            "expected": "URLs con menos de 30 palabras deben ir a omitted"
        }
    ]

    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['name']}")
        print(f"   Parámetros: {json.dumps(example['params'], indent=4)}")
        print(f"   Resultado esperado: {example['expected']}")

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 VERIFICACIÓN DE CONFIGURACIÓN DE PALABRAS MÍNIMAS")
    print("=" * 60)

    min_words = check_current_settings()
    show_params_examples()

    if min_words:
        print("\n✅ CONFIGURACIÓN VERIFICADA:")
        print(f"   - Valor actual de palabras mínimas: {min_words}")
        print("   - debería aplicarse consistentemente en toda la pipeline")
    else:
        print("\n❌ REVISAR CONFIGURACIÓN:")
        print("   - Verificar que el archivo config.json tiene el valor correcto")
        print("   - Verificar que el valor se esté pasando correctamente al scraper")
        print("\n📝 EN EL CÓDIGO BUSCAR:")
        print("   - min_words parameter en las llamadas al scraper")
        print("   - total_words < min_words en las validaciones")
        print("   - Líneas con 'hardcoded' 3 o 30 en lugar de variable")