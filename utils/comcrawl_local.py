import requests
import json
from datetime import datetime, timedelta

class IndexClient:
    def __init__(self):
        self.results = []

    def search(self, url_pattern, search_term=None, from_date=None, to_date=None):
        self.results = []
        try:
            # First, get the list of all available indexes
            collections_url = "http://index.commoncrawl.org/collinfo.json"
            collections_response = requests.get(collections_url, timeout=15)
            collections_response.raise_for_status()
            latest_index = collections_response.json()[0]["id"]
            print(f"Using latest Common Crawl index: {latest_index}")

            # Sanitize the search term to be part of the URL query
            query_term = ''
            if search_term:
                # Take the first two words, lowercase, and use them in the query
                query_term = ''.join(search_term.lower().split()[:2])

            # Construct a more specific URL pattern
            specific_url_pattern = f"{url_pattern.replace('/*', '')}/*{query_term}*"

            # Now, search within that specific, latest index with the refined pattern
            api_url = f"http://index.commoncrawl.org/{latest_index}-index?url={specific_url_pattern}&output=json"
            
            response = requests.get(api_url)
            response.raise_for_status()
            
            records = response.text.strip().split('\n')
            
            for record in records:
                try:
                    record_data = json.loads(record)
                    # Basic filtering by search term if provided
                    if search_term:
                        # This is a placeholder for a more sophisticated search
                        # The CDX API doesn't support full-text search directly
                        # A real implementation would download the WARC file and search within it.
                        # For this purpose, we assume the URL or a description might contain the term.
                        self.results.append({
                            "url": record_data.get("url"),
                            "title": record_data.get("url"), # No title available from CDX
                            "description": f"MIME: {record_data.get('mime-detected')}"
                        })
                    else:
                        self.results.append({
                            "url": record_data.get("url"),
                            "title": record_data.get("url"),
                            "description": f"MIME: {record_data.get('mime-detected')}"
                        })
                except json.JSONDecodeError:
                    continue # Ignore malformed lines
        except requests.exceptions.RequestException as e:
            print(f"Error fetching from Common Crawl Index: {e}")

