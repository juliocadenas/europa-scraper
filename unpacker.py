#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unpacker for CORDIS Europa CSV Scraper
--------------------------------
This script unpacks the Chromium browser and launches the main application.
"""

import os
import sys
import zipfile
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import time
import shutil
import urllib.request

def show_progress_window(title, message):
    """Show a progress window with the given title and message."""
    root = tk.Tk()
    root.title(title)
    root.geometry("400x150")
    root.resizable(False, False)
    
    # Center the window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    # Add message label
    label = tk.Label(root, text=message, wraplength=380, justify="center", padx=10, pady=10)
    label.pack(expand=True)
    
    # Add progress bar
    progress_var = tk.DoubleVar()
    progress_bar = tk.Canvas(root, width=350, height=20, bg="white")
    progress_bar.pack(pady=10)
    
    def update_progress_bar(value):
        progress_bar.delete("progress")
        width = 350 * (value / 100)
        progress_bar.create_rectangle(0, 0, width, 20, fill="green", tags="progress")
        progress_var.set(value)
        root.update()
    
    return root, update_progress_bar

def download_chromium(output_path, progress_callback=None):
    """Download Chromium browser from the official source."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # URL for Chromium browser
        url = "https://cdn.playwright.dev/dbazure/download/playwright/builds/chromium/1161/chromium-win64.zip"
        
        # Download with progress updates
        def report_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, int(downloaded * 100 / total_size))
            if progress_callback:
                progress_callback(percent)
        
        # Download the file
        urllib.request.urlretrieve(url, output_path, reporthook=report_progress)
        return True
    except Exception as e:
        print(f"Error downloading browser: {e}")
        return False

def extract_browser(browser_zip, target_dir, progress_callback=None):
    """Extract the browser zip file to the target directory with progress updates."""
    try:
        with zipfile.ZipFile(browser_zip, 'r') as zip_ref:
            total_files = len(zip_ref.infolist())
            extracted_files = 0
            
            for file in zip_ref.infolist():
                zip_ref.extract(file, target_dir)
                extracted_files += 1
                if progress_callback:
                    progress = int((extracted_files / total_files) * 100)
                    progress_callback(progress)
        
        return True
    except Exception as e:
        print(f"Error extracting browser: {e}")
        return False

def setup_playwright_browsers_path():
    """Set up the PLAYWRIGHT_BROWSERS_PATH environment variable."""
    # Get the directory of the executable
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        app_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set the PLAYWRIGHT_BROWSERS_PATH environment variable
    browsers_path = os.path.join(app_dir, "playwright_browsers")
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browsers_path
    
    # Create the directory if it doesn't exist
    os.makedirs(browsers_path, exist_ok=True)
    
    return browsers_path

def copy_browser_to_playwright_dir(extracted_dir, playwright_dir):
    """Copy the extracted browser to the Playwright browsers directory."""
    try:
        # Create both possible directory structures that Playwright might look for
        # Structure 1: chromium-1161
        chromium_dir1 = os.path.join(playwright_dir, "chromium-1161")
        os.makedirs(chromium_dir1, exist_ok=True)
        
        # Structure 2: chromium_headless_shell-1161
        chromium_dir2 = os.path.join(playwright_dir, "chromium_headless_shell-1161")
        os.makedirs(chromium_dir2, exist_ok=True)
        
        # Source directory (extracted Chromium)
        chrome_win_source = os.path.join(extracted_dir, "chrome-win")
        
        # Target directories
        chrome_win_target1 = os.path.join(chromium_dir1, "chrome-win")
        chrome_win_target2 = os.path.join(chromium_dir2, "chrome-win")
        
        # If targets already exist, remove them
        if os.path.exists(chrome_win_target1):
            shutil.rmtree(chrome_win_target1)
        if os.path.exists(chrome_win_target2):
            shutil.rmtree(chrome_win_target2)
        
        # Copy the browser files to both locations
        shutil.copytree(chrome_win_source, chrome_win_target1)
        shutil.copytree(chrome_win_source, chrome_win_target2)
        
        # Create a symbolic link from chrome.exe to headless_shell.exe in both locations
        chrome_exe1 = os.path.join(chrome_win_target1, "chrome.exe")
        headless_shell_exe1 = os.path.join(chrome_win_target1, "headless_shell.exe")
        
        chrome_exe2 = os.path.join(chrome_win_target2, "chrome.exe")
        headless_shell_exe2 = os.path.join(chrome_win_target2, "headless_shell.exe")
        
        # Copy chrome.exe to headless_shell.exe
        if os.path.exists(chrome_exe1) and not os.path.exists(headless_shell_exe1):
            shutil.copy2(chrome_exe1, headless_shell_exe1)
        
        if os.path.exists(chrome_exe2) and not os.path.exists(headless_shell_exe2):
            shutil.copy2(chrome_exe2, headless_shell_exe2)
        
        return True
    except Exception as e:
        print(f"Error copying browser: {e}")
        return False

def find_browser_zip():
    """Find the browser zip file in various possible locations."""
    # Get the directory of the executable
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        app_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check multiple possible locations
    possible_paths = [
        os.path.join(app_dir, "browser", "chromium-win64.zip"),
        os.path.join(app_dir, "chromium-win64.zip"),
        os.path.join(app_dir, "dist", "browser", "chromium-win64.zip"),
        os.path.join(app_dir, "dist_final", "browser", "chromium-win64.zip"),
        os.path.join(app_dir, "..", "browser", "chromium-win64.zip"),
        os.path.join(app_dir, "..", "dist", "browser", "chromium-win64.zip"),
        os.path.join(app_dir, "..", "dist_final", "browser", "chromium-win64.zip")
    ]
    
    # Check each path
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # If not found, return the default path (for later download)
    return os.path.join(app_dir, "browser", "chromium-win64.zip")

def main():
    """Main function."""
    try:
        # Get the directory of the executable
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            app_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Find the browser zip file
        browser_zip = find_browser_zip()
        extract_dir = os.path.join(app_dir, "browser", "extracted")
        
        # Set up Playwright browsers path
        playwright_dir = setup_playwright_browsers_path()
        
        # Check if the browser is already set up (check both possible locations)
        chrome_exe1 = os.path.join(playwright_dir, "chromium-1161", "chrome-win", "chrome.exe")
        chrome_exe2 = os.path.join(playwright_dir, "chromium_headless_shell-1161", "chrome-win", "chrome.exe")
        headless_shell_exe = os.path.join(playwright_dir, "chromium_headless_shell-1161", "chrome-win", "headless_shell.exe")
        
        if not (os.path.exists(chrome_exe1) or os.path.exists(chrome_exe2) or os.path.exists(headless_shell_exe)):
            # Show progress window
            root, update_progress = show_progress_window(
                "Unpacking Browser",
                "Unpacking Chromium browser. This may take a few minutes..."
            )
            
            # Extract the browser in a separate thread
            def extract_thread():
                try:
                    # Create the extraction directory if it doesn't exist
                    os.makedirs(extract_dir, exist_ok=True)
                    
                    # Check if browser zip exists, if not, download it
                    if not os.path.exists(browser_zip):
                        update_progress(0)
                        root.title("Downloading Browser")
                        label = root.winfo_children()[0]
                        label.config(text="Downloading Chromium browser. This may take a few minutes...")
                        
                        # Create the directory for the browser zip
                        os.makedirs(os.path.dirname(browser_zip), exist_ok=True)
                        
                        # Download the browser
                        download_success = download_chromium(browser_zip, update_progress)
                        
                        if not download_success:
                            messagebox.showerror(
                                "Error",
                                "Failed to download browser. Please check your internet connection and try again."
                            )
                            root.destroy()
                            sys.exit(1)
                    
                    # Extract the browser
                    update_progress(0)
                    root.title("Extracting Browser")
                    label = root.winfo_children()[0]
                    label.config(text="Extracting Chromium browser. This may take a few minutes...")
                    
                    success = extract_browser(browser_zip, extract_dir, update_progress)
                    
                    if success:
                        # Copy the browser to the Playwright directory
                        copy_success = copy_browser_to_playwright_dir(extract_dir, playwright_dir)
                        
                        if copy_success:
                            update_progress(100)
                            time.sleep(1)  # Give time to see 100%
                            root.destroy()
                        else:
                            messagebox.showerror(
                                "Error",
                                "Failed to copy browser files. Please try again."
                            )
                            root.destroy()
                            sys.exit(1)
                    else:
                        messagebox.showerror(
                            "Error",
                            "Failed to extract browser. Please try again."
                        )
                        root.destroy()
                        sys.exit(1)
                except Exception as e:
                    messagebox.showerror(
                        "Error",
                        f"An unexpected error occurred: {str(e)}"
                    )
                    root.destroy()
                    sys.exit(1)
            
            # Start the extraction thread
            threading.Thread(target=extract_thread, daemon=True).start()
            
            # Start the Tkinter main loop
            root.mainloop()
        
        # Launch the main application
        core_exe = os.path.join(app_dir, "USAGovScraper_core.exe")
        
        if os.path.exists(core_exe):
            subprocess.Popen([core_exe])
        else:
            # Try to find the core executable in other locations
            possible_core_paths = [
                os.path.join(app_dir, "USAGovScraper_core.exe"),
                os.path.join(app_dir, "dist", "USAGovScraper_core.exe"),
                os.path.join(app_dir, "..", "USAGovScraper_core.exe"),
                os.path.join(app_dir, "..", "dist", "USAGovScraper_core.exe")
            ]
            
            core_found = False
            for path in possible_core_paths:
                if os.path.exists(path):
                    subprocess.Popen([path])
                    core_found = True
                    break
            
            if not core_found:
                messagebox.showerror(
                    "Error",
                    f"Main application executable not found: {core_exe}"
                )
                sys.exit(1)
        
    except Exception as e:
        messagebox.showerror(
            "Error",
            f"An unexpected error occurred: {str(e)}"
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
