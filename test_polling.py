#!/usr/bin/env python3
"""Test rápido de polling - verifica si el servidor responde con datos."""
import requests
import json
import time

URL = "http://100.83.253.87:8001"

print("=" * 60)
print("TEST DE POLLING DEL SERVIDOR")
print("=" * 60)

for i in range(3):
    print(f"\n--- Poll #{i+1} ---")
    try:
        # Test 1: detailed_status
        r = requests.get(f"{URL}/api/detailed_status", timeout=10)
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            workers = data.get("workers", {})
            courses = data.get("courses", {})
            is_running = data.get("is_running", False)
            csv_total = data.get("csv_total", 0)
            
            print(f"is_running: {is_running}")
            print(f"workers: {len(workers)}")
            print(f"courses: {len(courses)}")
            print(f"csv_total: {csv_total}")
            
            # Mostrar primeros 3 cursos
            if courses:
                course_list = list(courses.values())[:3]
                for c in course_list:
                    print(f"  Curso: sic={c.get('sic')} status={c.get('status')} progress={c.get('progress')}")
            
            # Mostrar primeros 3 workers
            if workers:
                for wid, wdata in list(workers.items())[:3]:
                    print(f"  Worker {wid}: status={wdata.get('status')} task={wdata.get('current_task','')[:50]}")
        else:
            print(f"ERROR: Status code {r.status_code}")
            print(f"Response: {r.text[:200]}")
    
    except Exception as e:
        print(f"ERROR DE CONEXIÓN: {e}")
    
    # Test 2: events
    try:
        r2 = requests.get(f"{URL}/api/events?min_id=0", timeout=5)
        if r2.status_code == 200:
            evs = r2.json().get("events", [])
            print(f"Events: {len(evs)} eventos")
            if evs:
                for ev in evs[:3]:
                    print(f"  Event: {ev.get('source')} | {ev.get('type')} | {ev.get('message','')[:60]}")
        else:
            print(f"Events status: {r2.status_code}")
    except Exception as e:
        print(f"Events error: {e}")
    
    if i < 2:
        time.sleep(3)

print("\n" + "=" * 60)
print("TEST COMPLETADO")
print("=" * 60)
