
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.scraper.cordis_api_client import CordisApiClient

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_cordis():
    client = CordisApiClient()
    
    test_terms = [
        "Iron ore mining",     # Exact term check
        "Copper ore mining",
        "Mining of other non-ferrous metal ores",
        "101.0 - Iron ore mining", # Test if including SIC code breaks it
        "irrigation"
    ]
    
    print("\n" + "="*50)
    print("STARTING CORDIS API DEBUG")
    print("="*50 + "\n")
    
    for term in test_terms:
        print(f"Testing term: '{term}'")
        try:
            results = await client.search_projects_and_publications(term, max_results=5)
            if results:
                print(f"✅ SUCCESS: Found {len(results)} results for '{term}'")
                for i, res in enumerate(results[:2]):
                    print(f"   {i+1}. {res['title']} ({res['url']})")
            else:
                print(f"❌ FAILURE: No results found for '{term}'")
        except Exception as e:
            print(f"🔥 EXCEPTION: Error searching for '{term}': {e}")
        print("-" * 30)

if __name__ == "__main__":
    try:
        asyncio.run(test_cordis())
    except KeyboardInterrupt:
        pass
