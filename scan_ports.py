
import socket

def scan_ports(ip, ports):
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex((ip, port))
            if result == 0:
                print(f"Port {port} is OPEN")

if __name__ == "__main__":
    target_ip = "192.168.1.210"
    common_ssh_ports = [22, 2222, 1022, 2200, 22222, 443, 80]
    # Also scan some other ports just in case
    scan_ports(target_ip, common_ssh_ports)
