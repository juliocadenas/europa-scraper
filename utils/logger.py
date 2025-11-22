import logging
import os
import sys
from datetime import datetime
from typing import Callable, Optional

# Handler global para capturar todos los logs
class GlobalLogHandler(logging.Handler):
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        super().__init__()
        self.logs = []
        self.callback = None
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        self.setFormatter(self.formatter)
    
    def emit(self, record):
        log_entry = self.format(record)
        self.logs.append(log_entry)
        if self.callback:
            self.callback(log_entry)
    
    def set_callback(self, callback: Callable[[str], None]):
        self.callback = callback
    
    def get_logs(self):
        return self.logs
    
    def clear(self):
        self.logs = []

def setup_logger(log_level=logging.INFO, log_file=None):
    """
    Configura el sistema de logging para la aplicación.
    
    Args:
        log_level: Nivel de logging (default: INFO)
        log_file: Archivo de log personalizado (default: None, se genera automáticamente)
    
    Returns:
        Logger configurado
    """
    # Crear directorio de logs si no existe
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Generar nombre de archivo de log si no se proporciona
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(log_dir, f"scraper_{timestamp}.log")
    
    # Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Limpiar handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Crear handler para archivo
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level)
    root_logger.addHandler(file_handler)
    
    # Crear handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
    console_handler.setLevel(log_level)
    # Set encoding to UTF-8 to prevent UnicodeEncodeError
    console_handler.stream.reconfigure(encoding='utf-8')
    root_logger.addHandler(console_handler)
    
    # Añadir el handler global para capturar todos los logs
    global_handler = GlobalLogHandler.get_instance()
    root_logger.addHandler(global_handler)
    
    # Set specific levels for certain loggers if needed
    logging.getLogger('httpx').setLevel(logging.INFO)
    captcha_solver_logger = logging.getLogger('utils.captcha_solver')
    captcha_solver_logger.setLevel(logging.INFO)
    captcha_solver_logger.addHandler(console_handler) # Add console handler specifically for this logger
    
    # Crear logger específico para el módulo
    logger = logging.getLogger('root')
    logger.info(f"Logging initialized to {log_file}")
    
    return logger

def get_global_log_handler():
    """
    Obtiene el handler global para capturar logs.
    
    Returns:
        GlobalLogHandler: Handler global
    """
    return GlobalLogHandler.get_instance()
