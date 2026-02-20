#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build script for the Europa Scraper Server (Bulletproof Version)
This script manually generates the .spec file to ensure maximum compatibility and avoid CLI tool errors.
"""

import os
import subprocess
import sys
import shutil

def build_server():
    """Compiles the server by manually creating a .spec file and then building from it."""
    print("--- Building Europa Scraper Server (Bulletproof Mode) ---")

    # --- Configuration ---
    script_to_compile = os.path.join("server", "main.py")
    executable_name = "EuropaScraperServer"
    dist_path = "dist"
    build_path = "build_server"
    spec_file = f"{executable_name}.spec"

    # --- Stage 1: Manually create the .spec file content ---
    print("\n--- Stage 1: Creating .spec file content ---")
    playwright_browsers_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'ms-playwright')
    # Ensure path uses forward slashes for .spec file compatibility
    playwright_browsers_path_for_spec = playwright_browsers_path.replace('\\', '/')
    script_path_for_spec = script_to_compile.replace('\\', '/')

    hidden_imports_list = ['uvicorn', 'fastapi', 'pydantic', 'playwright']
    # Use repr() to get a valid Python string representation of the list
    hidden_imports_str = repr(hidden_imports_list)

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-\n\nblock_cipher = None\n
a = Analysis(
    ['{script_path_for_spec}'],
    pathex=[],
    binaries=[],
    datas=[('{playwright_browsers_path_for_spec}', 'ms-playwright'), ('courses.db', '.')],
    hiddenimports={hidden_imports_str},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{executable_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{executable_name}'
)
"""

    try:
        with open(spec_file, 'w') as f:
            f.write(spec_content)
        print(".spec file created successfully.")
    except Exception as e:
        print(f"\n--- Build Failed: Could not write .spec file: {e} ---")
        return False

    # --- Stage 2: Build the executable from the .spec file ---
    print(f"\n--- Stage 2: Building executable from {spec_file} ---")
    build_command = [
        sys.executable, "-m", "PyInstaller",
        spec_file,
        f"--distpath={dist_path}",
        f"--workpath={build_path}",
        "--noconfirm"
    ]

    print(f"Running command: {' '.join(build_command)}")

    try:
        process = subprocess.Popen(build_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        for line in iter(process.stdout.readline, ''):
            print(line, end='')
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, build_command)

        print("\nServer build successful!")
        # PyInstaller creates a directory for --onefile builds now, not a direct .exe
        print(f"Executable created at: {os.path.join(dist_path, executable_name)}")
    except subprocess.CalledProcessError as e:
        print(f"\n--- Build Failed: Error during server compilation ---")
        return False
    except Exception as e:
        print(f"\n--- Build Failed: An unexpected error occurred: {e} ---")
        return False
    finally:
        # --- Clean up ---
        print("\n--- Cleaning up temporary files ---")
        if os.path.exists(build_path):
            print(f"Removing build directory: {build_path}")
            shutil.rmtree(build_path)
        if os.path.exists(spec_file):
            print(f"Removing spec file: {spec_file}")
            os.remove(spec_file)

    return True

if __name__ == "__main__":
    if not build_server():
        sys.exit(1)
