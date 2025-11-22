#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para reparar el archivo CSV y asegurar que tenga las columnas correctas
"""

import os
import sys
import pandas as pd
import shutil
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def repair_csv_file(file_path):
    """
    Repara el archivo CSV asegurando que tenga las columnas sic_code y course_name
    
    Args:
        file_path: Ruta al archivo CSV
    
    Returns:
        bool: True si la reparación fue exitosa, False en caso contrario
    """
    try:
        # Verificar si el archivo existe
        if not os.path.exists(file_path):
            logger.error(f"El archivo no existe: {file_path}")
            return False
        
        # Crear una copia de respaldo
        backup_path = file_path + ".backup"
        shutil.copy2(file_path, backup_path)
        logger.info(f"Copia de respaldo creada en: {backup_path}")
        
        # Leer el archivo CSV
        df = pd.read_csv(file_path)
        
        # Mostrar información sobre el archivo original
        logger.info(f"Archivo CSV original: {file_path}")
        logger.info(f"Columnas originales: {df.columns.tolist()}")
        
        # Determinar qué columnas renombrar
        columns_to_rename = {}
        
        # Caso 1: Si tiene exactamente 'code' y 'course'
        if 'code' in df.columns and 'course' in df.columns:
            columns_to_rename = {'code': 'sic_code', 'course': 'course_name'}
        
        # Caso 2: Si tiene exactamente 'code' y 'course_name'
        elif 'code' in df.columns and 'course_name' in df.columns:
            columns_to_rename = {'code': 'sic_code'}
        
        # Caso 3: Si tiene 'sic_code' pero no 'course_name'
        elif 'sic_code' in df.columns and 'course_name' not in df.columns:
            # Buscar una columna que pueda ser course_name
            for col in df.columns:
                if col != 'sic_code' and col.lower().find('course') >= 0:
                    columns_to_rename = {col: 'course_name'}
                    break
            
            # Si no encontramos una columna adecuada, usar la segunda columna
            if 'course_name' not in columns_to_rename.values() and len(df.columns) >= 2:
                second_col = df.columns[1] if df.columns[0] == 'sic_code' else df.columns[1]
                columns_to_rename = {second_col: 'course_name'}
        
        # Caso 4: Si tiene 'course_name' pero no 'sic_code'
        elif 'course_name' in df.columns and 'sic_code' not in df.columns:
            # Buscar una columna que pueda ser sic_code
            for col in df.columns:
                if col != 'course_name' and (col.lower().find('code') >= 0 or col.lower().find('sic') >= 0):
                    columns_to_rename = {col: 'sic_code'}
                    break
            
            # Si no encontramos una columna adecuada, usar la primera columna
            if 'sic_code' not in columns_to_rename.values():
                first_col = df.columns[0]
                columns_to_rename = {first_col: 'sic_code'}
        
        # Caso 5: No tiene ninguna de las dos columnas
        elif 'sic_code' not in df.columns and 'course_name' not in df.columns:
            # Si tiene exactamente 2 columnas, asumir que la primera es sic_code y la segunda course_name
            if len(df.columns) == 2:
                columns_to_rename = {df.columns[0]: 'sic_code', df.columns[1]: 'course_name'}
            # Si tiene más de 2 columnas, intentar adivinar por nombres
            else:
                # Buscar columnas que puedan ser sic_code y course_name
                for col in df.columns:
                    if col.lower().find('code') >= 0 or col.lower().find('sic') >= 0:
                        columns_to_rename[col] = 'sic_code'
                    elif col.lower().find('course') >= 0 or col.lower().find('name') >= 0:
                        columns_to_rename[col] = 'course_name'
                
                # Si no encontramos ambas columnas, usar las dos primeras
                if 'sic_code' not in columns_to_rename.values():
                    columns_to_rename[df.columns[0]] = 'sic_code'
                if 'course_name' not in columns_to_rename.values() and len(df.columns) >= 2:
                    for col in df.columns:
                        if col not in columns_to_rename and columns_to_rename.get(col) != 'sic_code':
                            columns_to_rename[col] = 'course_name'
                            break
        
        # Renombrar las columnas
        if columns_to_rename:
            df = df.rename(columns=columns_to_rename)
            logger.info(f"Columnas renombradas: {columns_to_rename}")
        
        # Verificar que ahora tenemos las columnas necesarias
        missing_columns = []
        if 'sic_code' not in df.columns:
            missing_columns.append('sic_code')
        if 'course_name' not in df.columns:
            missing_columns.append('course_name')
        
        # Si todavía faltan columnas, crearlas
        if missing_columns:
            logger.warning(f"Aún faltan columnas: {missing_columns}")
            
            # Si falta sic_code, crear una columna con valores secuenciales
            if 'sic_code' in missing_columns:
                df['sic_code'] = [f"{i+1000}" for i in range(len(df))]
                logger.info("Creada columna 'sic_code' con valores secuenciales")
            
            # Si falta course_name, usar la primera columna que no sea sic_code
            if 'course_name' in missing_columns:
                for col in df.columns:
                    if col != 'sic_code':
                        df['course_name'] = df[col]
                        logger.info(f"Creada columna 'course_name' copiando valores de '{col}'")
                        break
                # Si no hay otras columnas, crear una con valores genéricos
                if 'course_name' not in df.columns:
                    df['course_name'] = [f"Curso {i+1}" for i in range(len(df))]
                    logger.info("Creada columna 'course_name' con valores genéricos")
        
        # Guardar el archivo reparado
        df.to_csv(file_path, index=False)
        
        # Mostrar información sobre el archivo reparado
        logger.info(f"Archivo CSV reparado: {file_path}")
        logger.info(f"Columnas finales: {df.columns.tolist()}")
        
        # Verificar que ahora tenemos las columnas necesarias
        if 'sic_code' in df.columns and 'course_name' in df.columns:
            logger.info("¡Reparación exitosa! El archivo ahora tiene las columnas 'sic_code' y 'course_name'")
            return True
        else:
            logger.error("La reparación falló. El archivo aún no tiene las columnas necesarias")
            return False
        
    except Exception as e:
        logger.error(f"Error al reparar el archivo CSV: {e}")
        return False

def main():
    """Función principal"""
    # Ruta predeterminada al archivo CSV
    default_path = os.path.join("data", "class5_course_list.csv")
    
    # Usar la ruta proporcionada como argumento o la predeterminada
    file_path = sys.argv[1] if len(sys.argv) > 1 else default_path
    
    logger.info(f"Reparando archivo CSV: {file_path}")
    
    # Reparar el archivo
    success = repair_csv_file(file_path)
    
    if success:
        logger.info("Reparación completada con éxito")
        print("\n¡REPARACIÓN EXITOSA!")
        print("El archivo CSV ahora tiene las columnas 'sic_code' y 'course_name'")
        print("Puedes ejecutar la aplicación principal ahora.")
    else:
        logger.error("Error durante la reparación")
        print("\n¡ERROR EN LA REPARACIÓN!")
        print("No se pudo reparar el archivo CSV.")
        print("Por favor, verifica el archivo manualmente.")

if __name__ == "__main__":
    main()
