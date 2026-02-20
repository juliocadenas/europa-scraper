import re
import os
import logging
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to be safe for all operating systems.
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
    """
    try:
        # Normalize unicode characters
        filename = unicodedata.normalize('NFKD', filename)
        
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Replace spaces with underscores
        filename = re.sub(r'\s+', '_', filename)
        
        # Limit length
        if len(filename) > 255:
            name_parts = filename.split('.')
            if len(name_parts) > 1:
                ext = name_parts[-1]
                name = '.'.join(name_parts[:-1])
                filename = f"{name[:250-len(ext)]}.{ext}"
            else:
                filename = filename[:255]
        
        # Ensure filename is not empty
        if not filename:
            filename = "unnamed_file"
        
        return filename
        
    except Exception as e:
        logger.error(f"Error sanitizing filename: {str(e)}")
        return "unnamed_file"

def sanitize_text(text: str) -> str:
    """
    Sanitize text for display or storage.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text
    """
    try:
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1F\x7F]', '', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Trim whitespace
        text = text.strip()
        
        return text
        
    except Exception as e:
        logger.error(f"Error sanitizing text: {str(e)}")
        return ""
