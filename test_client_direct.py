#!/usr/bin/env python3
# Cliente de prueba para descubrir servidores

import socket
import time

def test_direct_server_discovery():
    print("=== CLIENTE DE PRUEBA PARA DESCUBRIMIENTO ===")
    
    # Puerto del servidor
    server_ports = [8001, 8002, 8003]
    
    # Prueba de conexión TCP
    print("Probando conexion TCP directa...")
    for port in server_ports:
        print(f"\nProbando puerto {port}...")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                result = sock.connect_ex(('127.0.0.1', port))
                print(f"  Resultado conexion: {result}")
                
                if result == 0:
                    print(f"  Conectado a puerto {port}")
                    try:
                        # Enviar PING
                        sock.sendall(b"PING\n")
                        response = sock.recv(100)
                        print(f"  Respuesta: {response}")
                        
                        if b"EUROPA_SCRAPER_SERVER_PONG" in response:
                            print(f"  [OK] SERVIDOR ENCONTRADO EN PUERTO {port}!")
                            print(f"  Direccion: 127.0.0.1:{port}")
                            return f"127.0.0.1:{port}"
                    except Exception as e:
                        print(f"  [ERROR] Error en comunicacion: {e}")
                else:
                    print(f"  [FAIL] No se puede conectar")
        except Exception as e:
            print(f"  [ERROR] Excepcion: {e}")
    
    print("\nNo se encontro servidor por TCP")
    return None

if __name__ == "__main__":
    server_addr = test_direct_server_discovery()
    if server_addr:
        print(f"\n[SUCCESS] Servidor encontrado: {server_addr}")
    else:
        print(f"\n[FAIL] No se encontro servidor")