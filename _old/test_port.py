#!/usr/bin/env python3

import socket

def test_port(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', port))
        sock.listen(5)
        print(f"Puerto {port} OK")
        sock.close()
        return True
    except Exception as e:
        print(f"Puerto {port} Error: {e}")
        return False

# Probar varios puertos
for port in [8001, 8002, 8003, 9001, 12345, 54321]:
    test_port(port)