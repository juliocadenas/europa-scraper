#!/usr/bin/env python3

import socket
import time

def test_client_discovery():
    """Prueba el descubrimiento de servidores como lo haría el cliente."""
    
    print("Buscando servidores como el cliente...")
    
    # Primero buscar en localhost (prioridad para misma PC)
    server_ports = [8001, 8002, 8003]
    
    print("Buscando en localhost...")
    for port in server_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                if sock.connect_ex(('127.0.0.1', port)) == 0:
                    try:
                        sock.sendall(b"PING\n")
                        response = sock.recv(100)
                        if b"EUROPA_SCRAPER_SERVER_PONG" in response:
                            print(f"Servidor encontrado: 127.0.0.1:{port}")
                            print(f"Nombre: Localhost")
                            return f"127.0.0.1:{port}"
                    except:
                        pass
        except Exception as e:
            print(f"Error probando 127.0.0.1:{port}: {e}")
    
    # Si no se encuentra, escuchar broadcasts
    print("No encontrado en localhost, escuchando broadcasts...")
    broadcast_ports = [6000, 6001, 6002]
    
    for broadcast_port in broadcast_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('127.0.0.1', broadcast_port))
                sock.settimeout(5)
                
                print(f"Escuchando en puerto {broadcast_port}...")
                start_time = time.time()
                while time.time() - start_time < 5:
                    try:
                        data, addr = sock.recvfrom(1024)
                        message = data.decode('utf-8')
                        print(f"Mensaje recibido: {message}")
                        if message.startswith("EUROPA_SCRAPER_SERVER"):
                            parts = message.split(';')
                            if len(parts) == 4:
                                _, server_ip, server_port, machine_name = parts
                                server_address = f"{server_ip}:{server_port}"
                                print(f"Servidor encontrado via broadcast: {machine_name} - {server_address}")
                                return server_address
                    except socket.timeout:
                        continue
        except Exception as e:
            print(f"Error escuchando en puerto {broadcast_port}: {e}")
    
    print("No se encontraron servidores.")
    return None

if __name__ == "__main__":
    test_client_discovery()