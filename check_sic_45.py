
import sqlite3
import os

def check_sic():
    db_path = 'courses.db'
    if not os.path.exists(db_path):
        print("Database not found.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check for exact match or starts with
        cursor.execute("SELECT * FROM courses WHERE sic_code = '45' OR sic_code LIKE '45%' LIMIT 5")
        results = cursor.fetchall()
        
        if results:
            print(f"Found {len(results)} courses matching '45':")
            for r in results:
                print(r)
        else:
            print("No courses found for SIC '45'.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_sic()
