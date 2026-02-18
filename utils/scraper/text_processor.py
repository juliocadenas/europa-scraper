import re
import logging
from typing import List, Dict, Set, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)

# Precompilación de expresiones regulares para mejor rendimiento
WORD_PATTERN = re.compile(r'\b\w+\b')
URL_PATTERN = re.compile(r'https?://\S+')
WWW_PATTERN = re.compile(r'www\.\S+')
URL_END_PATTERN = re.compile(r'\s+https?://\S+$')
WWW_END_PATTERN = re.compile(r'\s+www\.\S+$')
URL_REF_PATTERN = re.compile(r'\s+(?:visita|ver|visitar|click|enlace|link|url|ver en|más en|más información en|leer más en)[:\s]+\S+$', re.IGNORECASE)
DOMAIN_PATTERN = re.compile(r'\s+\w+\.\w+(?:\.\w+)*(?:/\S*)?')
MULTI_SPACE_PATTERN = re.compile(r'\s+')

class TextProcessor:
    """
    Processes and analyzes text content.
    Handles text cleaning, word counting, and relevance analysis.
    """
    
    def __init__(self):
        """Initialize the text processor with stop words."""
        self.stop_words = {
            'a', 'ante', 'bajo', 'con', 'contra', 'de', 'desde', 'durante', 'en', 'entre',
            'hacia', 'hasta', 'mediante', 'para', 'por', 'según', 'sin', 'sobre', 'tras',
            'y', 'e', 'ni', 'que', 'o', 'u', 'pero', 'mas', 'aunque', 'sino', 'porque',
            'pues', 'ya', 'si', 'the', 'of', 'and', 'to', 'in', 'for', 'with', 'on', 'at',
            'from', 'by', 'about', 'as', 'into', 'like', 'through', 'after', 'over', 'between',
            'out', 'against', 'during', 'without', 'before', 'under', 'around', 'among',
            'or', 'but', 'yet', 'so', 'nor', 'if', 'while', 'because', 'though', 'although',
            'since', 'unless', 'than', 'whether', 'as if', 'even if', 'in order that'
        }
        # Caché para palabras significativas
        self._significant_words_cache = {}
        # Límite de caché para evitar uso excesivo de memoria
        self._cache_limit = 1000
    
    def filter_stop_words(self, query: str) -> str:
        """
        Filters prepositions and conjunctions from the query.
        
        Args:
            query: Original query
            
        Returns:
            Filtered query
        """
        if not query:
            return ""
            
        words = query.split()
        filtered_words = [word for word in words if word.lower() not in self.stop_words]
        
        # If nothing remains after filtering, return the original query
        if not filtered_words:
            return query
            
        return ' '.join(filtered_words)
    
    def get_significant_words(self, text: str) -> List[str]:
        """
        Gets significant words (excluding prepositions and conjunctions).
        Uses caching for improved performance.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of significant words
        """
        if not text:
            return []
        
        # Check cache first (for short to medium texts)
        if len(text) < 1000:
            cache_key = hash(text)
            if cache_key in self._significant_words_cache:
                return self._significant_words_cache[cache_key]
        
        # Use precompiled regex for better performance
        words = WORD_PATTERN.findall(text.lower())
        significant_words = [word for word in words if word not in self.stop_words]
        
        # Cache result for short to medium texts
        if len(text) < 1000:
            # Limit cache size
            if len(self._significant_words_cache) > self._cache_limit:
                self._significant_words_cache.clear()
            self._significant_words_cache[hash(text)] = significant_words
            
        return significant_words
    
    def count_all_words(self, text: str) -> int:
        """
        Counts all words in the text using a simple space split.
        This provides a more accurate count of original words.
        
        Args:
            text: Text to analyze
        
        Returns:
            Total number of words
        """
        if not text:
            return 0
        # Use a simple split to count words, which is more accurate for total word count
        return len(text.split())

    def count_significant_words(self, text: str) -> int:
        """
        Counts significant words (excluding prepositions and conjunctions).
        
        Args:
            text: Text to analyze
            
        Returns:
            Number of significant words
        """
        return len(self.get_significant_words(text))

    def estimate_keyword_occurrences(self, content: str, search_term: str) -> Dict[str, int]:
        """
        Counts occurrences of each keyword from the search term in the content.
        Uses regex with word boundaries for accurate counting.
        
        Args:
            content: Full document content
            search_term: Search term
        
        Returns:
            Dictionary with count of each keyword
        """
        if not content or not search_term:
            return {}

        content_lower = content.lower()
        word_counts = {}
        
        # Get significant words from the search term
        search_words = self.get_significant_words(search_term)
        
        for word in set(search_words):  # Use set to avoid duplicate counting
            if len(word) > 2:
                try:
                    # Use word boundaries for accurate counting
                    pattern = r'\b' + re.escape(word) + r'\b'
                    count = len(re.findall(pattern, content_lower))
                    if count > 0:
                        word_counts[word.capitalize()] = count
                except re.error as e:
                    logger.warning(f"Regex error for word '{word}': {e}")

        return word_counts

    def format_word_counts(self, total_count: int, word_counts: Dict[str, int]) -> str:
        """
        Formats the word count according to the required format.
        
        Args:
            total_count: Total word count
            word_counts: Dictionary with count of each keyword
        
        Returns:
            Formatted string
        """
        parts = [f"Total words: {total_count}"]
        
        # Add count of each keyword
        for word, count in sorted(word_counts.items()):
            parts.append(f"{word}: {count}")
        
        return " | ".join(parts)
    
    def clean_description(self, text: str) -> str:
        """
        Cleans a description by removing URLs and unnecessary spaces.
        Optimized with precompiled regex patterns.
        
        Args:
            text: Text to clean
            
        Returns:
            Clean text
        """
        if not text:
            return ""
        
        # Remove complete URLs (http://, https://, www.) using precompiled patterns
        cleaned = URL_PATTERN.sub('', text)
        cleaned = WWW_PATTERN.sub('', cleaned)
        
        # Remove URLs that may be at the end of the text
        cleaned = URL_END_PATTERN.sub('', cleaned)
        cleaned = WWW_END_PATTERN.sub('', cleaned)
        
        # Remove references to URLs like "Visit: " or "See at: " at the end
        cleaned = URL_REF_PATTERN.sub('', cleaned)
        
        # Remove any text that looks like a URL without protocol (example.com)
        cleaned = DOMAIN_PATTERN.sub('', cleaned)
        
        # Clean multiple spaces and trim
        cleaned = MULTI_SPACE_PATTERN.sub(' ', cleaned).strip()
        
        return cleaned
    
    def should_exclude_result(self, total_words: int, word_counts: Dict[str, int], min_words: int = 30) -> Tuple[bool, str]:
        """
        Determines if a result should be excluded based on keyword count.
        
        Args:
            total_words: Total number of words (for logging/legacy)
            word_counts: Dictionary with count of each keyword
            min_words: Minimum number of keyword occurrences required
            
        Returns:
            Tuple of (should_exclude, reason)
        """
        # Sum all keyword occurrences
        total_keywords_found = sum(word_counts.values()) if word_counts else 0
        
        # Check if total keyword occurrences is less than minimum
        if total_keywords_found < min_words:
            return True, f"Total keywords found ({total_keywords_found}) less than minimum required ({min_words})"
        
        # Don't exclude
        return False, ""
