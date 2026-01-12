#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fix Browser
-----------
Este script crea el archivo headless_shell.exe que Playwright está buscando.
"""

import os
import shutil
import tempfile
import sys
import tkinter as tk
from tkinter import messagebox

def main():
    """Función principal para arreglar el navegador"""
    print("\n" + "=" * 70)
    print("ARREGLANDO NAVEGADOR PARA PLAYWRIGHT".center(70))
    print("=" * 70 + "\n")
    
    # Definir directorios
    temp_dir = tempfile.gettempdir()
    playwright_dir = os.path.join(temp_dir, "playwright_browsers")
    chromium_dir = os.path.join(playwright_dir, "chromium-1161", "chrome-win")
    headless_dir = os.path.join(playwright_dir, "chromium_headless_shell-1161", "chrome-win")
    
    # Verificar si el directorio de Chromium existe
    if not os.path.exists(chromium_dir):
        print(f"Error: No se encontró el directorio de Chromium en {chromium_dir}")
        print("El navegador no parece estar instalado correctamente.")
        return False
    
    # Verificar si chrome.exe existe
    chrome_exe = os.path.join(chromium_dir, "chrome.exe")
    if not os.path.exists(chrome_exe):
        print(f"Error: No se encontró chrome.exe en {chrome_exe}")
        print("El navegador no parece estar instalado correctamente.")
        return False
    
    # Crear directorio para headless_shell si no existe
    os.makedirs(headless_dir, exist_ok=True)
    
    # Copiar chrome.exe a headless_shell.exe
    headless_exe = os.path.join(headless_dir, "headless_shell.exe")
    try:
        shutil.copy2(chrome_exe, headless_exe)
        print(f"Se ha creado correctamente el archivo {headless_exe}")
        
        # Copiar también chrome.exe al mismo directorio
        chrome_exe_dest = os.path.join(headless_dir, "chrome.exe")
        shutil.copy2(chrome_exe, chrome_exe_dest)
        print(f"Se ha copiado también {chrome_exe_dest}")
        
        # Copiar DLLs y otros archivos necesarios
        for file in os.listdir(chromium_dir):
            if file.endswith(".dll") or file.endswith(".bin") or file.endswith(".pak") or file.endswith(".dat"):
                src = os.path.join(chromium_dir, file)
                dst = os.path.join(headless_dir, file)
                shutil.copy2(src, dst)
                print(f"Copiado archivo de soporte: {file}")
        
        # Crear subdirectorios necesarios
        for subdir in ["locales", "swiftshader"]:
            src_dir = os.path.join(chromium_dir, subdir)
            if os.path.exists(src_dir) and os.path.isdir(src_dir):
                dst_dir = os.path.join(headless_dir, subdir)
                if not os.path.exists(dst_dir):
                    os.makedirs(dst_dir, exist_ok=True)
                
                # Copiar archivos del subdirectorio
                for file in os.listdir(src_dir):
                    src_file = os.path.join(src_dir, file)
                    dst_file = os.path.join(dst_dir, file)
                    if os.path.isfile(src_file):
                        shutil.copy2(src_file, dst_file)
                        print(f"Copiado archivo de soporte en {subdir}: {file}")
        
        print("\n¡Arreglo completado con éxito!")
        print("El mensaje de advertencia sobre headless_shell.exe no debería aparecer más.")
        
        # Mostrar mensaje de éxito
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(
                "Arreglo Completado",
                "El navegador ha sido configurado correctamente.\nEl mensaje de advertencia no debería aparecer más."
            )
        except:
            pass
        
        return True
    except Exception as e:
        print(f"Error al copiar el archivo: {e}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        
        if not success:
            print("\nHubo errores durante el proceso. Revise los mensajes anteriores.")
        
        print("\nPresione Enter para salir...")
        input()
    except Exception as e:
        print(f"\nError inesperado: {e}")
        print("\nPresione Enter para salir...")
        input()
