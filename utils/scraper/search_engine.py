import logging
import asyncio
import random
import os
import time
from typing import List, Dict, Any, Tuple, Optional, Set
from playwright.async_api import Page
from functools import lru_cache
import aiohttp
import urllib.parse
import re

from utils.scraper.browser_manager import BrowserManager
from utils.scraper.text_processor import TextProcessor
from utils.scraper.url_utils import URLUtils
from utils.captcha_solver import CaptchaSolver
from utils.scraper.cordis_api_client import CordisApiClient

logger = logging.getLogger(__name__)

class ManualCaptchaPendingError(Exception):
    """Custom exception to indicate that a manual CAPTCHA is pending."""
    pass

class SearchEngine:
    """
    Handles searching on different search engines and extracting search results.
    """
    
    def __init__(self, browser_manager: BrowserManager, text_processor: TextProcessor, config_manager=None):
        self.browser_manager = browser_manager
        self.text_processor = text_processor
        self.url_utils = URLUtils()
        self._search_cache = {}
        self.captcha_solver = CaptchaSolver(config_manager) if config_manager else None
        self.cordis_api_client = CordisApiClient()

    # ... (existing methods) ...

    async def get_search_results(self, search_term: str, search_engine: str, site_domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene los resultados de búsqueda utilizando el motor especificado.
        """
        if search_engine == 'Google':
            return await self.search_google(search_term, site_domain)
        elif search_engine == 'DuckDuckGo':
            return await self.search_duckduckgo(search_term, site_domain)
        elif search_engine == 'Cordis Europa':
            return await self.search_cordis_europa(search_term)
        elif search_engine == 'Cordis Europa API':
             return await self.cordis_api_client.search_projects_and_publications(search_term)
        elif search_engine == 'Wayback Machine':
            return await self.search_wayback(search_term, site_domain)
        else:
            logger.warning(f"Motor de búsqueda no soportado: {search_engine}")
            return []
    async def search_google(self, query: str, site_domain: str = None, max_pages: int = 100) -> List[Dict[str, Any]]:
        """
        Performs a highly stealthy and human-like Google search.
        This method simulates human behavior to avoid bot detection.
        """
        search_query = f'{query} site:{site_domain}' if site_domain else query
        logger.info(f"Starting stealthy Google search with term: '{search_query}'")

        all_results = []
        unique_urls = set()
        page = None

        try:
            page = await self.browser_manager.new_page()

            logger.info("Navigating to Google homepage with human-like delays.")
            await page.goto("https://www.google.com/", wait_until='domcontentloaded', timeout=60000)

            # Add realistic initial loading time to appear human
            await asyncio.sleep(random.uniform(3.0, 8.0))

            # Sometimes scroll a bit like a regular user browsing
            if random.random() < 0.4:
                logger.info("Simulating casual scrolling on homepage...")
                await page.mouse.wheel(0, random.uniform(200, 400))
                await asyncio.sleep(random.uniform(0.5, 1.2))

            # Additional human-like pause
            await asyncio.sleep(random.uniform(2.0, 5.0))

            try:
                consent_button = page.locator('button:has-text("Accept all"), button:has-text("Aceptar todo")').first
                if await consent_button.is_visible(timeout=5000):
                    logger.info("Cookie consent page detected on homepage. Clicking accept button with human-like behavior.")
                    await consent_button.hover()
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    await consent_button.click()
                    await asyncio.sleep(random.uniform(2.0, 4.0))

                    # Some mouse movements after accepting cookies
                    await page.mouse.move(random.randint(100, 500), random.randint(100, 300))
                    await asyncio.sleep(random.uniform(0.5, 1.0))
            except Exception:
                logger.info("No cookie consent dialog on homepage, or already handled.")

            # Simulate more sophisticated human browsing behavior
            logger.info("Simulating human browsing behavior...")
            mouse_positions = [
                (random.randint(100, 600), random.randint(100, 400)),
                (random.randint(200, 800), random.randint(150, 500)),
                (random.randint(50, 950), random.randint(200, 600)),
                (random.randint(150, 750), random.randint(100, 400)),
                (random.randint(100, 900), random.randint(150, 550))
            ]
            for x, y in random.sample(mouse_positions, random.randint(3, 5)):
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.3, 1.2))
                # Occasional small scrolls
                if random.random() < 0.3:
                    await page.mouse.wheel(0, random.uniform(50, 150))
                    await asyncio.sleep(random.uniform(0.2, 0.5))

            # Click on a random link or area to mimic real browsing
            if random.random() < 0.2:
                logger.info("Simulating clicking on homepage element...")
                clickable_areas = page.locator('a, button, [role="button"]')
                count = await clickable_areas.count()
                if count > 0:
                    random_index = random.randint(0, min(count - 1, 10))
                    element = clickable_areas.nth(random_index)
                    try:
                        if await element.is_visible(timeout=3000):
                            # Don't actually click, just hover to simulate interest
                            await element.hover()
                            await asyncio.sleep(random.uniform(0.8, 2.0))
                    except Exception:
                        pass  # Ignore hover failures

            # Final human-like pause before focusing search
            await asyncio.sleep(random.uniform(2.0, 4.5))

            search_box = page.locator('textarea[name="q"]')
            logger.info("Typing search query with human-like delays...")
            await search_box.hover()
            await asyncio.sleep(random.uniform(0.2, 0.5))
            await search_box.click()
            await asyncio.sleep(random.uniform(1.0, 2.0))

            # Human-like typing with variable delays and occasional mistakes
            for i, char in enumerate(search_query):
                base_delay = random.uniform(120, 280)  # More realistic typing speed
                if random.random() < 0.04:  # 4% chance of backspace (less mistakes)
                    await page.keyboard.press("Backspace")
                    await asyncio.sleep(random.uniform(100, 200))  # Pause after mistake
                await page.keyboard.type(char, delay=base_delay)
                # Add more realistic character spacing
                char_delay = random.uniform(0.02, 0.15)  # More varied spacing
                await asyncio.sleep(char_delay)
                if random.random() < 0.02:  # Occasional pause for "thinking"
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                # Random mouse movement during typing to simulate user activity
                if random.random() < 0.008:  # Very occasional
                    search_box_region = await search_box.bounding_box()
                    if search_box_region:
                        x_offset = random.uniform(-20, 20)
                        y_offset = random.uniform(-5, 5)
                        await page.mouse.move(
                            search_box_region['x'] + search_box_region['width']/2 + x_offset,
                            search_box_region['y'] + search_box_region['height']/2 + y_offset
                        )
                        await asyncio.sleep(random.uniform(0.1, 0.3))

            total_typing_time = len(search_query) / 10  # Rough estimate
            logger.info(f"Typing completed in ~{total_typing_time:.1f}s")

            # Longer human-like pause before submitting - humans take time to review what they've typed
            await asyncio.sleep(random.uniform(1.5, 4.0))

            # Sometimes users click the search button instead of Enter
            if random.random() < 0.3:  # 30% chance to use search button
                try:
                    search_button = page.locator('input[value*="Search"], button[aria-label*="search"]').first
                    if await search_button.is_visible(timeout=2000):
                        await search_button.click()
                        logger.info("Using search button instead of Enter key")
                    else:
                        await page.keyboard.press('Enter')
                except Exception:
                    await page.keyboard.press('Enter')
            else:
                await page.keyboard.press('Enter')
            
            # Wait for the page to stabilize by waiting for one of several key selectors
            logger.info("Waiting for search results or CAPTCHA page to load...")
            # Add some random delay to wait times to be less predictable
            search_timeout = int(random.uniform(35000, 45000))  # 35-45 seconds
            task_results = asyncio.create_task(page.wait_for_selector("#search", timeout=search_timeout))
            task_captcha = asyncio.create_task(page.wait_for_selector('iframe[src*="recaptcha"]', timeout=search_timeout))
            task_traffic = asyncio.create_task(page.locator('text=/unusual traffic/i').wait_for(timeout=search_timeout))

            done, pending = await asyncio.wait(
                [task_results, task_captcha, task_traffic],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            if task_captcha in done or task_traffic in done:
                logger.warning("CAPTCHA page detected. Attempting to solve automatically...")
                if self.captcha_solver:
                    solved = await self._try_solve_captcha_google(page)
                    if solved:
                        # Continue with the search
                        logger.info("CAPTCHA solved successfully, continuing search...")
                    else:
                        logger.warning("Failed to solve CAPTCHA. Raising exception for manual resolution.")
                        raise ManualCaptchaPendingError("Manual CAPTCHA resolution required.")
                else:
                    logger.warning("No CAPTCHA solver configured. Raising exception for manual resolution.")
                    raise ManualCaptchaPendingError("Manual CAPTCHA resolution required.")
            elif task_results in done:
                logger.info("Page with search results has stabilized.")
            else:
                try:
                    done.pop().result() # Re-raise exception if the task failed
                except Exception as e:
                    logger.error(f"Page did not stabilize after search: {e}")
                    raise e

            # Loop for multiple pages of results
            for current_page_num in range(max_pages):
                logger.info(f"Processing page {current_page_num + 1} of Google results...")
                
                await page.wait_for_selector('#search', timeout=30000)

                for _ in range(random.randint(3, 6)):
                    await page.mouse.wheel(0, random.uniform(300, 600))
                    await asyncio.sleep(random.uniform(0.5, 1.5))

                # Human-like reading pauses
                await asyncio.sleep(random.uniform(2.0, 5.0))

                extracted_results = await page.evaluate('''
                () => {
                    const results = [];
                    document.querySelectorAll('#search > div > div').forEach(el => {
                        const link = el.querySelector('a');
                        const h3 = el.querySelector('h3');
                        if (link && h3 && link.href && !link.href.startsWith('https://www.google.com/search?q=')) {
                            const url = link.href;
                            const title = h3.innerText;
                            let description = '';
                            const descriptionContainer = el.querySelector('div[data-sncf="2"]');
                            if (descriptionContainer) {
                                description = descriptionContainer.innerText;
                            } else {
                                const textBlocks = el.querySelectorAll('div[role="none"]');
                                for (const tb of textBlocks) {
                                    if (tb.innerText && tb.innerText.length > description.length) description = tb.innerText;
                                }
                            }
                            results.push({url, title, description});
                        }
                    });
                    return results;
                }
                ''')

                new_results_on_page = 0
                for r in extracted_results:
                    if r['url'] not in unique_urls:
                        unique_urls.add(r['url'])
                        result = {
                            'url': r['url'],
                            'title': r.get('title'),
                            'description': r.get('description', ''),
                            'mediatype': 'web',
                            'format': None
                        }
                        all_results.append(result)
                        new_results_on_page += 1

                        # Debug first few results
                        if len(all_results) <= 5:
                            logger.debug(f"Search result {len(all_results)}: {r['url']}")
                            logger.debug(f"  Title: {r.get('title', 'No title')}")
                            logger.debug(f"  Description: {r.get('description', 'No desc')[:100]}...")

                if new_results_on_page == 0:
                    logger.info("No new results on this page, stopping pagination.")
                    break

                # Try to find next button and click it
                try:
                    next_button = page.locator('a#pnnext')
                    if await next_button.is_visible(timeout=3000):
                        logger.info("Navigating to next page with human-like behavior...")
                        await next_button.hover()
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                        await next_button.click()
                        await asyncio.sleep(random.uniform(5.0, 10.0))  # Long delay after navigation
                        continue
                    else:
                        break
                except Exception:
                    break

        except ManualCaptchaPendingError:
            raise
        except Exception as e:
            logger.error(f"Error during Google search: {str(e)}")
            logger.error(e)
        finally:
            if page:
                await self.browser_manager.release_page(page)
            logger.info(f"Search completed for '{query}'. Total unique results: {len(all_results)}")
            self._search_cache[query.lower()] = all_results
        
        return all_results


    async def _fetch_cdx_urls(self, site_domain: str, max_items: int = 200) -> List[str]:
        """Fetch candidate URLs from CDX API for a given domain."""
        import urllib.parse
        urls = []
        try:
            cdx_base = "http://web.archive.org/cdx/search/cdx"
            params = {
                "url": f"*.{site_domain}/*",
                "output": "json",
                "filter": "statuscode:200",
                "collapse": "urlkey",
                "limit": max_items
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(cdx_base, params=params, timeout=30) as resp:
                    if resp.status == 200:
                        try:
                            data = await resp.json()
                        except Exception:
                            data = []
                        if isinstance(data, list) and len(data) > 1:
                            for row in data[1:]:
                                try:
                                    original = row[2] if len(row) > 2 else None
                                    timestamp = row[1] if len(row) > 1 else None
                                    if not original:
                                        continue
                                    wayback_url = f"https://web.archive.org/web/{timestamp}/{original}" if timestamp else original
                                    urls.append(wayback_url)
                                except Exception:
                                    continue
        except Exception as e:
            logger.warning(f"_fetch_cdx_urls failed: {e}")
        return urls

    async def _process_snapshot(self, session: aiohttp.ClientSession, snapshot_url: str, query: str, semaphore: asyncio.Semaphore, stop_words: Optional[Set[str]] = None) -> Optional[Dict[str, Any]]:
        """Download snapshot HTML, extract visible text and compute relevance against query."""
        try:
            async with semaphore:
                # Use the snapshot URL directly (should be like https://web.archive.org/web/<ts>/<orig>)
                timeout = aiohttp.ClientTimeout(total=20)
                async with session.get(snapshot_url, timeout=timeout) as resp:
                    if resp.status != 200:
                        return None
                    html = await resp.text()

                # Parse and extract visible text
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'lxml')
                for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript']):
                    try:
                        tag.decompose()
                    except Exception:
                        pass
                visible_text = soup.get_text(' ', strip=True).lower()

                q = query.lower()
                # Build tokens excluding stop words
                tokens = [t for t in re.findall(r"\w+", q) if (not stop_words or t not in stop_words) and len(t) > 2]

                phrase_count = visible_text.count(q)
                word_matches = sum(1 for t in tokens if t in visible_text)

                # Scoring: phrase counts weigh most
                score = 0.0
                if phrase_count > 0:
                    score += min(1.0, 0.7 + 0.1 * phrase_count)
                if tokens:
                    score += min(0.3, (word_matches / len(tokens)) * 0.3)
                score = min(1.0, score)

                if score < 0.3:
                    return None

                matched_words = [t for t in tokens if t in visible_text]
                # Extract timestamp from snapshot_url
                try:
                    ts = snapshot_url.split('/web/')[1].split('/')[0]
                except Exception:
                    ts = None

                return {
                    'url': snapshot_url,
                    'normalized_url': snapshot_url,
                    'score': round(score, 3),
                    'phrase_matches': phrase_count,
                    'word_matches': word_matches,
                    'matched_words': matched_words,
                    'timestamp': ts
                }
        except Exception as e:
            logger.debug(f"_process_snapshot failed for {snapshot_url}: {e}")
            return None

    async def search_wayback(self, query: str, site_domain: Optional[str] = None, max_items: int = 50) -> List[Dict[str, Any]]:
        """
        Use the Wayback Machine APIs (CDX / Archive.org) to collect results.
        This is API-only and will not open Playwright pages to avoid scraping and IP blocking.
        Returns a list of dicts with keys: url, wayback_url, timestamp, title, description, mediatype, format
        """
        results = []
        try:
            # Prefer CDX API when a site_domain is provided because it supports URL pattern queries
            if site_domain:
                cdx_base = "http://web.archive.org/cdx/search/cdx"
                params = {
                    "url": f"*.{site_domain}/*",
                    "output": "json",
                    "filter": "statuscode:200",
                    "collapse": "urlkey",
                    "limit": max_items
                }
                logger.info(f"Querying CDX API for domain {site_domain} with params: {params}")
                async with aiohttp.ClientSession() as session:
                    async with session.get(cdx_base, params=params, timeout=30) as resp:
                        if resp.status == 200:
                            try:
                                cdx_data = await resp.json()
                            except Exception:
                                cdx_text = await resp.text()
                                logger.debug(f"CDX non-json response: {cdx_text[:500]}")
                                cdx_data = []

                            if isinstance(cdx_data, list) and len(cdx_data) > 1:
                                for row in cdx_data[1:]:
                                    try:
                                        timestamp = row[1] if len(row) > 1 else None
                                        original = row[2] if len(row) > 2 else None
                                        if not original:
                                            continue
                                        wayback_url = f"https://web.archive.org/web/{timestamp}/{original}" if timestamp else original
                                        results.append({
                                            'url': original,
                                            'wayback_url': wayback_url,
                                            'timestamp': timestamp,
                                            'title': f"Archived: {original}",
                                            'description': '',
                                            'mediatype': 'web',
                                            'format': None
                                        })
                                        if len(results) >= max_items:
                                            break
                                    except Exception:
                                        continue
            else:
                # Fallback to archive.org advancedsearch.php for free-text queries
                base_urls = [
                    "https://archive.org/advancedsearch.php",
                    "https://archive.org/services/search/v1/scrape"
                ]
                fields = "title,identifier,original,timestamp,mediatype,format"
                q = f'text:"{query}" AND mediatype:web'

                for base in base_urls:
                    if len(results) >= max_items:
                        break
                    params = {"q": q, "fl": fields, "output": "json", "rows": max_items}
                    logger.info(f"Querying Archive.org API {base} with params: {params}")
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(base, params=params, timeout=30) as resp:
                                if resp.status != 200:
                                    logger.debug(f"Archive API returned {resp.status} for {base}")
                                    continue
                                data = await resp.json()

                                if "response" in data and isinstance(data.get("response", {}).get("docs", []), list):
                                    items = data.get("response", {}).get("docs", [])
                                else:
                                    items = data.get("items", [])

                                for item in items:
                                    original_url = item.get('original') or item.get('url') or None
                                    timestamp = item.get('timestamp') or item.get('date') or None
                                    if not original_url:
                                        continue
                                    wayback_url = f"https://web.archive.org/web/{timestamp}/{original_url}" if timestamp else original_url
                                    is_pdf = (item.get('format') == 'PDF') or (".pdf" in original_url.lower())
                                    results.append({
                                        'url': original_url,
                                        'wayback_url': wayback_url,
                                        'timestamp': timestamp,
                                        'title': item.get('title', f"Archived: {original_url}"),
                                        'description': item.get('description', ''),
                                        'mediatype': item.get('mediatype'),
                                        'format': item.get('format')
                                    })
                                    if len(results) >= max_items:
                                        break
                    except Exception as e:
                        logger.warning(f"Archive API {base} failed: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error during Wayback API search: {e}")
        
        # Post-process and refine results: normalize URLs, filter by domain, score and deduplicate
        try:
            def _normalize(u: str) -> str:
                try:
                    p = urllib.parse.urlparse(u)
                    scheme = p.scheme if p.scheme else 'https'
                    netloc = p.netloc
                    path = p.path or ''
                    normalized = urllib.parse.urlunparse((scheme, netloc, path.rstrip('/'), '', '', ''))
                    return normalized
                except Exception:
                    return u

            refined: List[Dict[str, Any]] = []
            seen = set()
            q_lower = (query or '').lower()

            for item in results:
                try:
                    orig = item.get('url') or item.get('original') or ''
                    if not orig:
                        continue

                    norm = _normalize(orig)

                    # If site_domain provided, filter strictly by domain presence
                    if site_domain and site_domain.lower() not in norm.lower():
                        continue

                    title = (item.get('title') or '').lower()
                    desc = (item.get('description') or '').lower()

                    # Scoring: prefer exact phrase in title > phrase in desc > tokens in title/desc > token in URL
                    score = 0.0
                    if q_lower and q_lower in title:
                        score += 0.6
                    if q_lower and q_lower in desc:
                        score += 0.25
                    if q_lower and q_lower in norm.lower():
                        score += 0.15

                    # Token-level boosts (short tokens ignored)
                    tokens = [t for t in re.findall(r"\w+", q_lower) if len(t) > 2]
                    for t in tokens:
                        if re.search(r'\b' + re.escape(t) + r'\b', title):
                            score += 0.08
                        if re.search(r'\b' + re.escape(t) + r'\b', desc):
                            score += 0.04
                        if t in norm.lower():
                            score += 0.02

                    score = min(1.0, score)

                    # Minimum threshold to consider relevant
                    if q_lower and score < 0.10:
                        continue

                    key = norm
                    if key in seen:
                        continue
                    seen.add(key)

                    new_item = dict(item)
                    new_item['normalized_url'] = norm
                    new_item['score'] = round(score, 3)
                    refined.append(new_item)
                except Exception:
                    continue

            # If we didn't find any refined items but original results exist, loosen threshold and try again
            if not refined and results:
                try:
                    for item in results:
                        orig = item.get('url') or item.get('original') or ''
                        if not orig:
                            continue
                        norm = _normalize(orig)
                        key = norm
                        if key in seen:
                            continue
                        seen.add(key)
                        new_item = dict(item)
                        new_item['normalized_url'] = norm
                        new_item['score'] = 0.05
                        refined.append(new_item)
                except Exception:
                    pass

            # Sort by score desc and limit
            refined.sort(key=lambda x: x.get('score', 0.0), reverse=True)
            results = refined[:max_items]
        except Exception as e:
            logger.error(f"Error refining Wayback results: {e}")

        logger.info(f"Wayback API search returned {len(results)} results for '{query}'")
        return results

    @lru_cache(maxsize=128)
    def _get_search_cache(self, query: str) -> Optional[List[Dict[str, Any]]]:
        return self._search_cache.get(query.lower())

    def _set_search_cache(self, query: str, results: List[Dict[str, Any]]):
        self._search_cache[query.lower()] = results
        
    async def get_search_results(self, search_term: str, search_engine: str, site_domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene los resultados de búsqueda utilizando el motor especificado.
        """
        if search_engine == 'Google':
            return await self.search_google(search_term, site_domain)
        elif search_engine == 'DuckDuckGo':
            return await self.search_duckduckgo(search_term, site_domain)
        elif search_engine == 'Cordis Europa':
            return await self.search_cordis_europa(search_term)
        elif search_engine == 'Wayback Machine':
            return await self.search_wayback(search_term, site_domain)
        else:
            logger.warning(f"Motor de búsqueda no soportado: {search_engine}")
            return []
        
    def clear_cache(self):
        """
        Limpia la caché de búsqueda.
        """
        self._search_cache.clear()
        logger.info("Caché de búsqueda limpiada.")
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retorna estadísticas sobre la caché de búsqueda.
        """
        return {
            "cached_queries": len(self._search_cache),
            "total_cached_results": sum(len(v) for v in self._search_cache.values())
        }
        
    def warm_up_cache(self, queries: List[str], search_engine: str, site_domain: Optional[str] = None):
        """
        Pre-carga la caché con una lista de consultas.
        """
        async def _warm_up():
            for query in queries:
                if not self._get_search_cache(query):
                    results = await self.get_search_results(query, search_engine, site_domain)
                    self._set_search_cache(query, results)
                    await asyncio.sleep(random.uniform(1, 3)) # Be nice
        
        asyncio.create_task(_warm_up())
        logger.info(f"Iniciando pre-calentamiento de caché para {len(queries)} consultas.")
        
    def invalidate_cache_entry(self, query: str):
        """
        Invalida una entrada específica en la caché.
        """
        if query.lower() in self._search_cache:
            del self._search_cache[query.lower()]
            logger.info(f"Entrada de caché para '{query}' invalidada.")
            
    def get_cached_queries(self) -> List[str]:
        """
        Retorna una lista de todas las consultas cacheadas.
        """
        return list(self._search_cache.keys())
        
    def set_cache_for_query(self, query: str, results: List[Dict[str, Any]]):
        """
        Establece manualmente la caché para una consulta.
        """
        self._set_search_cache(query, results)
        logger.info(f"Caché establecida manualmente para la consulta: '{query}'")
        
    def get_cache_entry(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Obtiene una entrada de caché específica.
        """
        return self._get_search_cache(query)
        
    def is_query_cached(self, query: str) -> bool:
        """
        Verifica si una consulta está en la caché.
        """
        return query.lower() in self._search_cache
        
    def get_cache_size_in_bytes(self) -> int:
        """
        Calcula el tamaño aproximado de la caché en bytes.
        """
        import json
        return len(json.dumps(self._search_cache))
        
    def trim_cache(self, max_size: int = 100):
        """
        Recorta la caché si excede un número máximo de entradas.
        """
        while len(self._search_cache) > max_size:
            # Elimina el elemento más antiguo (Python 3.7+)
            self._search_cache.pop(next(iter(self._search_cache)))
        logger.info(f"Caché recortada a {len(self._search_cache)} entradas.")
        
    def export_cache(self, filepath: str):
        """
        Exporta la caché a un archivo JSON.
        """
        import json
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._search_cache, f, ensure_ascii=False, indent=4)
            logger.info(f"Caché exportada a {filepath}")
        except Exception as e:
            logger.error(f"Error exportando caché: {e}")
            
    def import_cache(self, filepath: str):
        """
        Importa la caché desde un archivo JSON.
        """
        import json
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self._search_cache = json.load(f)
            logger.info(f"Caché importada desde {filepath}")
        except Exception as e:
            logger.error(f"Error importando caché: {e}")
        
    async def _try_solve_captcha_google(self, page: Page) -> bool:
        """Attempts to solve the CAPTCHA automatically for Google."""
        try:
            logger.info("🔓 Attempting to extract CAPTCHA details and solve for Google...")

            # Extract site_key from reCAPTCHA iframe
            site_key = None
            try:
                iframe = page.locator('iframe[src*="recaptcha"]').first
                if await iframe.count() > 0:
                    src = await iframe.get_attribute('src')
                    if src and 'k=' in src:
                        site_key = src.split('k=')[1].split('&')[0]
                        logger.info(f"Extracted site_key: {site_key}")
            except Exception as e:
                logger.debug(f"Error extracting site_key: {e}")

            # Check if it's a standard pattern without iframe
            if not site_key:
                try:
                    div = page.locator('.g-recaptcha').first
                    if await div.count() > 0:
                        site_key = await div.get_attribute('data-sitekey')
                        logger.info(f"Extracted site_key from div: {site_key}")
                except Exception as e:
                    logger.debug(f"Error extracting site_key from div: {e}")

            # Get current page URL
            page_url = page.url

            if site_key and page_url:
                # Attempt to solve CAPTCHA
                solution = await self.captcha_solver.solve_captcha(page=page, page_url=page_url, site_key=site_key)
                if solution:
                    # Try to submit the CAPTCHA
                    logger.info("⚙️  Attempting to submit CAPTCHA solution...")

                    # For reCAPTCHA V2, sometimes it auto-submits, sometimes needs script
                    await asyncio.sleep(3)  # Wait for auto-submit

                    # Check if solved
                    await page.reload()  # Refresh page to see if unblocked
                    await page.wait_for_load_state('domcontentloaded', timeout=10000)

                    # Navigate back to search if needed - but since we're in the search page, this might not be needed
                    if page.url != page_url:
                        await page.go_back()
                        await page.wait_for_load_state('domcontentloaded', timeout=10000)

                    return True
                else:
                    logger.warning("CAPTCHA solving returned no solution")
            else:
                logger.warning(f"Could not extract CAPTCHA details: site_key={site_key}, page_url={page_url}")

        except Exception as e:
            logger.error(f"Error during CAPTCHA solving attempt for Google: {e}")

        return False

    async def search_cordis_europa(self, query: str, max_pages: int = 100) -> List[Dict[str, Any]]:
        """
        Searches cordis.europa.eu for the given query and navigates through pages.
        This version is adapted from the old, working V2.6 scraper.
        """
        page = None
        all_results = []
        unique_urls = set()
        
        try:
            # Prepare query and URL
            filtered_query = self.text_processor.filter_stop_words(query)
            logger.info(f"Original query: '{query}', Filtered query for URL: '{filtered_query}'")
            encoded_query = self.url_utils.quote_plus(filtered_query)
            base_url = "https://cordis.europa.eu/search"

            page = await self.browser_manager.new_page()
            page.set_default_timeout(60000)

            # --- Page loading and preparation logic ---
            async def load_and_prepare_page(url: str, is_first_page: bool = False):
                logger.info(f"Navigating to: {url}")
                await page.goto(url, wait_until='domcontentloaded')

                if is_first_page:
                    try:
                        logger.info("Looking for cookie consent button with selector: 'button.wt-ecl-cookie-consent-banner__accept-button'")
                        accept_button = page.locator('button.wt-ecl-cookie-consent-banner__accept-button')
                        await accept_button.wait_for(state='visible', timeout=10000)
                        await accept_button.click()
                        logger.info("Cookie consent button clicked successfully.")
                        # Wait a bit for the banner to disappear
                        await asyncio.sleep(2)
                    except Exception as e:
                        logger.info(f"Cookie consent banner not found or failed to click (this might be ok): {e}")

                try:
                    await page.wait_for_selector('app-card-search', timeout=30000)
                    logger.info("Search results container 'app-card-search' is visible.")
                except Exception:
                    logger.warning(f"Timeout waiting for results container 'app-card-search' on {url}. The page might be empty.")


            # --- Main execution ---
            # Load the first page (using num=10 to match user's successful manual search)
            first_page_url = f"{base_url}?q={encoded_query}&p=1&num=10&srt=Relevance:decreasing&archived=true"
            logger.info(f"Generated Cordis URL: {first_page_url}")
            await load_and_prepare_page(first_page_url, is_first_page=True)

            # Handle potential CAPTCHA on the first page
            if hasattr(self.browser_manager, 'captcha_solver') and await self.browser_manager.captcha_solver.is_captcha_present(page):
                logger.warning(f"CAPTCHA detected on the first page for query: '{query}'")
                captcha_handled = await self.browser_manager.captcha_solver.handle_captcha(page)
                if not captcha_handled:
                    logger.error("Failed to handle CAPTCHA. Aborting search for this query.")
                    return []
                # Re-check for results after handling captcha
                await page.wait_for_selector('app-card-search', timeout=30000)

            # Loop through pages
            current_page = 1
            consecutive_empty_pages = 0
            
            while current_page <= max_pages:
                if current_page > 1:
                    page_url = f"{base_url}?q={encoded_query}&p={current_page}&num=10&srt=Relevance:decreasing&archived=true"
                    await load_and_prepare_page(page_url)
                
                # --- Extract results from the current page ---
                js_code = '''
                () => {
                    const results = [];
                    document.querySelectorAll('app-card-search').forEach(element => {
                        try {
                            const titleElement = element.querySelector('a.c-card-search__title');
                            const descriptionElement = element.querySelector('div.c-card-search__block');

                            if (titleElement && titleElement.href) {
                                const title = titleElement.textContent.trim();
                                const url = titleElement.href;
                                let description = '';
                                if (descriptionElement) {
                                    description = descriptionElement.innerText.trim().replace(/\s+/g, ' ');
                                }
                                results.push({ title, url, description });
                            }
                        } catch (e) {
                            console.error('Error processing a result element:', e);
                        }
                    });
                    return results;
                }
                '''
                extracted_results = await page.evaluate(js_code)

                if not extracted_results:
                    consecutive_empty_pages += 1
                    logger.warning(f"No results extracted on page {current_page}. ({consecutive_empty_pages} consecutive empty pages)")
                    if consecutive_empty_pages >= 3:
                        logger.info("Stopping search after 3 consecutive empty pages.")
                        break
                    current_page += 1
                    continue
                
                consecutive_empty_pages = 0
                new_results_on_page = 0
                for result in extracted_results:
                    if result['url'] not in unique_urls:
                        unique_urls.add(result['url'])
                        all_results.append(result)
                        new_results_on_page += 1
                
                logger.info(f"Found {len(extracted_results)} results on page {current_page} ({new_results_on_page} new). Total unique: {len(all_results)}")
                
                # Check for "no new unique results" condition
                if new_results_on_page == 0 and current_page > 1:
                    logger.info("No new unique results on this page. Assuming end of results.")
                    break

                current_page += 1

        except Exception as e:
            logger.error(f"CRITICAL error in search_cordis_europa: {str(e)}", exc_info=True)
            if page:
                await page.screenshot(path="critical_error_cordis.png")
            return []
        
        finally:
            if page:
                await self.browser_manager.release_page(page)
            logger.info(f"Search for '{query}' on Cordis finished. Total unique results: {len(all_results)}.")
            # Cache the results
            if query.lower() not in self._search_cache:
                self._search_cache[query.lower()] = all_results

        return all_results
        
    def __getstate__(self):
        """
        Prepara el estado para el 'pickling'.
        """
        state = self.__dict__.copy()
        # No se puede hacer 'pickle' de LRU cache, así que lo convertimos a dict
        state['_search_cache'] = dict(self._search_cache)
        return state

    def __setstate__(self, state):
        """
        Restaura el estado desde el 'pickling'.
        """
        self.__dict__.update(state)
        # Restaurar el LRU cache desde el dict
        self._search_cache = lru_cache(maxsize=128)(self._search_cache)
        
    def __contains__(self, query: str) -> bool:
        """
        Permite usar 'in' para verificar si una consulta está en la caché.
        """
        return self.is_query_cached(query)
    
    async def search_duckduckgo(self, query: str, site_domain: str = None) -> List[Dict[str, Any]]:
        """
        Realiza búsqueda en DuckDuckGo.
        """
        try:
            search_url = f"https://duckduckgo.com/html/?q={query}"
            if site_domain:
                search_url += f" site:{site_domain}"
            
            logger.info(f"Realizando búsqueda en DuckDuckGo: {query}")
            
            # Verificar que el navegador esté disponible
            if not await self.browser_manager.check_playwright_browser():
                logger.error("Navegador no disponible para búsqueda DuckDuckGo")
                return []
            
            # Usar playwright para obtener resultados
            page = await self.browser_manager.new_page()
            try:
                print(f"\n[DEBUG-DDG-1] INICIO BÚSQUEDA DDG. URL: {search_url}")
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                print(f"\n[DEBUG-DDG-2] NAVEGACIÓN DDG EXITOSA. URL: {search_url}")
                
                # Esperar a que cargue la página
                await asyncio.sleep(2)
                
                # Extraer resultados de búsqueda
                results = await page.evaluate('''
                    () => {
                        const results = [];
                        const searchResults = document.querySelectorAll('.result__body');
                        
                        searchResults.forEach(result => {
                            const titleElement = result.querySelector('h2.result__title a');
                            const linkElement = result.querySelector('h2.result__title a');
                            const snippetElement = result.querySelector('.result__snippet');
                            
                            if (linkElement && titleElement) {
                                const title = titleElement.textContent.trim();
                                const url = linkElement.href;
                                const description = snippetElement ? snippetElement.textContent.trim() : '';
                                
                                if (url) {
                                    results.push({
                                        'url': url,
                                        'title': title,
                                        'description': description,
                                        'mediatype': 'web',
                                        'format': None
                                    });
                                }
                            }
                        });
                        
                        return results;
                    }
                ''')
                
                logger.info(f"Se encontraron {len(results)} resultados en DuckDuckGo")
                return results
                
            except Exception as e:
                logger.error(f"Error en búsqueda DuckDuckGo: {str(e)}")
                return []
            finally:
                try:
                    await self.browser_manager.release_page(page)
                except Exception as e:
                    logger.error(f"Error liberando página: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error general en búsqueda DuckDuckGo: {str(e)}")
            return []