#!/usr/bin/env python3
"""
Test directo contra CORDIS para diagnosticar si la IP está baneada
o si hay un error en la construcción de la URL/headers.
Ejecutar desde el contenedor:
  docker exec europa-scraper-prod python test_cordis_direct.py
"""
import requests
import time
import json

SEARCH_URL = "https://cordis.europa.eu/search"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

headers = {
    "Accept": "application/json",
    "User-Agent": USER_AGENTS[0],
    "Accept-Language": "en-US,en;q=0.9",
}

test_queries = ["Art", "Science", "Chemistry"]

print("=" * 70)
print("TEST DIRECTO CORDIS - DIAGNÓSTICO DE CONECTIVIDAD")
print("=" * 70)

for query in test_queries:
    url = f"{SEARCH_URL}?q={query}&format=json&p=1&num=10&archived=true"
    print(f"\n--- Probando: '{query}' ---")
    print(f"URL: {url}")
    
    try:
        start = time.time()
        resp = requests.get(url, headers=headers, timeout=20)
        elapsed = time.time() - start
        
        print(f"HTTP Status: {resp.status_code}")
        print(f"Tiempo: {elapsed:.2f}s")
        print(f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
        print(f"Tamaño respuesta: {len(resp.text)} bytes")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                top_keys = list(data.keys())
                print(f"JSON keys: {top_keys}")
                
                # Buscar totalHits
                result = data.get("result", {})
                header = result.get("header", {}) if isinstance(result, dict) else {}
                total_hits = header.get("totalHits", "NO ENCONTRADO")
                print(f"totalHits: {total_hits}")
                
                # Contar hits reales
                hits = data.get("hits", {})
                if isinstance(hits, dict):
                    hit_list = hits.get("hit", [])
                    if not isinstance(hit_list, list):
                        hit_list = [hit_list] if hit_list else []
                    print(f"Hits en esta página: {len(hit_list)}")
                    if hit_list:
                        first = hit_list[0]
                        print(f"Primer hit keys: {list(first.keys()) if isinstance(first, dict) else type(first)}")
                elif isinstance(hits, list):
                    print(f"Hits (lista directa): {len(hits)}")
                else:
                    print(f"Hits tipo: {type(hits)}")
                    
            except json.JSONDecodeError as e:
                print(f"ERROR JSON: {e}")
                print(f"Primeros 500 chars: {resp.text[:500]}")
        else:
            print(f"Primeros 500 chars de respuesta: {resp.text[:500]}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"ERROR DE CONEXIÓN: {e}")
    except requests.exceptions.Timeout:
        print(f"TIMEOUT (>20s)")
    except Exception as e:
        print(f"ERROR INESPERADO: {type(e).__name__}: {e}")
    
    time.sleep(3)  # Pausa entre tests

print("\n" + "=" * 70)
print("TEST COMPLETADO")
print("=" * 70)
