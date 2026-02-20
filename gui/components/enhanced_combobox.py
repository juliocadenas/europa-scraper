#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Combobox
---------------
A combobox with search functionality.
"""

import tkinter as tk
from tkinter import ttk
import re

class EnhancedCombobox(ttk.Combobox):
    """Enhanced combobox with search functionality"""
    
    def __init__(self, master=None, **kwargs):
        """Initialize the enhanced combobox"""
        super().__init__(master, **kwargs)
        
        # Set up search functionality
        self.bind('<KeyRelease>', self._on_key_release)
        
        # Store original values
        self._all_values = []
    
    def configure(self, **kwargs):
        """Configure the combobox"""
        if 'values' in kwargs:
            self._all_values = list(kwargs['values'])
        
        super().configure(**kwargs)
    
    def _on_key_release(self, event):
        """Handle key release event for search"""
        # Ignore special keys
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return', 'Escape'):
            return
        
        # Get current text
        current_text = self.get()
        
        if not current_text:
            # Reset to all values if empty
            self.configure(values=self._all_values)
            return
        
        # Filter values based on current text
        filtered_values = [
            value for value in self._all_values
            if current_text.lower() in str(value).lower()
        ]
        
        # Update dropdown values
        self.configure(values=filtered_values)
        
        # Show dropdown
        self.event_generate('<Down>')
