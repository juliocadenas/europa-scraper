#!/usr/bin/env python3
import socket
import threading
import queue
import time

def test_server_discovery():
    """Prueba directa de descubrimiento de servidor"""
    print("=== PRUEBA DE DESCUBRIMIENTO DE SERVIDOR ===")
    
    # Probar conexión TCP directa
    server_ports = [8001, 8002, 8003]
    
    for port in server_ports:
        print(f"\nProbando puerto TCP {port}...")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                result = sock.connect_ex(('127.0.0.1', port))
                if result == 0:
                    print(f"[OK] Conexion establecida en puerto {port}")
                    try:
                        sock.sendall(b"PING\n")
                        response = sock.recv(100)
                        print(f"[RESP] Respuesta recibida: {response}")
                        if b"EUROPA_SCRAPER_SERVER_PONG" in response:
                            print(f"[SUCCESS] SERVIDOR ENCONTRADO EN PUERTO {port}!")
                            return f"127.0.0.1:{port}"
                        else:
                            print(f"[ERROR] Respuesta incorrecta: {response}")
                    except Exception as e:
                        print(f"[ERROR] Error enviando PING: {e}")
                else:
                    print(f"[FAIL] No se puede conectar al puerto {port}, codigo: {result}")
        except Exception as e:
            print(f"[ERROR] Excepcion en puerto {port}: {e}")
    
    # Probar recepción de broadcast UDP
    print(f"\nProbando recepcion de broadcast UDP en puerto 6000...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', 6000))
            sock.settimeout(5)
            
            print("Escuchando broadcasts por 5 segundos...")
            start_time = time.time()
            while time.time() - start_time < 5:
                try:
                    data, addr = sock.recvfrom(1024)
                    message = data.decode('utf-8')
                    print(f"[BROADCAST] Broadcast recibido: {message}")
                    if message.startswith("EUROPA_SCRAPER_SERVER"):
                        parts = message.split(';')
                        if len(parts) == 4:
                            _, server_ip, server_port, machine_name = parts
                            server_address = f"{server_ip}:{server_port}"
                            print(f"[SUCCESS] SERVIDOR ENCONTRADO VIA BROADCAST: {machine_name} - {server_address}!")
                            return server_address
                except socket.timeout:
                    continue
            print("[TIMEOUT] Timeout esperando broadcasts")
    except Exception as e:
        print(f"[ERROR] Error escuchando broadcasts: {e}")
    
    print(f"\n[FAIL] NO SE ENCONTRO NINGUN SERVIDOR")
    return None

if __name__ == "__main__":
    server_address = test_server_discovery()
    if server_address:
        print(f"\n[SUCCESS] EXITO! Servidor encontrado en: {server_address}")
    else:
        print(f"\n[FAIL] FALLO! No se encontro el servidor")