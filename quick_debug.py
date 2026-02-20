#!/usr/bin/env python3
"""
Quick debug script to see what's happening during scraping.
"""

import asyncio
import logging
from utils.scraper.browser_manager import BrowserManager
from utils.scraper.search_engine import SearchEngine
from utils.scraper.text_processor import TextProcessor
from utils.config import Config
from threading import Lock

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockServerState:
    """Mock server state for testing"""

    def __init__(self):
        self.captcha_solution_queue = asyncio.Queue()
        self._lock = Lock()

    def set_pending_captcha_challenge(self, challenge_data):
        logger.info(f"Mock CAPTCHA challenge: {challenge_data}")
        return None

async def quick_search_test():
    """Quick test to see what Google returns."""

    # Initialize components
    config_manager = Config()
    server_state = MockServerState()
    browser_manager = BrowserManager(config_manager, server_state)
    text_processor = TextProcessor()
    search_engine = SearchEngine(browser_manager, text_processor, config_manager)

    try:
        # Initialize browser first
        await browser_manager.initialize()
        logger.info("Browser initialized successfully")

        # Test search
        logger.info("Testing search for 'Cotton site:usa.gov'...")

        results = await search_engine.get_search_results("Cotton", "Google", "usa.gov")

        logger.info(f"Found {len(results)} results")
        for i, result in enumerate(results[:3]):  # Show first 3
            logger.info(f"Result {i+1}:")
            logger.info(f"  URL: {result['url']}")
            logger.info(f"  Title: {result.get('title', 'No title')}")
            logger.info(f"  Description: {result.get('description', 'No description')[:100]}...")

    except Exception as e:
        logger.error(f"Error during search: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser_manager.close()

if __name__ == "__main__":
    asyncio.run(quick_search_test())