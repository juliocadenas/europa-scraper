#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test directo del código de lectura Excel
"""
import pandas as pd
from tkinter import filedialog
import tkinter as tk

print("=" * 60)
print("TEST DIRECTO DEL CÓDIGO DE LECTURA")
print("=" * 60)

root = tk.Tk()
root.withdraw()

filepath = filedialog.askopenfilename(
    title="Selecciona tu archivo Excel/CSV",
    filetypes=[("Excel", "*.xlsx *.xls"), ("CSV", "*.csv"), ("Todos", "*.*")]
)

if not filepath:
    print("No seleccionaste archivo")
    exit()

print(f"\nArchivo: {filepath}\n")

# EXACTAMENTE el código que está en scraper_gui.py línea 979-999
if filepath.endswith(('.xlsx', '.xls')):
    print("--- MÉTODO: pd.read_excel con dtype=str, header=None ---")
    df = pd.read_excel(filepath, dtype=str, header=None)
    print(f"DataFrame shape: {df.shape}")
    print(f"Primeras 3 filas del DataFrame:")
    print(df.head(3))
    print()
    
    if len(df.columns) >= 2:
        col0 = df.iloc[:, 0].tolist()
        col1 = df.iloc[:, 1].tolist()
        
        print(f"Primera celda de col0: '{col0[0]}'")
        print(f"Tipo: {type(col0[0])}")
        print(f"Repr: {repr(col0[0])}")
        print()
        
        courses_data = [
            (str(code), str(name)) 
            for code, name in zip(col0, col1) 
            if code and name and str(code) != 'nan' and str(name) != 'nan'
        ]
        
        print(f"Primeros 5 resultados de courses_data:")
        for i, (code, name) in enumerate(courses_data[:5]):
            print(f"  {i+1}. '{code}' - '{name}'")
else:
    # CSV
    print("--- MÉTODO: csv.reader ---")
    import csv
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        courses_data = []
        for row in reader:
            if len(row) >= 2 and row[0] and row[1]:
                courses_data.append((str(row[0]), str(row[1])))
    
    print(f"Primeros 5 resultados de courses_data:")
    for i, (code, name) in enumerate(courses_data[:5]):
        print(f"  {i+1}. '{code}' - '{name}'")


print("\n" + "=" * 60)
input("Presiona ENTER para cerrar...")
