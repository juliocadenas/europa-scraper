import os
import sys
import sqlite3
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

class SQLiteHandler:
    """
    Maneja la conexión y las operaciones con la base de datos SQLite.
    """
    def __init__(self, db_path: str = "courses.db"):
        # Determine the correct path for the database when running as a bundled executable
        if getattr(sys, 'frozen', False):
            # If running as a PyInstaller bundle, the database should be in sys._MEIPASS
            base_path = sys._MEIPASS
        else:
            # If running as a script, the database is relative to the script's location
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.db_path = os.path.join(base_path, db_path)
        logger.info(f"SQLiteHandler inicializado con base de datos: {self.db_path}")
        self.create_table_if_not_exists()

    def create_table_if_not_exists(self):
        """Crea la tabla 'courses' si no existe y maneja la migración del esquema."""
        conn = None
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # 1. Verificar si la tabla 'courses' existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='courses';")
            table_exists = cursor.fetchone()

            if not table_exists:
                # La tabla no existe, la creamos con el nuevo esquema
                cursor.execute("""
                CREATE TABLE courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sic_code TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    status TEXT,
                    server TEXT
                )
                """)
                logger.info("Tabla 'courses' creada con el nuevo esquema.")
                conn.commit()
                return

            # 2. La tabla existe, verificar el esquema para una posible migración
            cursor.execute("PRAGMA table_info(courses);")
            columns_info = {info[1]: info for info in cursor.fetchall()}

            # Si las columnas 'course' o 'name' existen, se necesita migración
            if 'course' in columns_info or 'name' in columns_info:
                logger.info("Detectado esquema antiguo. Iniciando migración de la tabla 'courses'...")

                # 3. Renombrar tabla antigua
                cursor.execute("ALTER TABLE courses RENAME TO courses_old;")

                # 4. Crear tabla nueva con el esquema correcto
                cursor.execute("""
                CREATE TABLE courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sic_code TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    status TEXT,
                    server TEXT
                )
                """)

                # 5. Copiar datos, mapeando columnas antiguas a nuevas
                old_columns = columns_info.keys()
                id_col = 'id'
                sic_col = 'course' if 'course' in old_columns else 'sic_code'
                name_col = 'name' if 'name' in old_columns else 'course_name'
                status_col = 'status'
                
                # Manejar el caso en que la columna 'server' no exista en la tabla antigua
                server_col = 'server' if 'server' in old_columns else '""' 

                copy_query = f"""
                INSERT INTO courses (id, sic_code, course_name, status, server)
                SELECT {id_col}, {sic_col}, {name_col}, {status_col}, {server_col} FROM courses_old;
                """
                cursor.execute(copy_query)
                logger.info("Datos copiados al nuevo esquema de tabla.")

                # 6. Eliminar tabla antigua
                cursor.execute("DROP TABLE courses_old;")
                logger.info("Tabla antigua 'courses_old' eliminada.")
                
                conn.commit()
                logger.info("Migración de la tabla 'courses' completada exitosamente.")
            else:
                logger.info("El esquema de la tabla 'courses' ya está actualizado.")

        except Exception as e:
            logger.error(f"Error al crear/migrar la tabla 'courses': {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def _connect(self):
        """Establece una conexión con la base de datos."""
        return sqlite3.connect(self.db_path)

    def load_course_data(self) -> bool:
        """
        Carga los datos del curso desde la base de datos SQLite.
        Este método mantiene compatibilidad con la interfaz del CSVHandler.
        
        Returns:
            bool: True si la conexión fue exitosa, False en caso contrario
        """
        try:
            # Verificar que la conexión funciona
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM courses")
            count = cursor.fetchone()[0]
            conn.close()
            
            logger.info(f"Conexión exitosa a la base de datos SQLite. Total de cursos: {count}")
            return True
            
        except Exception as e:
            logger.error(f"Error al conectar con la base de datos SQLite: {e}")
            return False

    def get_table_schema(self, table_name: str) -> List[str]:
        """
        Obtiene el esquema (nombres de columnas) de una tabla.
        
        Args:
            table_name: Nombre de la tabla.
            
        Returns:
            Lista de nombres de columnas.
        """
        conn = None
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            return [row[1] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo esquema de la tabla {table_name}: {e}")
            return []
        finally:
            if conn:
                conn.close()
        """
        Obtiene el esquema (nombres de columnas) de una tabla.
        
        Args:
            table_name: Nombre de la tabla.
            
        Returns:
            Lista de nombres de columnas.
        """
        conn = None
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            return [row[1] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo esquema de la tabla {table_name}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_detailed_sic_codes_with_courses(self) -> List[Tuple[str, str, str, str]]:
        """
        Obtiene todos los códigos SIC detallados con sus nombres de curso, estado y servidor.
        
        Returns:
            List[Tuple[str, str, str, str]]: Lista de tuplas (sic_code, course_name, status, server)
        """
        conn = None
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            # Verificar el esquema de la tabla
            schema = self.get_table_schema('courses')
            
            # Construir la consulta dinámicamente
            query = "SELECT sic_code, course_name, status"
            if 'server' in schema:
                query += ", server"
            query += " FROM courses"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                sic_code = row[0] if row[0] is not None else ""
                course_name = row[1] if row[1] is not None else ""
                status = row[2] if row[2] is not None else ""
                server = ""
                if 'server' in schema and len(row) > 3 and row[3] is not None:
                    server = row[3]
                
                result.append((sic_code, course_name, status, server))
            
            logger.info(f"TOTAL de códigos SIC con nombres de curso cargados desde SQLite: {len(result)}")
            return result
        except sqlite3.OperationalError as e:
            logger.error(f"Error de operación en la base de datos: {e}. Asegúrese de que la tabla 'courses' y las columnas 'sic_code', 'course_name', 'status' existan.")
            return []
        except Exception as e:
            logger.error(f"Error obteniendo códigos SIC detallados desde SQLite: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def update_course_status(self, sic_code: str, course_name: str, status: str, server_info: Optional[str] = None) -> bool:
        """
        Actualiza el estado de un curso en la base de datos SQLite.

        Args:
            sic_code: Código SIC del curso.
            course_name: Nombre del curso.
            status: Nuevo estado del curso ("procesando", "procesado").
            server_info: IP del servidor que procesa el curso.

        Returns:
            True si la actualización fue exitosa, False en caso contrario.
        """
        conn = None
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            schema = self.get_table_schema('courses')
            
            update_query = "UPDATE courses SET status = ?"
            params = [status]
            
            if 'server' in schema and server_info is not None:
                update_query += ", server = ?"
                params.append(server_info)
            
            update_query += " WHERE sic_code = ? AND course_name = ?"
            params.extend([sic_code, course_name])
            
            cursor.execute(update_query, tuple(params))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Estado del curso '{sic_code} - {course_name}' actualizado a '{status}' en el servidor '{server_info}'.")
                return True
            else:
                logger.warning(f"No se encontró el curso '{sic_code} - {course_name}' para actualizar el estado en SQLite.")
                return False
        except Exception as e:
            logger.error(f"Error al actualizar el estado del curso en SQLite: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def update_range_status(self, courses_to_update: List[Tuple[str, str]], status: str, server_info: str) -> bool:
        """
        Actualiza el estado de un rango de cursos en una sola operación en la base de datos SQLite.

        Args:
            courses_to_update: Lista de tuplas (sic_code, course_name) para actualizar.
            status: Nuevo estado para los cursos.
            server_info: Información del servidor.

        Returns:
            True si la actualización fue exitosa, False en caso contrario.
        """
        conn = None
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            schema = self.get_table_schema('courses')
            
            updated_count = 0
            for sic_code, course_name in courses_to_update:
                query = "UPDATE courses SET status = ?"
                params = [status]
                
                if 'server' in schema:
                    query += ", server = ?"
                    params.append(server_info)
                
                query += " WHERE sic_code = ? AND course_name = ?"
                params.extend([sic_code, course_name])
                
                cursor.execute(query, tuple(params))
                updated_count += cursor.rowcount
            
            conn.commit()
            
            if updated_count > 0:
                logger.info(f"{updated_count} cursos actualizados a '{status}' en el servidor '{server_info}' en SQLite.")
                return True
            else:
                logger.warning("No se encontraron cursos para actualizar en el rango especificado en SQLite.")
                return False
        except Exception as e:
            logger.error(f"Error masivo al actualizar el estado de los cursos en SQLite: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_all_courses(self) -> List[Tuple[str, str]]:
        """
        Obtiene todos los cursos de la base de datos como lista de tuplas (sic_code, course_name).
        
        Returns:
            List[Tuple[str, str]]: Lista de tuplas (sic_code, course_name)
        """
        conn = None
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            cursor.execute("SELECT sic_code, course_name FROM courses ORDER BY sic_code")
            rows = cursor.fetchall()
            
            # Convertir a lista de tuplas (sic_code, course_name)
            courses = [(row[0] if row[0] is not None else "",
                       row[1] if row[1] is not None else "") for row in rows]
            
            logger.info(f"Obtenidos {len(courses)} cursos desde la base de datos SQLite")
            return courses
            
        except Exception as e:
            logger.error(f"Error obteniendo todos los cursos desde SQLite: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def clear_courses_table(self) -> bool:
        """
        Limpia completamente la tabla de cursos.
        
        Returns:
            True si la operación fue exitosa, False en caso contrario.
        """
        conn = None
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM courses")
            conn.commit()
            
            logger.info("Tabla 'courses' limpiada exitosamente.")
            return True
            
        except Exception as e:
            logger.error(f"Error limpiando la tabla 'courses': {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def insert_courses(self, courses: List[Tuple[str, str]]) -> bool:
        """
        Inserta múltiples cursos en la base de datos.
        
        Args:
            courses: Lista de tuplas (sic_code, course_name) para insertar.
            
        Returns:
            True si la inserción fue exitosa, False en caso contrario.
        """
        conn = None
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            # Preparar datos para inserción masiva
            courses_to_insert = []
            for sic_code, course_name in courses:
                # Asegurarse de que los valores no sean None
                sic_code = sic_code if sic_code is not None else ""
                course_name = course_name if course_name is not None else ""
                courses_to_insert.append((sic_code, course_name))
            
            cursor.executemany(
                "INSERT INTO courses (sic_code, course_name) VALUES (?, ?)",
                courses_to_insert
            )
            conn.commit()
            
            logger.info(f"Insertados {len(courses_to_insert)} cursos en la base de datos SQLite.")
            return True
            
        except Exception as e:
            logger.error(f"Error insertando cursos en SQLite: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()