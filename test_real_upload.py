
import requests
import os
import pandas as pd

def test_real_upload():
    # 1. Create a dummy Excel file that mimics what a user might upload
    # The user said "columna 1 corresponda el codigo del curso y la columna 2 al nombre del curso"
    # Let's create a file with headers and one without, just in case, but the code uses pandas with header=0 by default usually.
    # My server code uses pd.read_excel(temp_file, dtype=str) which assumes header=0.
    
    print("Creating test Excel file...")
    df = pd.DataFrame({
        'Codigo': ['TEST_REAL_1', 'TEST_REAL_2'],
        'Nombre': ['Real Course 1', 'Real Course 2']
    })
    filename = 'real_upload_test.xlsx'
    df.to_excel(filename, index=False)
    
    url = 'http://localhost:8001/upload_courses'
    
    try:
        print(f"Attempting to upload {filename} to {url}...")
        with open(filename, 'rb') as f:
            files = {'file': (filename, f)}
            response = requests.post(url, files=files, timeout=10)
            
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("Upload successful according to server.")
            
            # Verify with get_all_courses
            print("Verifying with /get_all_courses...")
            r = requests.get('http://localhost:8001/get_all_courses')
            courses = r.json()
            print(f"Courses in DB: {len(courses)}")
            print(courses)
            
            found = any(c['sic_code'] == 'TEST_REAL_1' for c in courses)
            if found:
                print("✅ SUCCESS: Uploaded data found in DB.")
            else:
                print("❌ FAILURE: Uploaded data NOT found in DB.")
        else:
            print("❌ FAILURE: Server returned error.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_real_upload()
