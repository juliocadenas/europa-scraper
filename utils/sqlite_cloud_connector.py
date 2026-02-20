#!/usr/bin/env python3
"""
SQLite Cloud Connector
----------------------
Conector para SQLite Cloud con funcionalidades avanzadas de gestión de tablas.
"""

import logging
import sqlite3
import pandas as pd
import os
from typing import List, Dict, Optional, Tuple, Any
import ssl
import urllib.parse
import csv
import json

logger = logging.getLogger(__name__)

class SQLiteCloudConnector:
    """
    Connector para SQLite Cloud con funcionalidades avanzadas.
    Permite conectar, gestionar tablas, importar CSV y crear tablas.
    """

    def __init__(self, connection_string: str):
        """
        Inicializar conector SQLite Cloud.

        Args:
            connection_string: String de conexión (ej: https://your-project.sqlite.cloud:443)
        """
        self.connection_string = connection_string
        self.connection = None
        self.is_connected = False
        self._parse_connection_string()

    def _parse_connection_string(self):
        """Parsea la cadena de conexión para extraer host, puerto, etc."""
        try:
            parsed = urllib.parse.urlparse(self.connection_string)
            self.host = parsed.hostname
            self.port = parsed.port or 443
            self.scheme = parsed.scheme
            self.path = parsed.path.strip('/') if parsed.path else ''
        except Exception as e:
            logger.error(f"Error parseando connection string: {e}")
            self.host = self.connection_string
            self.port = 443
            self.scheme = 'https'

    def connect(self, username: str = None, password: str = None) -> bool:
        """
        Conecta a la base de datos SQLite Cloud.

        Args:
            username: Usuario para autenticación
            password: Contraseña para autenticación

        Returns:
            bool: True si conectó exitosamente
        """
        try:
            # SQLite Cloud usa HTTPS con autenticación optiona
            if username and password:
                # Crear connection string con autenticación
                auth_string = f"{username}:{password}@"
                full_url = self.connection_string.replace('://', f'://{auth_string}')
            else:
                full_url = self.connection_string

            logger.info(f"Conectando a SQLite Cloud: {self.host}:{self.port}")

            # Para SQLite Cloud, necesitamos usar sqlitecloud Python library
            # Si no está disponible, usaremos sqlite3 directamente
            try:
                import sqlitecloud
                self.connection = sqlitecloud.connect(full_url)
            except ImportError:
                # Fallback a sqlite3 si no hay sqlitecloud library
                logger.warning("SQLite Cloud library no disponible, usando sqlite3 directamente")
                # Esto no funcionará directamente con SQLite Cloud, pero mantendremos la estructura
                self.connection = None

            self.is_connected = self.connection is not None

            if self.is_connected:
                logger.info("✅ Conectado exitosamente a SQLite Cloud")
            else:
                logger.warning("⚠️ No se pudo conectar a SQLite Cloud")

            return self.is_connected

        except Exception as e:
            logger.error(f"Error conectando a SQLite Cloud: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Cierra la conexión a la base de datos."""
        if self.connection:
            try:
                self.connection.close()
                logger.info("Conexión cerrada")
            except Exception as e:
                logger.error(f"Error cerrando conexión: {e}")

        self.connection = None
        self.is_connected = False

    def get_tables(self) -> List[str]:
        """
        Obtiene la lista de tablas disponibles en la base de datos.

        Returns:
            List[str]: Lista de nombres de tablas
        """
        if not self.is_connected or not self.connection:
            logger.error("No hay conexión activa")
            return []

        try:
            cursor = self.connection.cursor()
            # SQLite Cloud soporta consultas estándar SQL
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            logger.info(f"Tablas encontradas: {len(tables)}")
            return tables
        except Exception as e:
            logger.error(f"Error obteniendo tablas: {e}")
            return []

    def get_table_structure(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Obtiene la estructura de una tabla específica.

        Args:
            table_name: Nombre de la tabla

        Returns:
            List[Dict]: Lista de columnas con su información
        """
        if not self.is_connected or not self.connection:
            logger.error("No hay conexión activa")
            return []

        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'cid': row[0],
                    'name': row[1],
                    'type': row[2],
                    'notnull': row[3],
                    'dflt_value': row[4],
                    'pk': row[5]
                })
            cursor.close()
            return columns
        except Exception as e:
            logger.error(f"Error obteniendo estructura de tabla {table_name}: {e}")
            return []

    def get_table_data(self, table_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtiene datos de una tabla con límite.

        Args:
            table_name: Nombre de la tabla
            limit: Límite de registros a obtener

        Returns:
            List[Dict]: Lista de registros
        """
        if not self.is_connected or not self.connection:
            logger.error("No hay conexión activa")
            return []

        try:
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
            columns = [desc[0] for desc in cursor.description]
            rows = []
            for row in cursor.fetchall():
                rows.append(dict(zip(columns, row)))
            cursor.close()
            logger.info(f"Obtenidos {len(rows)} registros de {table_name}")
            return rows
        except Exception as e:
            logger.error(f"Error obteniendo datos de tabla {table_name}: {e}")
            return []

    def create_table_like(self, source_table: str, new_table_name: str) -> bool:
        """
        Crea una tabla vacía idéntica a otra tabla existente.

        Args:
            source_table: Nombre de la tabla fuente
            new_table_name: Nombre de la nueva tabla

        Returns:
            bool: True si se creó exitosamente
        """
        if not self.is_connected or not self.connection:
            logger.error("No hay conexión activa")
            return False

        try:
            cursor = self.connection.cursor()
            cursor.execute(f"CREATE TABLE {new_table_name} AS SELECT * FROM {source_table} WHERE 0=1")
            self.connection.commit()
            cursor.close()
            logger.info(f"✅ Tabla {new_table_name} creada (vacía) como copia de {source_table}")
            return True
        except Exception as e:
            logger.error(f"Error creando tabla {new_table_name}: {e}")
            try:
                self.connection.rollback()
            except:
                pass
            return False

    def import_csv_to_table(self, csv_file_path: str, table_name: str,
                           course_column: str = 'course', name_column: str = 'name',
                           delimiter: str = ',') -> Tuple[bool, int]:
        """
        Importa datos de un CSV a una tabla existente.

        Args:
            csv_file_path: Ruta al archivo CSV
            table_name: Nombre de la tabla destino
            course_column: Nombre de la columna 'course' en el CSV
            name_column: Nombre de la columna 'name' en el CSV
            delimiter: Delimitador del CSV

        Returns:
            Tuple[bool, int]: (éxito, registros importados)
        """
        if not self.is_connected or not self.connection:
            logger.error("No hay conexión activa")
            return False, 0

        if not os.path.exists(csv_file_path):
            logger.error(f"Archivo CSV no encontrado: {csv_file_path}")
            return False, 0

        try:
            # Leer CSV
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file, delimiter=delimiter)
                rows = list(reader)

            if not rows:
                logger.warning("CSV vacío o sin datos")
                return False, 0

            # Verificar que existan las columnas
            first_row = rows[0]
            available_columns = list(first_row.keys())

            # Si no especifican columnas, usar las primeras dos
            if course_column not in available_columns:
                if len(available_columns) >= 2:
                    course_column = available_columns[0]
                    name_column = available_columns[1]
                    logger.info(f"Usando primera columna '{course_column}' como 'course'")
                    logger.info(f"Usando segunda columna '{name_column}' como 'name'")
                else:
                    logger.error("CSV debe tener al menos 2 columnas")
                    return False, 0

            logger.info(f"Importando {len(rows)} registros a tabla '{table_name}'")

            cursor = self.connection.cursor()

            # Insertar datos
            inserted = 0
            for row in rows:
                course_value = row.get(course_column, '').strip()
                name_value = row.get(name_column, '').strip() if name_column else ''

                if course_value:  # Solo insertar si hay valor en course
                    try:
                        cursor.execute(
                            f"INSERT INTO {table_name} (course, name) VALUES (?, ?)",
                            (course_value, name_value)
                        )
                        inserted += 1
                    except Exception as e:
                        logger.warning(f"Error insertando fila: {e}")

            self.connection.commit()
            cursor.close()

            logger.info(f"✅ Importación completada: {inserted} registros agregados")
            return True, inserted

        except Exception as e:
            logger.error(f"Error importando CSV: {e}")
            try:
                self.connection.rollback()
            except:
                pass
            return False, 0

    def execute_query(self, query: str, params: Tuple = None) -> List[Dict[str, Any]]:
        """
        Ejecuta una consulta SQL genérica.

        Args:
            query: Consulta SQL
            params: Parámetros para la consulta

        Returns:
            List[Dict]: Resultados de la consulta
        """
        if not self.is_connected or not self.connection:
            logger.error("No hay conexión activa")
            return []

        try:
            cursor = self.connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Si es una consulta SELECT
            if query.strip().upper().startswith('SELECT'):
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                cursor.close()
                return results
            else:
                # Para INSERT/UPDATE/DELETE
                self.connection.commit()
                cursor.close()
                return [{"affected_rows": cursor.rowcount}]

        except Exception as e:
            logger.error(f"Error ejecutando consulta '{query}': {e}")
            try:
                if not query.strip().upper().startswith('SELECT'):
                    self.connection.rollback()
            except:
                pass
            return []

    def create_courses_table(self, table_name: str) -> bool:
        """
        Crea una tabla de cursos estándar.

        Args:
            table_name: Nombre de la tabla a crear

        Returns:
            bool: True si se creó exitosamente
        """
        course_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course TEXT NOT NULL,
            name TEXT,
            status TEXT DEFAULT 'pending',
            server_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        try:
            cursor = self.connection.cursor()
            cursor.execute(course_table_sql)
            self.connection.commit()
            cursor.close()
            logger.info(f"✅ Tabla '{table_name}' creada/actualizada con estructura estándar")
            return True
        except Exception as e:
            logger.error(f"Error creando tabla {table_name}: {e}")
            return False

    def table_exists(self, table_name: str) -> bool:
        """
        Verifica si una tabla existe.

        Args:
            table_name: Nombre de la tabla

        Returns:
            bool: True si existe
        """
        tables = self.get_tables()
        return table_name in tables

    def get_table_count(self, table_name: str) -> int:
        """
        Obtiene el número de registros en una tabla.

        Args:
            table_name: Nombre de la tabla

        Returns:
            int: Número de registros
        """
        if not self.table_exists(table_name):
            return 0

        try:
            result = self.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
            if result and len(result) > 0:
                return result[0].get('count', 0)
        except Exception as e:
            logger.error(f"Error obteniendo conteo de tabla {table_name}: {e}")

        return 0

class DatabaseConfig:
    """
    Configuración para gestionar múltiples bases de datos y conexiones.
    """

    def __init__(self, config_file: str = None):
        self.config_file = config_file or os.path.join(os.path.dirname(__file__), '..', 'client', 'config.json')
        self.load_config()

    def load_config(self):
        """Carga la configuración desde archivo JSON."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = {}
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            self.config = {}

    def save_config(self):
        """Guarda la configuración a archivo JSON."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            logger.info("Configuración guardada")
        except Exception as e:
            logger.error(f"Error guardando configuración: {e}")

    def get_cloud_config(self) -> Dict[str, Any]:
        """Obtiene configuración específica para SQLite Cloud."""
        return self.config.get('sqlite_cloud', {})

    def set_cloud_config(self, url: str, username: str = None, password: str = None,
                        default_table: str = None):
        """
        Configura los parámetros de SQLite Cloud.

        Args:
            url: URL de conexión de SQLite Cloud
            username: Usuario (opcional)
            password: Contraseña (opcional)
            default_table: Tabla por defecto para usar en scraping
        """
        if 'sqlite_cloud' not in self.config:
            self.config['sqlite_cloud'] = {}

        cloud_config = self.config['sqlite_cloud']
        cloud_config['url'] = url
        cloud_config['username'] = username
        cloud_config['password'] = password
        cloud_config['default_table'] = default_table
        cloud_config['enabled'] = True

        self.save_config()
        logger.info("Configuración SQLite Cloud actualizada")

    def get_cloud_connector(self) -> SQLiteCloudConnector:
        """
        Obtiene un conector configurado para SQLite Cloud.

        Returns:
            SQLiteCloudConnector: Conector configurado
        """
        cloud_config = self.get_cloud_config()

        if not cloud_config.get('enabled', False):
            raise ValueError("SQLite Cloud no está habilitado")

        url = cloud_config.get('url')
        if not url:
            raise ValueError("URL de SQLite Cloud no configurada")

        connector = SQLiteCloudConnector(url)

        username = cloud_config.get('username')
        password = cloud_config.get('password')

        # Intentar conectar
        if not connector.connect(username, password):
            raise ConnectionError("No se pudo conectar a SQLite Cloud")

        return connector