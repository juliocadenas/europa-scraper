
import requests
import os
import csv

# Crear un CSV de prueba
csv_file = 'test_courses.csv'
with open(csv_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['sic_code', 'course_name'])
    writer.writerow(['999.1', 'TEST COURSE 1'])
    writer.writerow(['999.2', 'TEST COURSE 2'])

url = 'http://localhost:8001/upload_courses'
files = {'file': open(csv_file, 'rb')}

try:
    print(f"Uploading {csv_file} to {url}...")
    response = requests.post(url, files=files)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("Upload successful!")
        
        # Verificar con get_all_courses
        print("Verifying with /get_all_courses...")
        r = requests.get('http://localhost:8001/get_all_courses')
        data = r.json()
        print(f"Courses count: {len(data)}")
        print("Courses:", data)
    else:
        print("Upload failed.")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    files['file'].close()
    if os.path.exists(csv_file):
        os.remove(csv_file)
