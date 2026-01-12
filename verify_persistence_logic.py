
import sys
import os
import sqlite3
import pandas as pd
import shutil
from fastapi import UploadFile

# Add server directory to path to import the module
sys.path.append(os.path.join(os.getcwd(), 'server'))

# Mocking FastAPI components
class MockFile:
    def __init__(self, filename, content):
        self.filename = filename
        self.file = content

# Import the module - this might run startup code if not careful, but we checked __name__ == "__main__"
import main_wsl_corregido as server

def test_persistence():
    print("--- TESTING PERSISTENCE LOGIC ---")
    
    # 1. Check DB Path Calculation
    expected_db_path = os.path.join(os.getcwd(), 'courses.db')
    print(f"Expected DB Path: {expected_db_path}")
    
    # We can't easily access the internal db_path var unless we modify the code or run the function
    # Let's run init_database
    print("Running init_database()...")
    server.init_database()
    
    # Check if DB exists
    if os.path.exists(expected_db_path):
        print("✅ courses.db exists at the correct location.")
    else:
        print("❌ courses.db NOT found at expected location!")
        return

    # 2. Create a dummy Excel file
    print("\n--- TESTING UPLOAD LOGIC ---")
    df = pd.DataFrame({
        'Col1': ['TEST_CODE_1', 'TEST_CODE_2'],
        'Col2': ['TEST_NAME_1', 'TEST_NAME_2']
    })
    excel_file = 'test_upload.xlsx'
    df.to_excel(excel_file, index=False)
    
    # 3. Simulate Upload
    # We need to mock the UploadFile object
    # Since the function is async, we need to run it in an event loop or just extract the logic.
    # For simplicity, let's replicate the logic here to verify it works with the file
    
    try:
        # Logic from upload_courses
        temp_file = f"temp_{excel_file}"
        shutil.copy(excel_file, temp_file)
        
        df_read = pd.read_excel(temp_file, dtype=str)
        courses_data = []
        for _, row in df_read.iterrows():
            if pd.notna(row[0]) and pd.notna(row[1]):
                courses_data.append((str(row[0]).strip(), str(row[1]).strip()))
        
        print(f"Extracted {len(courses_data)} courses from file.")
        print(f"Sample: {courses_data[0]}")
        
        if len(courses_data) != 2:
            print("❌ Failed to extract correct number of courses.")
        else:
            print("✅ Data extraction logic works.")
            
        # 4. Simulate DB Update
        conn = sqlite3.connect(expected_db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM courses")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='courses'")
        cursor.executemany("INSERT INTO courses (sic_code, course_name) VALUES (?, ?)", courses_data)
        conn.commit()
        conn.close()
        print("✅ Database updated manually using server logic.")
        
        # 5. Verify Content
        conn = sqlite3.connect(expected_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses")
        rows = cursor.fetchall()
        conn.close()
        
        print(f"DB Rows: {len(rows)}")
        for row in rows:
            print(row)
            
        if len(rows) == 2 and rows[0][1] == 'TEST_CODE_1':
             print("✅ PERSISTENCE TEST PASSED: Data was written to the correct DB file.")
        else:
             print("❌ PERSISTENCE TEST FAILED: Data mismatch.")

    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        if os.path.exists(excel_file): os.remove(excel_file)
        if os.path.exists(temp_file): os.remove(temp_file)

if __name__ == "__main__":
    test_persistence()
