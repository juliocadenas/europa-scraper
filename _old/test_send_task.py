#!/usr/bin/env python3
import socket
import json

def test_send_task():
    """Prueba enviar una tarea al servidor"""
    print("=== PRUEBA DE ENVIO DE TAREA ===")
    
    # Datos de prueba
    task_data = {
        'from_sic': '01.0',
        'to_sic': '01.0', 
        'from_course': 'AGRICULTURAL PRODUCTION',
        'to_course': 'AGRICULTURAL PRODUCTION',
        'min_words': 30
    }
    
    try:
        # Conectar al servidor
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(10)
            print("Conectando al servidor 127.0.0.1:8001...")
            result = sock.connect_ex(('127.0.0.1', 8001))
            
            if result == 0:
                print("[OK] Conexion establecida")
                
                # Enviar tarea
                request = json.dumps(task_data)
                print(f"Enviando tarea: {request}")
                sock.sendall(request.encode('utf-8'))
                
                # Esperar respuesta
                print("Esperando respuesta...")
                response_data = sock.recv(4096)
                print(f"Respuesta recibida: {response_data}")
                
                # Procesar múltiples respuestas
                for response_str in response_data.decode('utf-8').strip().split('\n'):
                    if response_str:
                        try:
                            response = json.loads(response_str)
                            print(f"Respuesta JSON: {response}")
                            
                            if response.get('type') == 'progress':
                                print(f"Progreso: {response.get('percentage')}%")
                            elif response.get('type') == 'log':
                                print(f"Log: {response.get('message')}")
                        except json.JSONDecodeError:
                            print(f"Respuesta no JSON: {response_str}")
            else:
                print(f"[FAIL] No se pudo conectar, codigo: {result}")
                
    except Exception as e:
        print(f"[ERROR] Error: {e}")

if __name__ == "__main__":
    test_send_task()