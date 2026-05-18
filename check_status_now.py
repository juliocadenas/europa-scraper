import requests
import json

base = "http://100.83.253.87:8001"

# 1. Estado detallado
print("=" * 60)
print("ESTADO DEL SERVIDOR")
print("=" * 60)
r = requests.get(f"{base}/api/detailed_status", timeout=15, verify=False)
d = r.json()
print(f"is_running: {d.get('is_running')}")
print(f"start_time: {d.get('start_time')}")
print(f"accumulated_time: {d.get('accumulated_time')}s")
print(f"csv_total: {d.get('csv_total')}")

workers = d.get("workers", {})
courses = d.get("courses", {})
print(f"\nWorkers: {len(workers)}")
print(f"Courses: {len(courses)}")

# Contar por estado
statuses = {}
for sic, c in courses.items():
    st = c.get("status", "?")
    statuses[st] = statuses.get(st, 0) + 1
print(f"\nDistribución de cursos:")
for st, count in sorted(statuses.items(), key=lambda x: -x[1]):
    print(f"  {st}: {count}")

# Workers activos vs idle
active_w = 0
idle_w = 0
for wid, w in workers.items():
    if not isinstance(w, dict):
        continue
    if w.get("status") == "Idle":
        idle_w += 1
    else:
        active_w += 1
print(f"\nWorkers activos: {active_w}, idle: {idle_w}")

# 2. Workers con detalles
print("\n" + "=" * 60)
print("DETALLE DE WORKERS")
print("=" * 60)
for wid, w in sorted(workers.items(), key=lambda x: x[0]):
    if not isinstance(w, dict):
        continue
    status = w.get("status", "?")
    task = w.get("current_task", "?")
    prog = w.get("progress", 0)
    urls = w.get("urls_scraped", 0)
    saved = w.get("contents_saved", 0)
    print(f"  {wid}: status={status} | task={task[:60]} | prog={prog}% | urls={urls} | saved={saved}")

# 3. Cursos en proceso
print("\n" + "=" * 60)
print("CURSOS EN PROCESO (Procesando)")
print("=" * 60)
processing = [(sic, c) for sic, c in courses.items() if c.get("status") == "Procesando"]
for sic, c in processing[:20]:
    name = c.get("name", "?")[:50]
    prog = c.get("progress", 0)
    worker = c.get("worker_id", "?")
    print(f"  SIC:{sic} | {name} | Worker:{worker} | {prog}%")
if not processing:
    print("  (Ninguno)")

# 4. Últimos eventos
print("\n" + "=" * 60)
print("ÚLTIMOS 20 EVENTOS")
print("=" * 60)
r2 = requests.get(f"{base}/api/events?min_id=0", timeout=10, verify=False)
if r2.status_code == 200:
    events = r2.json().get("events", [])
    for ev in events[-20:]:
        ts = ev.get("timestamp", "")[11:19]
        src = ev.get("source", "?")
        typ = ev.get("type", "?")
        msg = ev.get("message", "")[:80]
        print(f"  [{ts}] {src} ({typ}): {msg}")
else:
    print(f"  Error: {r2.status_code}")

# 5. Cursos con error
print("\n" + "=" * 60)
print("CURSOS CON ERROR")
print("=" * 60)
errors = [(sic, c) for sic, c in courses.items() if c.get("status") in ["Error", "Fallido"]]
for sic, c in errors[:10]:
    name = c.get("name", "?")[:50]
    err = c.get("error", c.get("last_error", "N/A"))[:80]
    print(f"  SIC:{sic} | {name} | Error: {err}")
if not errors:
    print("  (Ninguno)")

# 6. Cola pendiente
print("\n" + "=" * 60)
print("CURSOS PENDIENTES EN COLA")
print("=" * 60)
pending = [(sic, c) for sic, c in courses.items() if c.get("status") == "Pendiente"]
print(f"  Total pendientes: {len(pending)}")
if pending:
    # Mostrar primeros 5
    for sic, c in pending[:5]:
        name = c.get("name", "?")[:50]
        print(f"  SIC:{sic} | {name}")
    if len(pending) > 5:
        print(f"  ... y {len(pending) - 5} más")
