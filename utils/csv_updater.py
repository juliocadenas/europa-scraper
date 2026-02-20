#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utilidades para manejo del CSV de cursos
"""

import csv
import os


class CSVUpdater:
    """Maneja actualizaciones del archivo class5_course_list.csv"""
    
    def __init__(self, csv_file=None):
        self.csv_file = csv_file or os.path.join("data", "class5_course_list.csv")
        
    def update_course_status(self, sic_code, status, server_info=""):
        """Actualiza el status y servidor de un curso específico por sic_code"""
        if not os.path.exists(self.csv_file):
            print(f"ERROR: Archivo CSV no encontrado: {self.csv_file}")
            return False
            
        try:
            # Leer todas las filas
            updated = False
            rows = []
            
            with open(self.csv_file, 'r', encoding='utf-8', newline='') as file:
                reader = csv.DictReader(file)
                header = reader.fieldnames
                rows = list(reader)
            
            # Buscar y actualizar la fila correspondiente
            for row in rows:
                if row['sic_code'].strip('"') == sic_code.strip('"'):
                    print(f"Actualizando curso: {row['sic_code']} - {row['course']}")
                    row['status'] = f'"{status}"'
                    row['server'] = f'"{server_info}"'
                    updated = True
                    break
                    
            if not updated:
                print(f"ADVERTENCIA: No se encontró el curso con sic_code: {sic_code}")
                return False
                
            # Escribir el archivo actualizado
            with open(self.csv_file, 'w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=header)
                writer.writeheader()
                writer.writerows(rows)
                
            print(f"CSV actualizado: {sic_code} -> status={status}, server={server_info}")
            return True
            
        except Exception as e:
            print(f"ERROR actualizando CSV: {e}")
            return False
            
    def update_range_status(self, from_sic, to_sic, status, server_info=""):
        """Actualiza el status y servidor de un rango de cursos"""
        if not os.path.exists(self.csv_file):
            print(f"ERROR: Archivo CSV no encontrado: {self.csv_file}")
            return False
            
        try:
            # Leer todas las filas
            updated_count = 0
            rows = []
            
            with open(self.csv_file, 'r', encoding='utf-8', newline='') as file:
                reader = csv.DictReader(file)
                header = reader.fieldnames
                rows = list(reader)
            
            # Actualizar todas las filas en el rango
            for row in rows:
                sic_code = row['sic_code'].strip('"')
                if from_sic <= sic_code <= to_sic:
                    print(f"Actualizando curso en rango: {sic_code} - {row['course']}")
                    row['status'] = f'"{status}"'
                    row['server'] = f'"{server_info}"'
                    updated_count += 1
                    
            if updated_count == 0:
                print(f"ADVERTENCIA: No se encontraron cursos en el rango {from_sic} a {to_sic}")
                return False
                
            # Escribir el archivo actualizado
            with open(self.csv_file, 'w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=header)
                writer.writeheader()
                writer.writerows(rows)
                
            print(f"Rango actualizado en CSV: {updated_count} cursos -> status={status}, server={server_info}")
            return True
            
        except Exception as e:
            print(f"ERROR actualizando rango en CSV: {e}")
            return False
            
    def get_course_info(self, sic_code):
        """Obtiene información de un curso específico"""
        if not os.path.exists(self.csv_file):
            return None
            
        try:
            with open(self.csv_file, 'r', encoding='utf-8', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['sic_code'].strip('"') == sic_code.strip('"'):
                        return row
            return None
        except Exception as e:
            print(f"ERROR leyendo CSV: {e}")
            return None