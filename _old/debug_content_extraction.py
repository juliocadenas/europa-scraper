#!/usr/bin/env python3
"""
Debug script for content extraction and keyword matching issues.
Run this to see what's happening with content extraction.
"""

import asyncio
import logging
import sys
from utils.scraper.content_extractor import ContentExtractor
from utils.scraper.text_processor import TextProcessor
from utils.scraper.browser_manager import BrowserManager
from utils.config import Config
from threading import Lock

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class MockServerState:
    """Mock server state for testing"""

    def __init__(self):
        self.captcha_solution_queue = asyncio.Queue()
        self._lock = Lock()

    def set_pending_captcha_challenge(self, challenge_data):
        logger.info(f"Mock CAPTCHA challenge: {challenge_data}")
        return None

async def debug_specific_url(url, search_term):
    """Debug a specific URL and search term."""

    print(f"\n{'='*80}")
    print(f"DEBUGGING URL: {url}")
    print(f"SEARCH TERM: '{search_term}'")
    print(f"{'='*80}")

    # Initialize components
    config_manager = Config()
    server_state = MockServerState()
    browser_manager = BrowserManager(config_manager, server_state)
    text_processor = TextProcessor()
    content_extractor = ContentExtractor(browser_manager)

    # Initialize browser
    await browser_manager.initialize()

    try:
        # Extract content
        print("\n📥 Extracting content...")
        content = await content_extractor.extract_full_content(url)

        if not content:
            print("❌ FAILED: No content extracted")
            return False

        print(f"✅ Content extracted: {len(content)} characters")

        # Analyze content
        total_words = text_processor.count_all_words(content)
        word_counts = text_processor.estimate_keyword_occurrences(content, search_term)

        print(f"📊 Total words: {total_words}")
        print(f"🔍 Keyword counts: {word_counts}")

        # Check keyword matching
        if word_counts and any(count > 0 for count in word_counts.values()):
            print("✅ KEYWORDS FOUND - This result should be kept")
            return True
        else:
            print("❌ NO KEYWORDS FOUND")

            # Check if search term is anywhere in content
            search_lower = search_term.lower()
            content_lower = content.lower()

            if search_lower in content_lower:
                print("🔍 Search term found in raw content (case-insensitive)")
                # Show context around the found term
                start_idx = content_lower.find(search_lower)
                context_start = max(0, start_idx - 100)
                context_end = min(len(content), start_idx + len(search_lower) + 100)
                context = content[context_start:context_end]
                print(f"Context: '...{context}...'")
            else:
                print("🚫 Search term not found anywhere in content")

            return False

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await browser_manager.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        url = sys.argv[1]
        search_term = sys.argv[2]
        asyncio.run(debug_specific_url(url, search_term))
    else:
        print("Usage: python debug_content_extraction.py <URL> <search_term>")
        print("Example: python debug_content_extraction.py 'https://example.com' 'test'")
        print("For debugging scraping issues, use URLs from the omitted results Excel file.")