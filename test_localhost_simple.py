#!/usr/bin/env python3

import socket

def test_localhost():
    """Prueba conexion localhost."""
    
    server_ports = [8001, 8002, 8003]
    
    for port in server_ports:
        print(f"Probando 127.0.0.1:{port}")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                result = sock.connect_ex(('127.0.0.1', port))
                if result == 0:
                    print(f"Conexion exitosa a 127.0.0.1:{port}")
                    
                    # Probar si es nuestro servidor
                    try:
                        sock.sendall(b"PING\n")
                        response = sock.recv(100)
                        print(f"Respuesta: {response.decode('utf-8').strip()}")
                        if b"EUROPA_SCRAPER_SERVER_PONG" in response:
                            print(f"Servidor Europa encontrado!")
                            return True
                    except Exception as e:
                        print(f"Error en ping: {e}")
                else:
                    print(f"Conexion fallida a 127.0.0.1:{port}")
                    
        except Exception as e:
            print(f"Error: {e}")
    
    print("No se encontro servidor Europa en localhost.")
    return False

if __name__ == "__main__":
    test_localhost()