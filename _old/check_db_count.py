import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'client', 'courses.db'))

conn = None
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM courses")
    count = cursor.fetchone()[0]
    print(f"Total records in courses table: {count}")
except sqlite3.OperationalError as e:
    print(f"Error: {e}. Table 'courses' might not exist or database file is corrupted.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    if conn:
        conn.close()