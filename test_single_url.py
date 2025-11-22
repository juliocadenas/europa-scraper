#!/usr/bin/env python3
"""
Test content extraction from a single URL
"""

import asyncio
import logging
from utils.scraper.browser_manager import BrowserManager
from utils.scraper.content_extractor import ContentExtractor
from utils.config import Config
from threading import Lock

# Setup logging
logging.basicConfig(level=logging.INFO)

class MockServerState:
    """Mock server state for testing"""

    def __init__(self):
        self.captcha_solution_queue = asyncio.Queue()
        self._lock = Lock()

    def set_pending_captcha_challenge(self, challenge_data):
        logging.info(f"Mock CAPTCHA challenge: {challenge_data}")
        return None

async def test_url(url):
    """Test content extraction from a single URL."""

    config_manager = Config()
    server_state = MockServerState()
    browser_manager = BrowserManager(config_manager, server_state)
    extractor = ContentExtractor(browser_manager)

    # Initialize browser
    await browser_manager.initialize()

    try:
        print(f"🔍 Testing content extraction from: {url}")
        content = await extractor.extract_full_content(url)

        if content:
            print("✅ Content extracted successfully!")
            print(f"📊 Length: {len(content)} characters")
            print(f"📄 Word count: {len(content.split())}")
            print("\n" + "="*80)
            print("CONTENT PREVIEW (first 500 chars):")
            print("="*80)
            print(content[:500])
            print("\n" + "="*80)
            print("CONTENT PREVIEW (last 500 chars):")
            print("="*80)
            print(content[-500:])

            # Check for common terms
            search_terms = ["cotton", "agriculture", "farm", "crop", "usda", "gov"]
            print(f"\n🔍 Checking for search terms: {search_terms}")
            for term in search_terms:
                found = term.lower() in content.lower()
                status = "✅" if found else "❌"
                print(f"  {status} '{term}': {found}")
        else:
            print("❌ No content extracted")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser_manager.close()

if __name__ == "__main__":
    # Example USA.gov URL - replace with actual URLs from your results
    test_urls = [
        "https://www.usda.gov/topics/cotton",
        "https://www.ers.usda.gov/topics/crops/cotton-and-wool/cotton-sector/",
    ]

    async def main():
        for url in test_urls:
            await test_url(url)
            print("\n" + "="*100 + "\n")

    asyncio.run(main())