import requests

def test_cordis(term):
    query = f"""
    PREFIX eurio: <http://data.europa.eu/s66#>
    SELECT DISTINCT ?title WHERE {{
      {{
        ?project a eurio:Project .
        ?project eurio:title ?title .
        FILTER(CONTAINS(LCASE(STR(?title)), "{term.lower()}"))
      }}
      UNION
      {{
        ?pub a eurio:ProjectPublication .
        ?pub eurio:title ?title .
        FILTER(CONTAINS(LCASE(STR(?title)), "{term.lower()}"))
      }}
    }}
    LIMIT 2
    """
    try:
        r = requests.post('https://cordis.europa.eu/datalab/sparql', 
                         data={'query': query}, 
                         headers={'Accept': 'application/sparql-results+json'},
                         timeout=10)
        count = len(r.json().get('results', {}).get('bindings', []))
        print(f"Term '{term}': {count} results")
    except Exception as e:
        print(f"Term '{term}': Error {e}")

print("Testing Cordis keyword variants:")
test_cordis("mining metals")
test_cordis("metal mining")
test_cordis("mining")
test_cordis("metals")
