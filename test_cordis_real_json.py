import requests
import json

url = "https://cordis.europa.eu/search?q=AGRICULTURAL+PRODUCTION+CROP&format=json&p=1&num=10"

print("Fetching:", url)
response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
print(f"Status: {response.status_code}\n")

data = response.json()

# Mostrar estructura completa con indentación
print("=== JSON COMPLETO (primeros 2000 caracteres) ===")
json_str = json.dumps(data, indent=2)
print(json_str[:2000])
print(f"\n... (total length: {len(json_str)} chars)\n")

# Navegación paso a paso
print("=== NAVEGACIÓN ===")
print(f"Root keys: {list(data.keys())}")

if 'result' in data:
    result = data['result']
    print(f"\nresult keys: {list(result.keys())}")
    
    # Check header
    if 'header' in result:
        header = result['header']
        print(f"\nheader keys: {list(header.keys())}")
        if 'totalHits' in header:
            print(f"  totalHits: {header['totalHits']}")
    
    # Check hits
    if 'hits' in result:
        hits_obj = result['hits']
        print(f"\nhits type: {type(hits_obj)}")
        print(f"hits keys: {list(hits_obj.keys()) if isinstance(hits_obj, dict) else 'N/A (not dict)'}")
        
        if isinstance(hits_obj, dict):
            if 'hit' in hits_obj:
                hit_data = hits_obj['hit']
                print(f"\nhit type: {type(hit_data)}")
                if isinstance(hit_data, list):
                    print(f"hit length: {len(hit_data)}")
                    if hit_data:
                        print(f"\nFirst hit keys: {list(hit_data[0].keys())}")
                        print(f"\nFirst hit sample:")
                        print(json.dumps(hit_data[0], indent=2)[:800])
                else:
                    print("hit is not a list!")
                    print(json.dumps(hit_data, indent=2)[:500])
            else:
                print("\nNO 'hit' key in hits object!")
                print(f"Available keys: {list(hits_obj.keys())}")
        elif isinstance(hits_obj, list):
            print(f"hits is a list with {len(hits_obj)} items")
    else:
        print("\nNO 'hits' key in result!")
