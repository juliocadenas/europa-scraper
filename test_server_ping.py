#!/usr/bin/env python3

import socket
import time

def test_server_ping():
    """Prueba si el servidor responde al ping correctamente."""
    
    server_ports = [8001, 8002, 8003]
    
    for port in server_ports:
        print(f"Probando 127.0.0.1:{port}")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                result = sock.connect_ex(('127.0.0.1', port))
                if result == 0:
                    print(f"Conexion exitosa a 127.0.0.1:{port}")
                    
                    # Probar si es nuestro servidor
                    try:
                        sock.sendall(b"PING\n")
                        response = sock.recv(100)
                        print(f"Respuesta recibida: {len(response)} bytes")
                        print(f"Contenido: {response}")
                        
                        if b"EUROPA_SCRAPER_SERVER_PONG" in response:
                            print(f"Servidor Europa encontrado en puerto {port}!")
                            return True
                        else:
                            print(f"Respuesta inesperada: {response.decode('utf-8', errors='ignore')}")
                    except Exception as e:
                        print(f"Error en ping: {e}")
                else:
                    print(f"Conexion fallida a 127.0.0.1:{port} (codigo: {result})")
                    
        except Exception as e:
            print(f"Error: {e}")
    
    print("No se encontro servidor Europa.")
    return False

if __name__ == "__main__":
    test_server_ping()