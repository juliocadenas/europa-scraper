#!/usr/bin/env python3
"""
PRUEBA MANUAL CORDIS - Diagnóstico de bloqueos y rate limiting

Este script hace peticiones manuales a la API de CORDIS para determinar:
1. Si la IP está bloqueada (HTTP 403)
2. Si hay rate limiting (HTTP 429)
3. Si el problema es de timeouts
4. En qué página falla la paginación
"""

import requests
import time
import json
from datetime import datetime
from urllib.parse import quote_plus

# Configuración
QUERY = "artificial intelligence"
BASE_URL = "https://cordis.europa.eu/search"
RESULTS_PER_PAGE = 100
START_PAGE = 1
MAX_PAGES = 50  # Ajustar según necesidad
DELAY_BETWEEN_REQUESTS = 5  # segundos entre peticiones (empezar con 5)

# Headers para parecer un navegador real
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def print_header(text):
    print("\n" + "="*70)
    print(f" {text}")
    print("="*70)

def print_result(status, message):
    icon = "✅" if status == "success" else "⚠️" if status == "warning" else "❌"
    print(f"{icon} {message}")

def test_single_page(page_num):
    """Hace una petición a una página específica"""
    encoded_query = quote_plus(QUERY)
    url = f"{BASE_URL}?q={encoded_query}&format=json&p={page_num}&num={RESULTS_PER_PAGE}&archived=true"

    print(f"\n📡 Petición a página {page_num}: {url[:80]}...")

    start_time = time.time()

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        elapsed = time.time() - start_time

        print(f"   Estado: HTTP {response.status_code}")
        print(f"   Tiempo: {elapsed:.2f} segundos")
        print(f"   Tamaño: {len(response.content)} bytes")

        # Analizar respuesta según código de estado
        if response.status_code == 200:
            try:
                data = response.json()

                # Extraer totalHits si es la primera página
                if page_num == 1:
                    if "payload" in data:
                        data = data["payload"]
                    total_hits = data.get("result", {}).get("header", {}).get("totalHits", "0")
                    print(f"   📊 Total resultados disponibles: {total_hits}")

                # Contar hits en esta página
                if "payload" in data and "hits" not in data:
                    data = data["payload"]

                hits = data.get("hits")
                if isinstance(hits, dict):
                    hits = hits.get("hit", [])
                elif not isinstance(hits, list):
                    hits = []

                print(f"   📦 Hits en esta página: {len(hits)}")
                return "success", f"Página {page_num} OK - {len(hits)} hits"

            except json.JSONDecodeError as e:
                return "error", f"JSON inválido: {str(e)[:50]}"

        elif response.status_code == 429:
            return "warning", f"RATE LIMITING (429) - Too Many Requests"

        elif response.status_code == 403:
            return "error", f"BLOQUEO (403) - IP probablemente baneada"

        elif response.status_code == 404:
            return "warning", "Not Found - URL incorrecta"

        elif response.status_code >= 500:
            return "warning", f"Error servidor {response.status_code}"

        else:
            return "warning", f"Código inesperado: {response.status_code}"

    except requests.exceptions.Timeout:
        return "error", f"Timeout después de 30s"
    except requests.exceptions.ConnectionError as e:
        return "error", f"Error de conexión: {str(e)[:50]}"
    except Exception as e:
        return "error", f"Excepción: {type(e).__name__}: {str(e)[:50]}"

def main():
    print_header("PRUEBA MANUAL CORDIS - DIAGNÓSTICO")
    print(f"Query: {QUERY}")
    print(f"Delay entre peticiones: {DELAY_BETWEEN_REQUESTS} segundos")
    print(f"Páginas a probar: {START_PAGE} a {MAX_PAGES}")
    print(f"Hora inicio: {datetime.now().strftime('%H:%M:%S')}")

    # Prueba inicial rápida
    print_header("FASE 1: PRUEBA INICIAL")
    status, msg = test_single_page(1)

    if status == "error" and "BLOQUEO" in msg:
        print_result("error", "❌ TU IP ESTÁ BLOQUEADA (403)")
        print("   💡 Solución: Esperar 10-20 minutos o usar VPN/proxy diferente")
        return

    if status == "warning" and "RATE LIMITING" in msg:
        print_result("warning", "⚠️ RATE LIMITING detectado")
        print("   💡 Solución: Aumentar delay entre peticiones")
        return

    # Prueba de paginación progresiva
    print_header("FASE 2: PRUEBA DE PAGINACIÓN PROGRESIVA")

    results = {
        "success": 0,
        "warning": 0,
        "error": 0,
        "pages_tested": 0,
        "first_error_page": None,
        "errors_detail": []
    }

    for page in range(START_PAGE, MAX_PAGES + 1):
        print(f"\n--- Página {page}/{MAX_PAGES} ---")
        status, msg = test_single_page(page)

        results["pages_tested"] += 1

        if status == "success":
            results["success"] += 1
            print_result("success", msg)
        elif status == "warning":
            results["warning"] += 1
            print_result("warning", msg)
            results["errors_detail"].append({"page": page, "status": status, "msg": msg})
        else:
            results["error"] += 1
            print_result("error", msg)
            results["errors_detail"].append({"page": page, "status": status, "msg": msg})
            if results["first_error_page"] is None:
                results["first_error_page"] = page

        # Delay entre peticiones (excepto en la última)
        if page < MAX_PAGES:
            print(f"⏳ Esperando {DELAY_BETWEEN_REQUESTS}s antes de la siguiente petición...")
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Resumen final
    print_header("RESUMEN FINAL")
    print(f"📊 Páginas probadas: {results['pages_tested']}")
    print(f"✅ Exitosas: {results['success']}")
    print(f"⚠️ Advertencias: {results['warning']}")
    print(f"❌ Errores: {results['error']}")

    if results["first_error_page"]:
        print(f"\n🔍 Primer error en página: {results['first_error_page']}")
        print("\n📋 Detalle de errores:")
        for err in results["errors_detail"][:10]:  # Mostrar max 10 errores
            print(f"   Pág {err['page']}: {err['msg']}")
    else:
        print(f"\n🎉 Todas las páginas funcionaron correctamente!")

    print(f"\n⏰ Hora fin: {datetime.now().strftime('%H:%M:%S')}")

    # Recomendaciones
    print_header("RECOMENDACIONES")

    if results["error"] > 0:
        if any("BLOQUEO" in e["msg"] for e in results["errors_detail"]):
            print("✦ Tu IP está bloqueada (403). Soluciones:")
            print("  - Esperar 15-30 minutos antes de volver a intentar")
            print("  - Usar una VPN o proxy diferente")
            print("  - Reducir drásticamente el número de workers")

        elif any("RATE LIMITING" in e["msg"] for e in results["errors_detail"]):
            print("✦ Rate limiting detectado (429). Soluciones:")
            print("  - Aumentar delay entre peticiones (recomendado: 8-10s)")
            print("  - Reducir workers concurrentes a 3-5 máximo")

        elif any("Timeout" in e["msg"] for e in results["errors_detail"]):
            print("✦ Timeouts detectados. Soluciones:")
            print("  - Aumentar timeout de la petición")
            print("  - Verificar conexión a internet")
            print("  - Posible problema de conexión intermitente")

        if results["first_error_page"]:
            print(f"\n✦ El problema aparece consistentemente en la página {results['first_error_page']}")
            if results["first_error_page"] > 20:
                print("  - Parece ser un límite de paginación profunda")
                print("  - Considera dividir la búsqueda por años u otros filtros")
    else:
        print("✦ No se detectaron errores con la configuración actual")
        print("✦ El problema puede estar en la concurrencia del scraper")
        print("  - Proba reduce workers a 5-10 máximo")
        print("  - Asegúrate de que el delay entre páginas sea >= 3 segundos")

if __name__ == "__main__":
    main()
