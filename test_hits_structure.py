import requests
import json

url = "https://cordis.europa.eu/search?q=AGRICULTURAL+PRODUCTION+CROP&format=json&p=1&num=10"

response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
data = response.json()

print("=== ROOT LEVEL ===")
print(f"Root keys: {list(data.keys())}\n")

# Check data['hits']
if 'hits' in data:
    hits_obj = data['hits']
    print(f"data['hits'] type: {type(hits_obj)}")
    
    if isinstance(hits_obj, dict):
        print(f"data['hits'] keys: {list(hits_obj.keys())}")
        
        if 'hit' in hits_obj:
            hit_array = hits_obj['hit']
            print(f"\ndata['hits']['hit'] type: {type(hit_array)}")
            
            if isinstance(hit_array, list):
                print(f"data['hits']['hit'] length: {len(hit_array)}")
                
                if hit_array:
                    print(f"\nFirst element keys: {list(hit_array[0].keys())}")
                    print(f"\nFirst element:\n{json.dumps(hit_array[0], indent=2)[:1500]}")
            else:
                print("hit is not a list!")
        else:
            print("\nNO 'hit' key inside data['hits']!")
    elif isinstance(hits_obj, list):
        print(f"data['hits'] is a list with {len(hits_obj)} items")
        if hits_obj:
            print(f"First item: {json.dumps(hits_obj[0], indent=2)[:800]}")
