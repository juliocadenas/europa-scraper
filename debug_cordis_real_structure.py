import requests
import json

url = "https://cordis.europa.eu/search?q=AGRICULTURAL+PRODUCTION+CROP&format=json&p=1&num=10"

response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
data = response.json()

print("=== ESTRUCTURA COMPLETA ===")
print(json.dumps(data, indent=2)[:3000])  # Primeros 3000 caracteres

print("\n=== NAVEGACIÓN ===")
print(f"Keys en raíz: {list(data.keys())}")

if 'result' in data:
    print(f"Keys en 'result': {list(data['result'].keys())}")
    
    if 'hits' in data['result']:
        hits_obj = data['result']['hits']
        print(f"\nTipo de 'hits': {type(hits_obj)}")
        print(f"Keys en 'hits': {list(hits_obj.keys()) if isinstance(hits_obj, dict) else 'No es dict'}")
        
        if 'hit' in hits_obj:
            hit_data = hits_obj['hit']
            print(f"\nTipo de 'hit': {type(hit_data)}")
            
            if isinstance(hit_data, list):
                print(f"Longitud de lista: {len(hit_data)}")
                if hit_data:
                    print(f"\nPrimer elemento:")
                    print(json.dumps(hit_data[0], indent=2)[:1000])
            elif isinstance(hit_data, dict):
                print("Es un diccionario único")
                print(json.dumps(hit_data, indent=2)[:1000])
