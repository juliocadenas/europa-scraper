#!/usr/bin/env python3
"""
TEST DIRECTO V27 - Prueba el endpoint JSON de Cordis SIN depender del controlador
"""
import requests
from urllib.parse import quote_plus

def test_cordis_json():
    print("=" * 60)
    print("TEST DIRECTO V27 - Endpoint JSON de Cordis")
    print("=" * 60)
    
    query = "AGRICULTURAL"  # Prueba simple
    encoded = quote_plus(query)
    
    url = f"https://cordis.europa.eu/search?q={encoded}&format=json&p=1&num=10"
    print(f"\nURL: {url}")
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    try:
        print("\nFetching...")
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"ERROR: {response.text[:500]}")
            return
        
        data = response.json()
        
        # Navigate the structure
        result = data.get('result', {})
        header = result.get('header', {})
        total = header.get('totalHits', '0')
        
        print(f"\n*** TOTAL HITS: {total} ***")
        
        hits_container = result.get('hits', {})
        hits = hits_container.get('hit', [])
        
        if isinstance(hits, dict):
            hits = [hits]
        
        print(f"\nResults on this page: {len(hits)}")
        print("-" * 40)
        
        for i, hit in enumerate(hits[:5]):
            # Find content type
            for ctype in ['article', 'project', 'result', 'publication']:
                if ctype in hit:
                    content = hit[ctype]
                    print(f"\n[{i+1}] Type: {ctype}")
                    print(f"    ID: {content.get('id', 'N/A')}")
                    print(f"    Title: {content.get('title', 'No title')[:60]}...")
                    break
        
        print("\n" + "=" * 60)
        print("✅ V27 API WORKS! Total available:", total)
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cordis_json()
