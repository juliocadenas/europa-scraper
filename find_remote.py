import paramiko
import os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('100.83.253.87', username='julio', password='julio@julio')

# Encontrar donde esta el proyecto
stdin, stdout, stderr = client.exec_command('find /home/julio -name server.py 2>/dev/null | grep server/server.py')
paths = stdout.read().decode().strip().split('\n')
print(f"Paths found: {paths}")
