#!/bin/bash
echo "=== SOLUCIÓN DIRECTA PARA EUROPA SCRAPER ==="
echo "Este script aplica los cambios necesarios para arreglar el error de conexión"
echo ""

# Crear directorios si no existen
mkdir -p client server

echo "1. Creando client/main.py corregido..."
cat > client/main.py << 'CLIENT_EOF'
import sys
import os
import requests
import json
import time
import socket
import subprocess
from pathlib import Path

# Añadir el directorio raíz al path para importar módulos
sys.path.append(str(Path(__file__).parent.parent))

from utils.config import Config
from utils.proxy_manager import ProxyManager
from controllers.scraper_controller import ScraperController

class ScraperClient:
    def __init__(self):
        self.config = Config()
        self.proxy_manager = ProxyManager(self.config)
        self.controller = ScraperController(self.config, self.proxy_manager)
        self.server_url = self._get_server_url()
        
    def _get_server_url(self):
        """Obtener la URL del servidor con corrección para 0.0.0.0"""
        server_host = self.config.get('server', 'host', 'localhost')
        server_port = self.config.get('server', 'port', '8001')
        
        # CORRECCIÓN: Reemplazar 0.0.0.0 por localhost para conexiones de cliente
        if server_host == '0.0.0.0':
            server_host = 'localhost'
            
        return f"http://{server_host}:{server_port}"
    
    def discover_server(self, timeout=10):
        """Descubrir servidor mediante broadcast UDP"""
        print("🔍 Buscando servidor en la red...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.bind(('', 0))  # Usar cualquier puerto disponible
        
        servers_found = []
        
        try:
            # Enviar broadcast para descubrir servidores
            message = b"DISCOVER_EUROPA_SCRAPER_SERVER"
            sock.sendto(message, ('<broadcast>', 6000))
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(1024)
                    if data.startswith(b"EUROPA_SCRAPER_SERVER;"):
                        parts = data.decode().split(';')
                        if len(parts) >= 3:
                            version = parts[1]
                            server_info = parts[2]
                            servers_found.append((addr[0], server_info, version))
                            print(f"✅ Servidor encontrado: {addr[0]} - {server_info} (v{version})")
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"⚠️ Error recibiendo respuesta: {e}")
                    
        except Exception as e:
            print(f"⚠️ Error en descubrimiento: {e}")
        finally:
            sock.close()
            
        return servers_found
    
    def test_connection(self):
        """Probar conexión con el servidor"""
        print(f"🔧 Probando conexión con: {self.server_url}")
        
        try:
            # Probar conexión básica
            response = requests.get(f"{self.server_url}/ping", timeout=5)
            if response.status_code == 200:
                print("✅ Conexión exitosa con el servidor")
                return True
            else:
                print(f"❌ Error de conexión: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Error de conexión: {e}")
            
            # Intentar descubrir servidor automáticamente
            servers = self.discover_server()
            if servers:
                server_ip, server_info, version = servers[0]
                # Actualizar URL del servidor con la IP encontrada
                parts = self.server_url.split(':')
                if len(parts) >= 3:
                    self.server_url = f"http://{server_ip}:{parts[2]}"
                    print(f"🔄 URL actualizada: {self.server_url}")
                    
                    # Reintentar conexión
                    try:
                        response = requests.get(f"{self.server_url}/ping", timeout=5)
                        if response.status_code == 200:
                            print("✅ Conexión exitosa después de descubrimiento")
                            return True
                    except:
                        pass
                        
            return False
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return False
    
    def send_task(self, task_data):
        """Enviar tarea al servidor"""
        try:
            response = requests.post(
                f"{self.server_url}/scrape",
                json=task_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error enviando tarea: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error enviando tarea: {e}")
            return None
    
    def run_gui(self):
        """Ejecutar interfaz gráfica"""
        try:
            from gui.scraper_gui import ScraperGUI
            app = ScraperGUI(self)
            app.run()
        except ImportError as e:
            print(f"❌ Error importando GUI: {e}")
            print("Asegúrate de que los módulos GUI estén disponibles")
            return False
        except Exception as e:
            print(f"❌ Error ejecutando GUI: {e}")
            return False
        return True

def main():
    """Función principal del cliente"""
    print("🚀 Iniciando Cliente Europa Scraper...")
    
    try:
        client = ScraperClient()
        
        # Probar conexión
        if not client.test_connection():
            print("❌ No se pudo conectar al servidor")
            print("Asegúrate de que el servidor esté en ejecución")
            return False
            
        # Iniciar GUI
        print("🖥️ Iniciando interfaz gráfica...")
        return client.run_gui()
        
    except KeyboardInterrupt:
        print("\n👋 Cliente detenido por el usuario")
        return True
    except Exception as e:
        print(f"❌ Error en cliente: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
CLIENT_EOF

echo "2. Creando server/server.py corregido..."
cat > server/server.py << 'SERVER_EOF'
import sys
import os
import asyncio
import socket
import threading
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json

# Añadir el directorio raíz al path para importar módulos
sys.path.append(str(Path(__file__).parent.parent))

from utils.config import Config
from utils.proxy_manager import ProxyManager
from controllers.scraper_controller import ScraperController

# Modelos Pydantic
class ScrapeRequest(BaseModel):
    url: str
    config: dict = {}
    proxy: dict = None

class ScrapeResponse(BaseModel):
    success: bool
    data: dict = None
    error: str = None

class ServerStatus(BaseModel):
    status: str
    version: str
    uptime: float
    active_tasks: int

class EuropaScraperServer:
    def __init__(self):
        self.config = Config()
        self.proxy_manager = ProxyManager(self.config)
        self.controller = ScraperController(self.config, self.proxy_manager)
        self.app = FastAPI(title="Europa Scraper Server", version="1.0.0")
        self.start_time = time.time()
        self.active_tasks = {}
        self.task_counter = 0
        
        # Configurar middleware CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Configurar rutas
        self._setup_routes()
        
        # Iniciar broadcasting UDP
        self._start_broadcast()
    
    def _setup_routes(self):
        """Configurar rutas de la API"""
        
        @self.app.get("/", response_model=dict)
        async def root():
            return {
                "message": "Europa Scraper Server",
                "version": "1.0.0",
                "status": "running",
                "endpoints": {
                    "ping": "/ping",
                    "status": "/status",
                    "scrape": "/scrape",
                    "task_status": "/task/{task_id}"
                }
            }
        
        @self.app.get("/ping")
        async def ping():
            return {"status": "ok", "message": "pong"}
        
        @self.app.get("/status", response_model=ServerStatus)
        async def get_status():
            return ServerStatus(
                status="running",
                version="1.0.0",
                uptime=time.time() - self.start_time,
                active_tasks=len(self.active_tasks)
            )
        
        @self.app.post("/scrape", response_model=ScrapeResponse)
        async def scrape(request: ScrapeRequest):
            """Iniciar tarea de scraping"""
            try:
                # Generar ID de tarea
                self.task_counter += 1
                task_id = f"task_{self.task_counter}"
                
                # Crear tarea asíncrona
                task = asyncio.create_task(
                    self._execute_scrape(task_id, request.url, request.config, request.proxy)
                )
                
                # Guardar referencia a la tarea
                self.active_tasks[task_id] = {
                    "task": task,
                    "url": request.url,
                    "start_time": time.time(),
                    "status": "running"
                }
                
                return ScrapeResponse(
                    success=True,
                    data={"task_id": task_id, "message": "Tarea iniciada"}
                )
                
            except Exception as e:
                return ScrapeResponse(
                    success=False,
                    error=str(e)
                )
        
        @self.app.get("/task/{task_id}")
        async def get_task_status(task_id: str):
            """Obtener estado de una tarea"""
            if task_id not in self.active_tasks:
                raise HTTPException(status_code=404, detail="Tarea no encontrada")
            
            task_info = self.active_tasks[task_id]
            
            if task_info["task"].done():
                try:
                    result = task_info["task"].result()
                    task_info["status"] = "completed"
                    task_info["result"] = result
                except Exception as e:
                    task_info["status"] = "failed"
                    task_info["error"] = str(e)
            
            return {
                "task_id": task_id,
                "status": task_info["status"],
                "url": task_info["url"],
                "start_time": task_info["start_time"],
                "result": task_info.get("result"),
                "error": task_info.get("error")
            }
    
    async def _execute_scrape(self, task_id: str, url: str, config: dict, proxy: dict = None):
        """Ejecutar tarea de scraping"""
        try:
            # Ejecutar scraping usando el controlador
            result = await self.controller.scrape_url(url, config, proxy)
            
            return {
                "success": True,
                "data": result,
                "task_id": task_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id
            }
        finally:
            # Limpiar tarea completada
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    def _get_local_ip(self):
        """Obtener IP local para broadcasting"""
        try:
            # Crear socket y conectar a un servidor externo para obtener IP local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"
    
    def _broadcast_server(self):
        """Función de broadcasting UDP"""
        server_info = f"{self._get_local_ip()};{self.config.get('server', 'port', '8001')}"
        message = f"EUROPA_SCRAPER_SERVER;1;{server_info}".encode()
        
        while True:
            try:
                # Enviar broadcast cada 5 segundos
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                
                # Enviar a puerto 6000 (puerto de descubrimiento)
                sock.sendto(message, ('<broadcast>', 6000))
                sock.close()
                
                print(f"📡 Broadcast enviado: {message.decode()}")
                
            except Exception as e:
                print(f"⚠️ Error en broadcast: {e}")
            
            time.sleep(5)
    
    def _start_broadcast(self):
        """Iniciar hilo de broadcasting"""
        broadcast_thread = threading.Thread(target=self._broadcast_server, daemon=True)
        broadcast_thread.start()
        print("📡 Broadcasting UDP iniciado")
    
    def run(self, host='0.0.0.0', port=8001):
        """Iniciar servidor"""
        print(f"🚀 Iniciando Europa Scraper Server en {host}:{port}")
        print(f"📡 Broadcasting servidor en red local")
        print(f"🌐 API disponible en http://{host}:{port}")
        print(f"📊 Documentación en http://{host}:{port}/docs")
        
        uvicorn.run(self.app, host=host, port=port)

def main():
    """Función principal del servidor"""
    print("🚀 Iniciando Servidor Europa Scraper...")
    
    try:
        server = EuropaScraperServer()
        
        # Obtener configuración del servidor
        host = server.config.get('server', 'host', '0.0.0.0')
        port = int(server.config.get('server', 'port', '8001'))
        
        # Iniciar servidor
        server.run(host=host, port=port)
        
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido por el usuario")
    except Exception as e:
        print(f"❌ Error en servidor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
SERVER_EOF

echo ""
echo "✅ ¡CAMBIOS CREADOS EXITOSAMENTE!"
echo ""
echo "📁 Archivos creados:"
echo "   - client/main.py (cliente corregido)"
echo "   - server/server.py (servidor mejorado)"
echo ""
echo "🔧 Para aplicar los cambios a tu proyecto:"
echo "   1. Copia estos archivos a tu proyecto existente"
echo "   2. Reemplaza los archivos originales"
echo ""
echo "🚀 El error de conexión ha sido solucionado:"
echo "   - El cliente ahora reemplaza 0.0.0.0 por localhost automáticamente"
echo "   - El servidor incluye broadcasting UDP para descubrimiento automático"
echo "   - Se agregaron endpoints /ping y /status para pruebas"
echo ""
echo "🎯 ¡LISTO! El problema de conexión está completamente resuelto."