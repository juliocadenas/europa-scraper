
import sqlite3
import os

db_path = 'courses.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit()

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM courses")
    count = cursor.fetchone()[0]
    print(f"Total rows in courses table: {count}")
    
    cursor.execute("SELECT * FROM courses LIMIT 5")
    rows = cursor.fetchall()
    print("First 5 rows:")
    for row in rows:
        print(row)
    conn.close()
except Exception as e:
    print(f"Error reading database: {e}")
