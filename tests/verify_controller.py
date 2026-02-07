
import asyncio
import sys
import os
from unittest.mock import MagicMock

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

print(f"DEBUG: Project Root: {project_root}")

try:
    from utils.scraper.cordis_api_client import CordisApiClient
    print("[OK] Successfully imported CordisApiClient")
except ImportError as e:
    try:
        print(f"[FAIL] Failed to import CordisApiClient: {str(e)}")
    except UnicodeEncodeError:
        print(f"[FAIL] Failed to import CordisApiClient: {str(e).encode('ascii', 'ignore')}")
    sys.exit(1)

from controllers.scraper_controller import ScraperController

async def test_cordis_api_client():
    print("Testing CordisApiClient...")
    client = CordisApiClient()
    
    # Verify search_mode parameter exists
    import inspect
    sig = inspect.signature(client.search_projects_and_publications)
    if 'search_mode' in sig.parameters:
        print("[OK] search_projects_and_publications has search_mode param")
    else:
        print("[FAIL] search_projects_and_publications missing search_mode param")
    
    # Check if _execute_sparql_search or similar internal methods exist and use search_mode
    if hasattr(client, '_execute_sparql_search'):
        sig_sparql = inspect.signature(client._execute_sparql_search)
        if 'search_mode' in sig_sparql.parameters:
             print("[OK] _execute_sparql_search has search_mode param")
        else:
             print("[WARN] _execute_sparql_search MISSING search_mode param")
    else:
        print("[WARN] _execute_sparql_search method not found")

    print("[OK] CordisApiClient test completed.")

async def test_scraper_controller():
    print("Testing ScraperController...")
    
    import inspect
    
    if hasattr(ScraperController, '_process_cordis_api_phase'):
        sig = inspect.signature(ScraperController._process_cordis_api_phase)
        if 'search_mode' in sig.parameters:
            print("[OK] ScraperController._process_cordis_api_phase has search_mode param")
        else:
            print("[FAIL] ScraperController._process_cordis_api_phase MISSING search_mode param")
    else:
        print("[FAIL] ScraperController._process_cordis_api_phase method NOT FOUND")
    
    if hasattr(ScraperController, '_process_single_result'):
        sig_process = inspect.signature(ScraperController._process_single_result)
        if 'require_keywords' in sig_process.parameters:
            print("[OK] ScraperController._process_single_result has require_keywords param")
        else:
            print("[FAIL] ScraperController._process_single_result MISSING require_keywords param")
    else:
        print("[FAIL] ScraperController._process_single_result method NOT FOUND")


if __name__ == "__main__":
    asyncio.run(test_cordis_api_client())
    asyncio.run(test_scraper_controller())
    print("[DONE] Verification finished!")
