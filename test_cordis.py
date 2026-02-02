import requests
import json

# Test simple query
query = """
PREFIX eurio: <http://data.europa.eu/s66#>

SELECT DISTINCT ?title WHERE {
  ?project a eurio:Project .
  ?project eurio:title ?title .
  FILTER(CONTAINS(LCASE(STR(?title)), "metal"))
}
LIMIT 5
"""

print("Testing Cordis API...")
print(f"Query: {query}")

try:
    response = requests.post(
        'https://cordis.europa.eu/datalab/sparql',
        data={'query': query},
        headers={'Accept': 'application/sparql-results+json'},
        timeout=30
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        bindings = data.get('results', {}).get('bindings', [])
        print(f"Results found: {len(bindings)}")
        
        for i, item in enumerate(bindings, 1):
            title = item.get('title', {}).get('value', 'No title')
            print(f"{i}. {title}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Exception: {e}")
