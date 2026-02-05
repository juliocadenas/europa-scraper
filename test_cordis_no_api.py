import asyncio
import logging
import sys
import os

# Add project root to sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.scraper.browser_manager import BrowserManager
from utils.scraper.search_engine import SearchEngine
from utils.scraper.text_processor import TextProcessor
from utils.config import Config

async def test_cordis_no_api():
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # Load config
    config_path = os.path.join(project_root, 'config.json')
    config = Config(config_path)

    # Mock server state for BrowserManager
    class MockServerState:
        def __init__(self):
            self.captcha_solution_queue = asyncio.Queue()
        def set_pending_captcha_challenge(self, *args, **kwargs):
            pass

    server_state = MockServerState()

    # Initialize components
    browser_manager = BrowserManager(config, server_state)
    text_processor = TextProcessor()
    search_engine = SearchEngine(browser_manager, text_processor, config)

    search_term = "metal ores"
    print(f"\n--- Testing Cordis Europa (No API) for term: '{search_term}' ---\n")

    # Initialize Browser
    await browser_manager.initialize(headless=True)

    try:
        # Check browser
        if not await browser_manager.check_playwright_browser():
            print("Error: Playwright browser not available.")
            return

        # Perform search
        results = await search_engine.search_cordis_europa(search_term, max_pages=1)
        
        print(f"\nResults found: {len(results)}")
        for i, res in enumerate(results[:5], 1):
            print(f"{i}. {res['title']}")
            print(f"   URL: {res['url']}")
            print(f"   Desc: {res['description'][:100]}...\n")

        if not results:
            print("No results found. Selectors might be outdated or site structure changed.")
    
    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        # Cleanup
        await browser_manager.close()

if __name__ == "__main__":
    asyncio.run(test_cordis_no_api())
