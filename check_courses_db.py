import sqlite3, os

db = 'courses.db'
print(f"Exists: {os.path.exists(db)}, Size: {os.path.getsize(db)} bytes")
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", c.fetchall())
c.execute("SELECT COUNT(*) FROM courses")
print("Total rows:", c.fetchone()[0])
c.execute("SELECT * FROM courses LIMIT 5")
print("Sample:")
for row in c.fetchall():
    print(f"  {row}")
conn.close()
