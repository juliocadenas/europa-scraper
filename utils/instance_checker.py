# -*- coding: utf-8 -*-

import os
import sys
import time
import socket
import threading
import logging
import tempfile
import atexit

# Configurar logger
logger = logging.getLogger('scraper.instance_checker')

# Puerto TCP para bloqueo de instancia única
LOCK_PORT = 50789

# Archivo de bloqueo (como respaldo)
LOCK_FILE = os.path.join(tempfile.gettempdir(), "usagov_scraper_lock.tmp")

# Socket global para mantener el puerto bloqueado
_lock_socket = None
_thread_running = False

def _keep_socket_alive():
    """Mantiene el socket abierto en un hilo separado"""
    global _lock_socket, _thread_running
    while _thread_running and _lock_socket:
        time.sleep(1)
    logger.debug("Socket keep-alive thread terminated")

def cleanup():
    """Limpia los recursos al salir"""
    global _lock_socket, _thread_running
    logger.debug("Cleaning up instance checker resources")
    _thread_running = False
    if _lock_socket:
        try:
            _lock_socket.close()
        except:
            pass
        _lock_socket = None
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except:
            pass

def ensure_single_instance():
    """
    Asegura que solo una instancia de la aplicación esté en ejecución.
    Utiliza un socket TCP para bloquear un puerto específico.
    
    Returns:
        bool: True si esta es la única instancia, False si ya hay otra instancia en ejecución.
    """
    global _lock_socket, _thread_running
    
    # Registrar la función de limpieza para que se ejecute al salir
    atexit.register(cleanup)
    
    try:
        # Verificar si el puerto ya está en uso
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(1)
        result = test_socket.connect_ex(('localhost', LOCK_PORT))
        test_socket.close()
        
        if result == 0:
            logger.warning(f"Port {LOCK_PORT} is already in use. Another instance is likely running.")
            return False
        
        # Intentar crear un socket y vincularlo al puerto de bloqueo
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _lock_socket.bind(('localhost', LOCK_PORT))
        _lock_socket.listen(1)
        
        # Iniciar un hilo para mantener el socket abierto
        _thread_running = True
        socket_thread = threading.Thread(target=_keep_socket_alive, daemon=True)
        socket_thread.start()
        
        # Como respaldo, también usar un archivo de bloqueo
        if os.path.exists(LOCK_FILE):
            # Verificar si el archivo de bloqueo es antiguo (más de 1 hora)
            file_age = time.time() - os.path.getmtime(LOCK_FILE)
            if file_age > 3600:  # 1 hora en segundos
                logger.warning(f"Lock file exists but is old ({file_age:.0f} seconds). Removing it.")
                try:
                    os.remove(LOCK_FILE)
                except:
                    pass
        
        # Crear archivo de bloqueo
        try:
            with open(LOCK_FILE, 'w') as f:
                f.write(f"PID: {os.getpid()}\n")
                f.write(f"Time: {time.ctime()}\n")
        except:
            logger.warning("Could not create lock file, continuing anyway")
        
        return True
        
    except socket.error as e:
        logger.warning(f"Socket error when checking for single instance: {e}")
        cleanup()
        return False
    except Exception as e:
        logger.error(f"Error checking for single instance: {e}")
        cleanup()
        return False
