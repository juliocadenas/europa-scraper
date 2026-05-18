import requests
r = requests.get('http://100.83.253.87:8001/api/detailed_status', timeout=10, verify=False)
d = r.json()
csv_total = d.get("csv_total")
is_running = d.get("is_running")
workers = d.get("workers", {})
courses = d.get("courses", {})
print(f"csv_total: {csv_total}")
print(f"is_running: {is_running}")
print(f"workers: {len(workers)}")
print(f"courses: {len(courses)}")

# Contar completados, procesando, pendientes, fallidos
completed = 0
processing = 0
pending = 0
failed = 0
for sic, c in courses.items():
    st = c.get("status", "")
    if st == "Completado":
        completed += 1
    elif st == "Procesando":
        processing += 1
    elif st == "Pendiente":
        pending += 1
    elif st in ["Error", "Fallido"]:
        failed += 1

print(f"Completados: {completed}")
print(f"Procesando: {processing}")
print(f"Pendientes: {pending}")
print(f"Fallidos: {failed}")

# Verificar archivos en results
r2 = requests.get('http://100.83.253.87:8001/api/results_line_count', timeout=10, verify=False)
if r2.status_code == 200:
    d2 = r2.json()
    print(f"results_line_count total: {d2.get('total_lines')}")
    print(f"results_line_count files: {d2.get('total_files')}")
