import json

with open('C:/Temp/status.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

cs = d.get('course_states', {})
ws = d.get('worker_states', {})

pending  = [v for v in cs.values() if v.get('status') == 'Pendiente']
running  = [v for v in cs.values() if v.get('status') == 'En proceso']
err      = [v for v in cs.values() if v.get('status') == 'Error']
done     = [v for v in cs.values() if v.get('status') == 'Completado']

print("=== ESTADO DEL SERVIDOR ===")
print(f"is_running       : {d.get('is_running')}")
print(f"start_time       : {d.get('start_time')}")
acc = d.get('accumulated_time', 0)
print(f"accumulated_time : {acc} seg ({acc/3600:.2f} horas)")
print(f"csv_total        : {d.get('csv_total')}")
print(f"WORKERS activos  : {len(ws)}")
print()
print("=== CONTEO DE CURSOS ===")
print(f"Pendiente        : {len(pending)}")
print(f"En proceso       : {len(running)}")
print(f"Completado       : {len(done)}")
print(f"Error            : {len(err)}")

print()
print("=== WORKER STATES (todos) ===")
for k, v in ws.items():
    print(f"  {k}: {v}")

if running:
    print()
    print("=== EN PROCESO ===")
    for v in running[:10]:
        print(f"  sic={v.get('sic')} progress={v.get('progress')} name={v.get('name')}")

if err:
    print()
    print("=== ERRORES (primeros 10) ===")
    for v in err[:10]:
        print(f"  sic={v.get('sic')} | error={v.get('error','N/A')}")
