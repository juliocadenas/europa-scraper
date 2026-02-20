import requests
import pandas as pd
import os

# 1. Test "iron ore" query
query = """
PREFIX eurio: <http://data.europa.eu/s66#>

SELECT DISTINCT ?title WHERE {
  ?project a eurio:Project .
  ?project eurio:title ?title .
  FILTER(CONTAINS(LCASE(STR(?title)), "iron ore"))
}
LIMIT 5
"""

print("Testing Cordis API with 'iron ore'...")
try:
    response = requests.post(
        'https://cordis.europa.eu/datalab/sparql',
        data={'query': query},
        headers={'Accept': 'application/sparql-results+json'},
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        bindings = data.get('results', {}).get('bindings', [])
        print(f"Results for 'iron ore': {len(bindings)}")
        for b in bindings:
            print(f"- {b['title']['value']}")
    else:
        print(f"Error: {response.status_code}")
except Exception as e:
    print(f"Exception: {e}")

# 2. Inspect the non-empty CSV file
csv_path = "/opt/docuscraper/results/results_1.0_CULTIVOS_DE_to_1.0_CULTIVOS_DE_cordis_europa_api_worker_1_20260202_135730.csv"
print(f"\nChecking content of {csv_path}...")
if os.path.exists(csv_path):
    with open(csv_path, 'r') as f:
        print(f.read())
else:
    print("File not found (expected if running locally, skipping)")
