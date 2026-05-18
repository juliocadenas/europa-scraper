import requests
import json

base = "http://100.83.253.87:8001"

# 1. Estado detallado
r = requests.get(f"{base}/api/detailed_status", timeout=15, verify=False)
d = r.json()
courses = d.get("courses", {})

# Analizar calidad de resultados
zero_results = []
low_results = []  # 1-5
medium_results = []  # 6-50
high_results = []  # 51+
error_courses = []
completed_courses = []

for sic, c in courses.items():
    st = c.get("status", "?")
    if st in ["Error", "Fallido"]:
        error_courses.append((sic, c))
    elif st == "Completado":
        completed_courses.append((sic, c))

# De los completados, ver cuántos resultados encontró cada uno
result_distribution = {"0 resultados": 0, "1-5 resultados": 0, "6-20 resultados": 0, "21-50 resultados": 0, "51-200 resultados": 0, "200+ resultados": 0}
zero_detail = []

for sic, c in completed_courses:
    task = c.get("current_task", c.get("last_task", ""))
    # Extraer número de resultados del task
    import re
    match = re.search(r'Se encontraron (\d+) resultados', task)
    if match:
        n = int(match.group(1))
        if n == 0:
            result_distribution["0 resultados"] += 1
            zero_detail.append(sic)
        elif n <= 5:
            result_distribution["1-5 resultados"] += 1
        elif n <= 20:
            result_distribution["6-20 resultados"] += 1
        elif n <= 50:
            result_distribution["21-50 resultados"] += 1
        elif n <= 200:
            result_distribution["51-200 resultados"] += 1
        else:
            result_distribution["200+ resultados"] += 1
    else:
        result_distribution["0 resultados"] += 1

print("=" * 60)
print("CALIDAD DE RESULTADOS DEL SCRAPING")
print("=" * 60)
print(f"\nTotal cursos: {len(courses)}")
print(f"Completados: {len(completed_courses)}")
print(f"Con error: {len(error_courses)}")
print(f"\nDistribución de resultados (cursos completados):")
for cat, count in result_distribution.items():
    pct = count / len(completed_courses) * 100 if completed_courses else 0
    print(f"  {cat}: {count} ({pct:.1f}%)")

# Total de resultados encontrados
total_results = 0
for sic, c in completed_courses:
    task = c.get("current_task", c.get("last_task", ""))
    match = re.search(r'Se encontraron (\d+) resultados', task)
    if match:
        total_results += int(match.group(1))

print(f"\nTotal resultados encontrados: {total_results:,}")
print(f"Promedio por curso: {total_results/len(completed_courses):.1f}" if completed_courses else "")

# Cursos con más resultados
print("\n" + "=" * 60)
print("TOP 10 CURSOS CON MÁS RESULTADOS")
print("=" * 60)
course_results = []
for sic, c in completed_courses:
    task = c.get("current_task", c.get("last_task", ""))
    match = re.search(r'Se encontraron (\d+) resultados', task)
    n = int(match.group(1)) if match else 0
    name = c.get("name", "?")[:50]
    course_results.append((n, sic, name))

course_results.sort(key=lambda x: -x[0])
for n, sic, name in course_results[:10]:
    print(f"  {n:>5} resultados | SIC:{sic} | {name}")

# Cursos con 0 resultados (muestra)
print("\n" + "=" * 60)
print(f"CURSOS CON 0 RESULTADOS (muestra de 20 de {result_distribution['0 resultados']})")
print("=" * 60)
count = 0
for n, sic, name in course_results:
    if n == 0:
        print(f"  SIC:{sic} | {name}")
        count += 1
        if count >= 20:
            break

# Verificar archivos en results
print("\n" + "=" * 60)
print("ARCHIVOS EN SERVIDOR")
print("=" * 60)
r2 = requests.get(f"{base}/api/results_line_count", timeout=15, verify=False)
if r2.status_code == 200:
    d2 = r2.json()
    print(f"Total líneas: {d2.get('total_lines', 0):,}")
    print(f"Total archivos: {d2.get('total_files', 0)}")
    files = d2.get("files", [])
    if files:
        # Top 10 archivos más grandes
        files.sort(key=lambda x: -x.get("line_count", 0))
        print(f"\nTop 10 archivos más grandes:")
        for f in files[:10]:
            print(f"  {f.get('line_count', 0):>5} líneas | {f.get('name', '?')[:60]}")
