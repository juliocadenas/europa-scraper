#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build script for the Europa Scraper Client
"""

import os
import subprocess
import sys
import shutil

def build_client():
    """Compiles the client into a single executable."""
    print("--- Building Europa Scraper Client ---")

    # --- Configuration ---
    script_to_compile = os.path.join("client", "main.py")
    executable_name = "EuropaScraperClient"
    dist_path = "dist"
    build_path = "build_client"

    # --- PyInstaller Command ---
    command = [
        sys.executable, "-m", "PyInstaller",
        "--name", executable_name,
        "--onefile",
        "--windowed", # Use --console=true for debugging
        f"--distpath={dist_path}",
        f"--workpath={build_path}",
        "--hidden-import", "requests",
        script_to_compile
    ]

    print(f"Running command: {' '.join(command)}")

    # --- Execution ---
    try:
        subprocess.run(command, check=True, text=True, capture_output=True)
        print("\nClient build successful!")
        print(f"Executable created at: {os.path.join(dist_path, f'{executable_name}.exe')}")
    except subprocess.CalledProcessError as e:
        print("\n--- Build Failed ---")
        print(f"Error during client compilation:")
        print(e.stdout)
        print(e.stderr)
        return False
    finally:
        # Clean up build directory
        if os.path.exists(build_path):
            print(f"Cleaning up build directory: {build_path}")
            shutil.rmtree(build_path)
        # Clean up .spec file
        spec_file = f"{executable_name}.spec"
        if os.path.exists(spec_file):
            os.remove(spec_file)

    return True

if __name__ == "__main__":
    if not build_client():
        sys.exit(1)
