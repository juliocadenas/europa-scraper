#!/usr/bin/env python3

import socket
import time

def test_server_connection():
    """Prueba conectarse al servidor directamente."""
    
    # Obtener IP local
    local_ip = socket.gethostbyname(socket.gethostname())
    network_parts = local_ip.split('.')
    network_base = '.'.join(network_parts[:-1])
    
    print(f"Tu IP: {local_ip}")
    print(f"Escaneando red: {network_base}.*")
    
    server_ports = [8001, 8002, 8003]
    
    for server_port in server_ports:
        print(f"\nEscaneando puerto {server_port}:")
        
        for i in range(1, 255):
            if i > 10:  # Limitar a primeras 10 IPs
                break
                
            if i == int(network_parts[-1]):
                continue  # Saltar propia IP
            
            server_ip = f"{network_base}.{i}"
            
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex((server_ip, server_port))
                    if result == 0:
                        print(f"  ✓ Conexión exitosa a {server_ip}:{server_port}")
                        
                        # Probar si es nuestro servidor
                        try:
                            sock.sendall(b"PING\n")
                            response = sock.recv(100)
                            if b"EUROPA" in response:
                                print(f"  ¡Servidor Europa encontrado en {server_ip}:{server_port}!")
                                print(f"  Respuesta: {response.decode('utf-8').strip()}")
                                return server_ip, server_port
                        except:
                            print(f"  Conexión OK pero no es nuestro servidor")
                    else:
                        print(f"  ✗ {server_ip}:{server_port} - Conexión fallida")
                        
            except Exception as e:
                print(f"  ✗ {server_ip}:{server_port} - Error: {e}")
    
    print("\nNo se encontraron servidores Europa activos.")
    return None, None

if __name__ == "__main__":
    test_server_connection()