import asyncio
import os
import pandas as pd
from utils.scraper.cordis_api_client import CordisApiClient
from utils.scraper.result_manager import ResultManager
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_flow():
    # 1. Test Data retrieval
    client = CordisApiClient()
    
    # Test valid term
    print("--- Searching 'Iron Ores' ---")
    results_iron = await client.search_projects_and_publications("Iron Ores")
    print(f"Found {len(results_iron)} results for Iron Ores")
    
    # Test user's specific term "CULTIVOS DE"
    print("--- Searching 'CULTIVOS DE' ---")
    results_user = await client.search_projects_and_publications("CULTIVOS DE")
    print(f"Found {len(results_user)} results for 'CULTIVOS DE'")

    # 2. Test ResultManager Cleanup
    print("\n--- Testing Cleanup Logic ---")
    rm = ResultManager()
    
    # manually create a dummy empty file (simulating the 1KB file)
    output_file, _ = rm.initialize_output_files("9999", "9999", "TestEmpty", "TestEmpty", "Cordis Europa API")
    print(f"Created file: {output_file}")
    
    # Check it exists
    if os.path.exists(output_file):
        print(f"File exists. Size: {os.path.getsize(output_file)} bytes")
        
    # Run cleanup
    print("Running cleanup_if_empty()...")
    deleted = rm.cleanup_if_empty()
    
    if deleted:
        print("SUCCESS: File was deleted.")
    else:
        print("FAILURE: File was NOT deleted.")
        
    if not os.path.exists(output_file):
        print("Verified: File is gone from disk.")
    else:
        print("Verified: File still exists.")

if __name__ == "__main__":
    asyncio.run(test_flow())
