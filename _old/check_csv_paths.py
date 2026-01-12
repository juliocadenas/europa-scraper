#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para verificar el formato del archivo CSV y mostrar sus columnas
"""

import os
import sys
import pandas as pd
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_csv_file(file_path):
    """
    Verifica el formato del archivo CSV y muestra sus columnas
    
    Args:
        file_path: Ruta al archivo CSV
    """
    try:
        # Verificar si el archivo existe
        if not os.path.exists(file_path):
            logger.error(f"El archivo no existe: {file_path}")
            return False
        
        # Leer el archivo CSV
        df = pd.read_csv(file_path)
        
        # Mostrar información sobre el archivo
        logger.info(f"Archivo CSV: {file_path}")
        logger.info(f"Número de filas: {len(df)}")
        logger.info(f"Número de columnas: {len(df.columns)}")
        logger.info(f"Columnas: {df.columns.tolist()}")
        
        # Mostrar las primeras filas
        logger.info("Primeras 5 filas:")
        for i, row in df.head().iterrows():
            logger.info(f"Fila {i+1}: {dict(row)}")
        
        # Verificar si tiene las columnas 'code' y 'course'
        if 'code' in df.columns and 'course' in df.columns:
            logger.info("El archivo tiene el formato esperado con columnas 'code' y 'course'")
            logger.info("Estas columnas se mapearán a 'sic_code' y 'course_name' respectivamente")
        else:
            logger.warning("El archivo no tiene el formato esperado (code, course)")
            logger.info("Columnas esperadas: 'code', 'course'")
            logger.info("Columnas encontradas: " + ", ".join([f"'{col}'" for col in df.columns]))
        
        return True
    
    except Exception as e:
        logger.error(f"Error al verificar el archivo CSV: {e}")
        return False

def main():
    """Función principal"""
    # Ruta predeterminada al archivo CSV
    default_path = os.path.join("data", "class5_course_list.csv")
    
    # Usar la ruta proporcionada como argumento o la predeterminada
    file_path = sys.argv[1] if len(sys.argv) > 1 else default_path
    
    logger.info(f"Verificando archivo CSV: {file_path}")
    
    # Verificar el archivo
    success = check_csv_file(file_path)
    
    if success:
        logger.info("Verificación completada con éxito")
    else:
        logger.error("Error durante la verificación")

if __name__ == "__main__":
    main()
