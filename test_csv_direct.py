#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico directo para verificar qué está leyendo pandas del CSV
"""
import pandas as pd
import csv
from tkinter import filedialog
import tkinter as tk

def test_csv_reading():
    root = tk.Tk()
    root.withdraw()
    
    print("=" * 60)
    print("DIAGNÓSTICO DE LECTURA CSV")
    print("=" * 60)
    
    filepath = filedialog.askopenfilename(
        title="Selecciona tu CSV problemático",
        filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx *.xls"), ("Todos", "*.*")]
    )
    
    if not filepath:
        print("No seleccionaste archivo")
        return
    
    print(f"\nArchivo: {filepath}\n")
    
    # Método 1: CSV reader (lo que debería funcionar)
    print("--- MÉTODO 1: csv.reader (Python puro) ---")
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i >= 3:
                break
            if len(row) >= 2:
                code = str(row[0])
                print(f"Fila {i+1}: '{code}' (len={len(code)}, repr={repr(code)})")
                # Mostrar bytes
                print(f"  Bytes: {code.encode('utf-8')}")
    
    # Método 2: Pandas con dtype=str
    print("\n--- MÉTODO 2: pandas con dtype=str ---")
    if filepath.endswith('.csv'):
        df = pd.read_csv(filepath, dtype=str)
    else:
        df = pd.read_excel(filepath, dtype=str)
    
    print(df.head(3))
    print(f"\nPrimera celda: '{df.iloc[0, 0]}'")
    print(f"Tipo: {type(df.iloc[0, 0])}")
    print(f"Repr: {repr(df.iloc[0, 0])}")
    
    # Método 3: Aplicar la sanitización
    print("\n--- MÉTODO 3: Aplicando sanitización ---")
    import re
    code_raw = str(df.iloc[0, 0])
    code_clean = code_raw.replace('\ufeff', '').strip()
    print(f"Antes: '{code_raw}'")
    print(f"Después de limpiar: '{code_clean}'")
    
    if re.match(r'^\d\.', code_clean):
        code_fixed = "0" + code_clean
        print(f"✅ MATCH! Corregido a: '{code_fixed}'")
    else:
        print(f"❌ NO MATCH con regex '^\\d\\.'")
        print(f"   Primer carácter: {repr(code_clean[0]) if code_clean else 'VACÍO'}")
    
    print("\n" + "=" * 60)
    input("Presiona ENTER para cerrar...")

if __name__ == "__main__":
    test_csv_reading()
