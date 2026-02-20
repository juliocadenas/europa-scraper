#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Admin Check
---------
Checks for admin privileges.
"""

import os
import sys
import logging
import ctypes

def check_admin_privileges() -> bool:
    """Check if the application is running with admin privileges"""
    logger = logging.getLogger('scraper.admin_check')
    
    try:
        if sys.platform == 'win32':
            # Windows
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            # Unix/Linux/Mac
            return os.geteuid() == 0
    
    except Exception as e:
        logger.error(f"Error checking admin privileges: {e}", exc_info=True)
        return False
