from urllib.parse import quote_plus, urlparse
import logging

logger = logging.getLogger(__name__)

class URLUtils:
    """
    Utilities for URL handling and validation.
    """
    
    @staticmethod
    def quote_plus(text: str) -> str:
        """
        Encodes text for URL.
        
        Args:
            text: Text to encode
            
        Returns:
            URL-encoded text
        """
        return quote_plus(text)
    
    @staticmethod
    def is_excluded_domain(url: str, excluded_domains: list = None) -> bool:
        """
        Checks if a domain should be excluded.
        
        Args:
            url: URL to check
            excluded_domains: List of domains to exclude
            
        Returns:
            True if it should be excluded, False otherwise
        """
        if not excluded_domains:
            excluded_domains = []
            
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
        
            for excluded in excluded_domains:
                if domain.endswith(excluded):
                    return True
            
            return False
        except:
            return False
    
    @staticmethod
    def normalize_url(url: str, base_url: str = "https://cordis.europa.eu") -> str:
        """
        Normalizes a URL to ensure it's absolute.
        
        Args:
            url: URL to normalize
            base_url: Base URL to use for relative URLs
            
        Returns:
            Normalized URL
        """
        if not url:
            return ""
            
        # If already absolute, return as is
        if url.startswith(('http://', 'https://')):
            return url
            
        # Handle relative URLs
        if url.startswith('/'):
            return f"{base_url}{url}"
        else:
            return f"{base_url}/{url}"
    
    @staticmethod
    def is_file_url(url: str) -> bool:
        """
        Checks if a URL points to a downloadable file.
        
        Args:
            url: URL to check
            
        Returns:
            True if it's a file URL, False otherwise
        """
        file_extensions = ['.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.csv', '.json', '.xml']
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        return any(path.endswith(ext) for ext in file_extensions)
