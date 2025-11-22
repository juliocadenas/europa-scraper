#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Config
-----
Application configuration.
"""

import os
import json
import logging
from typing import Dict, Any

class Config:
    """Configuration manager for the application"""
    
    def __init__(self, config_file="config.json"):
        """Initialize the configuration manager"""
        self.logger = logging.getLogger('scraper.config')
        self.config_file = config_file
        self.config = self._load_config()
        
        self.logger.info("Configuration manager initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        default_config = {
            "data_dir": "data",
            "log_dir": "logs",
            "max_results_per_search": 10,
            "relevance_threshold": 0.5,
            "concurrent_searches": 3,
            "captcha_solving_enabled": False,
            "captcha_service": "manual",
            "captcha_api_key": "",
            "headless_mode": True
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                # Update with any missing default values
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                
                self.logger.info(f"Loaded configuration from {self.config_file}")
                return config
            else:
                self.logger.info(f"Configuration file not found, using defaults")
                return default_config
        
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}", exc_info=True)
            return default_config
    
    def save_config(self) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            self.logger.info(f"Saved configuration to {self.config_file}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}", exc_info=True)
            return False
    
    def get(self, key: str, default=None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value"""
        self.config[key] = value
    
    def update(self, config: Dict[str, Any]):
        """Updates the configuration with a dictionary."""
        self.config.update(config)
