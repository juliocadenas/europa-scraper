#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scraper Utils
-----------
General utility functions.
"""

import os
import sys
import logging
import platform
from datetime import datetime
from typing import Dict, Any

def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    logger = logging.getLogger('scraper.utils')
    
    try:
        info = {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'python_version': sys.version,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        logger.debug("System information collected")
        return info
    
    except Exception as e:
        logger.error(f"Error getting system information: {e}", exc_info=True)
        return {
            'error': str(e),
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

def format_time_elapsed(seconds: float) -> str:
    """Format seconds into a human-readable time string"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"
