
import sys
import os
import tkinter as tk
from tkinter import ttk

# Add project root to path
sys.path.append(os.getcwd())

from gui.scraper_gui import ScraperGUI

def check_button_binding():
    root = tk.Tk()
    app = ScraperGUI(root)
    
    # Access the button
    button = app.load_courses_button
    command = button.cget('command')
    
    print(f"Button Text: {button.cget('text')}")
    print(f"Button Command: {command}")
    
    # Check if the method exists
    if hasattr(app, '_upload_courses_file'):
        print("✅ Method '_upload_courses_file' exists in ScraperGUI.")
    else:
        print("❌ Method '_upload_courses_file' DOES NOT exist in ScraperGUI.")
        
    # Check if the command matches the method
    # Tcl/Tk commands are strings, so we can't directly compare, but we can check the name
    print(f"Bound method name: {app._upload_courses_file.__name__}")

    root.destroy()

if __name__ == "__main__":
    try:
        check_button_binding()
    except Exception as e:
        print(f"Error: {e}")
