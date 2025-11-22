#!/usr/bin/env python3

import subprocess
import re

def find_port_occupier(port):
    try:
        # Ejecutar netstat
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        for line in lines:
            if f':{port}' in line and 'LISTENING' in line:
                parts = re.split(r'\s+', line.strip())
                pid = parts[-1]
                print(f"Puerto {port} ocupado por PID: {pid}")
                
                # Obtener información del proceso
                try:
                    task_result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'], capture_output=True, text=True)
                    print(f"Proceso: {task_result.stdout}")
                except:
                    print(f"No se pudo obtener info del PID {pid}")
                return True
        print(f"Puerto {port} libre")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

# Probar varios puertos
for port in [8001, 8002, 8003, 9001]:
    find_port_occupier(port)