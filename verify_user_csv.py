
import tkinter as tk
from tkinter import filedialog
import os

def check_csv_content():
    root = tk.Tk()
    root.withdraw()

    print("Por favor, selecciona tu archivo CSV o Excel...")
    filepath = filedialog.askopenfilename(
        title="SELECCIONA EL ARCHIVO QUE DICES QUE TIENE EL VIDEO",
        filetypes=[("Archivos", "*.csv *.xlsx *.xls")]
    )

    if not filepath:
        print("No seleccionaste nada.")
        return

    print(f"\nAnalizando archivo: {filepath}\n")
    print("-" * 50)

    if filepath.endswith('.csv'):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            # Leer primeras 5 lineas
            lines = [f.readline().strip() for _ in range(5)]
            for i, line in enumerate(lines):
                print(f"Línea {i+1} (RAW): {line}")
                
                # Check for 01.0
                if "01.0" in line:
                    print("   -> DETECTADO '01.0' (El archivo está BIEN)")
                elif line.startswith("1.0") or ",1.0" in line:
                    print("   -> DETECTADO '1.0' (El archivo tiene el cero comido!!)")
    else:
        import pandas as pd
        try:
            # Leer con mi fix
            df = pd.read_excel(filepath, dtype=str)
            print("Datos leídos con dtype=str (Mi arreglo):\n")
            print(df.iloc[:5, :2]) # Primeras 5 filas, 2 columnas
            
            val = str(df.iloc[0, 0])
            print(f"\nValor en la primera fila, primera columna: '{val}'")
        except Exception as e:
            print(f"Error leyendo Excel: {e}")

    print("-" * 50)
    print("\nSi arriba ves '01.0' y en la APP ves '1.0' -> ESTÁS USANDO LA APP VIEJA.")
    print("Si arriba ves '1.0' -> TU ARCHIVO ESTÁ MAL GENERADO POR EXCEL.")
    
    input("\nPresiona ENTER para cerrar...")

if __name__ == "__main__":
    check_csv_content()
