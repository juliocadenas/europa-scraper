import sqlite3
import json

def actualizar_codigo_desde_payload():
    """
    Extrae el valor de 'sic_code' del campo 'payload'
    y actualiza el campo 'codigo' en la tabla 'courses'.
    """
    try:
        # 1. Conexión a la base de datos
        conn = sqlite3.connect('course.db')
        cursor = conn.cursor()

        # 2. Seleccionar todas las filas de la tabla 'courses'
        cursor.execute("SELECT rowid, payload FROM courses")
        filas = cursor.fetchall()

        print(f"Se encontraron {len(filas)} registros para procesar.")

        for fila in filas:
            rowid, payload_str = fila

            # 3. Convertir la cadena de texto a un diccionario
            try:
                # Sanitizar la cadena para que sea un JSON válido
                payload_str_sanitized = payload_str.replace("'nan'", "None").replace("'", '"')
                payload_dict = json.loads(payload_str_sanitized)

                # 4. Obtener el valor de 'sic_code'
                sic_code = payload_dict.get('sic_code')

                if sic_code:
                    # 5. Actualizar el campo 'codigo' con el valor extraído
                    cursor.execute("UPDATE courses SET codigo = ? WHERE rowid = ?", (sic_code, rowid))
                    print(f"Fila con rowid {rowid} actualizada. sic_code extraído: {sic_code}")
                else:
                    print(f"Fila con rowid {rowid} no tiene 'sic_code'. No se actualizó el campo.")

            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error al procesar la fila con rowid {rowid}: {e}")
                print(f"Payload problemático: {payload_str}")

        # Guardar (commit) los cambios en la base de datos
        conn.commit()
        print("\nTodos los registros han sido procesados. Cambios guardados.")

    except sqlite3.Error as e:
        print(f"Error de SQLite: {e}")
    finally:
        # Cerrar la conexión
        if conn:
            conn.close()

# Llamar a la función para ejecutar el proceso
actualizar_codigo_desde_payload()