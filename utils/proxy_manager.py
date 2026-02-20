"""
Proxy Manager
-------------
Gestiona la configuración y uso de proxies para el scraping.
"""

import logging
import random
import time
import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple, Any
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ProxyManager:
    """
    Gestiona proxies para el scraping web.
    Incluye rotación automática, validación y manejo de errores.
    """
    
    def __init__(self):
        """Inicializa el gestor de proxies."""
        self.proxies = []
        self.current_proxy_index = 0
        self.enabled = False  # DESHABILITADO por defecto
        self.rotation_enabled = True
        self.timeout = 30
        self.max_retries = 3
        self.failed_proxies = set()
        self.proxy_stats = {}
        
        logger.info("ProxyManager inicializado (proxies deshabilitados por defecto)")
    
    def is_enabled(self) -> bool:
        """
        Verifica si los proxies están habilitados.
        
        Returns:
            bool: True si están habilitados, False en caso contrario
        """
        return self.enabled and len(self.proxies) > 0
    
    def enable(self, enable: bool = True):
        """
        Habilita o deshabilita el uso de proxies.
        
        Args:
            enable: True para habilitar, False para deshabilitar
        """
        self.enabled = enable
        if enable:
            logger.info("Proxies HABILITADOS")
        else:
            logger.info("Proxies DESHABILITADOS")
    
    def set_proxies(self, proxy_list: List[str]):
        """
        Establece la lista de proxies a utilizar.
        
        Args:
            proxy_list: Lista de proxies en formato "host:puerto" o "host:puerto:usuario:contraseña"
        """
        self.proxies = []
        self.failed_proxies = set()
        self.proxy_stats = {}
        
        for proxy_str in proxy_list:
            proxy_str = proxy_str.strip()
            if not proxy_str:
                continue
            
            try:
                proxy_info = self._parse_proxy_string(proxy_str)
                if proxy_info:
                    self.proxies.append(proxy_info)
                    self.proxy_stats[proxy_str] = {
                        'success_count': 0,
                        'failure_count': 0,
                        'last_used': None,
                        'response_time': None
                    }
            except Exception as e:
                logger.warning(f"Error parseando proxy '{proxy_str}': {str(e)}")
        
        logger.info(f"Configurados {len(self.proxies)} proxies válidos")
        
        # Si hay proxies configurados pero no están habilitados, mostrar advertencia
        if self.proxies and not self.enabled:
            logger.warning("Proxies configurados pero NO habilitados. Usar enable() para habilitarlos.")
    
    def _parse_proxy_string(self, proxy_str: str) -> Optional[Dict[str, Any]]:
        """
        Parsea una cadena de proxy en formato "host:puerto" o "host:puerto:usuario:contraseña".
        
        Args:
            proxy_str: Cadena del proxy
            
        Returns:
            Dict con información del proxy o None si es inválido
        """
        try:
            parts = proxy_str.split(':')
            
            if len(parts) < 2:
                logger.warning(f"Formato de proxy inválido: {proxy_str}")
                return None
            
            host = parts[0].strip()
            port = int(parts[1].strip())
            
            # Validar host y puerto
            if not host or port <= 0 or port > 65535:
                logger.warning(f"Host o puerto inválido en proxy: {proxy_str}")
                return None
            
            proxy_info = {
                'host': host,
                'port': port,
                'username': None,
                'password': None,
                'original_string': proxy_str
            }
            
            # Si hay credenciales
            if len(parts) >= 4:
                proxy_info['username'] = parts[2].strip()
                proxy_info['password'] = parts[3].strip()
            
            return proxy_info
            
        except ValueError as e:
            logger.warning(f"Error parseando puerto en proxy '{proxy_str}': {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado parseando proxy '{proxy_str}': {str(e)}")
            return None
    
    def get_next_proxy(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene el siguiente proxy disponible.
        
        Returns:
            Dict con información del proxy o None si no hay proxies disponibles
        """
        if not self.is_enabled():
            return None
        
        if not self.proxies:
            logger.warning("No hay proxies configurados")
            return None
        
        # Si la rotación está deshabilitada, usar siempre el primer proxy
        if not self.rotation_enabled:
            return self.proxies[0] if self.proxies else None
        
        # Buscar un proxy que no haya fallado
        attempts = 0
        max_attempts = len(self.proxies)
        
        while attempts < max_attempts:
            proxy = self.proxies[self.current_proxy_index]
            proxy_str = proxy['original_string']
            
            # Avanzar al siguiente proxy para la próxima vez
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            attempts += 1
            
            # Si el proxy no ha fallado recientemente, usarlo
            if proxy_str not in self.failed_proxies:
                return proxy
        
        # Si todos los proxies han fallado, limpiar la lista de fallos y usar cualquiera
        logger.warning("Todos los proxies han fallado, limpiando lista de fallos")
        self.failed_proxies.clear()
        
        return self.proxies[0] if self.proxies else None
    
    def get_random_proxy(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene un proxy aleatorio.
        
        Returns:
            Dict con información del proxy o None si no hay proxies disponibles
        """
        if not self.is_enabled():
            return None
        
        if not self.proxies:
            return None
        
        # Filtrar proxies que no hayan fallado
        available_proxies = [p for p in self.proxies if p['original_string'] not in self.failed_proxies]
        
        if not available_proxies:
            # Si todos han fallado, usar cualquiera
            available_proxies = self.proxies
            self.failed_proxies.clear()
        
        return random.choice(available_proxies)
    
    def mark_proxy_failed(self, proxy: Dict[str, Any], error: str = ""):
        """
        Marca un proxy como fallido.
        
        Args:
            proxy: Información del proxy
            error: Descripción del error (opcional)
        """
        if not proxy:
            return
        
        proxy_str = proxy['original_string']
        self.failed_proxies.add(proxy_str)
        
        # Actualizar estadísticas
        if proxy_str in self.proxy_stats:
            self.proxy_stats[proxy_str]['failure_count'] += 1
        
        logger.warning(f"Proxy marcado como fallido: {proxy_str} - {error}")
    
    def mark_proxy_success(self, proxy: Dict[str, Any], response_time: float = None):
        """
        Marca un proxy como exitoso.
        
        Args:
            proxy: Información del proxy
            response_time: Tiempo de respuesta en segundos (opcional)
        """
        if not proxy:
            return
        
        proxy_str = proxy['original_string']
        
        # Remover de la lista de fallos si estaba ahí
        self.failed_proxies.discard(proxy_str)
        
        # Actualizar estadísticas
        if proxy_str in self.proxy_stats:
            self.proxy_stats[proxy_str]['success_count'] += 1
            self.proxy_stats[proxy_str]['last_used'] = time.time()
            if response_time:
                self.proxy_stats[proxy_str]['response_time'] = response_time
        
        logger.debug(f"Proxy exitoso: {proxy_str}")
    
    def get_proxy_for_playwright(self, proxy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convierte la información del proxy al formato requerido por Playwright.
        
        Args:
            proxy: Información del proxy
            
        Returns:
            Dict en formato Playwright o None
        """
        if not proxy:
            return None
        
        playwright_proxy = {
            'server': f"http://{proxy['host']}:{proxy['port']}"
        }
        
        if proxy.get('username') and proxy.get('password'):
            playwright_proxy['username'] = proxy['username']
            playwright_proxy['password'] = proxy['password']
        
        return playwright_proxy
    
    def get_proxy_for_requests(self, proxy: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Convierte la información del proxy al formato requerido por requests.
        
        Args:
            proxy: Información del proxy
            
        Returns:
            Dict en formato requests o None
        """
        if not proxy:
            return None
        
        if proxy.get('username') and proxy.get('password'):
            proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
        else:
            proxy_url = f"http://{proxy['host']}:{proxy['port']}"
        
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    async def test_proxy(self, proxy: Dict[str, Any], test_url: str = "http://httpbin.org/ip") -> Tuple[bool, str, float]:
        """
        Prueba un proxy específico.
        
        Args:
            proxy: Información del proxy
            test_url: URL para probar el proxy
            
        Returns:
            Tupla (éxito, mensaje, tiempo_respuesta)
        """
        if not proxy:
            return False, "Proxy inválido", 0.0
        
        start_time = time.time()
        
        try:
            proxy_url = f"http://{proxy['host']}:{proxy['port']}"
            
            # Configurar autenticación si es necesaria
            auth = None
            if proxy.get('username') and proxy.get('password'):
                auth = aiohttp.BasicAuth(proxy['username'], proxy['password'])
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(test_url, proxy=proxy_url, proxy_auth=auth) as response:
                    if response.status == 200:
                        response_time = time.time() - start_time
                        return True, "Proxy funcionando correctamente", response_time
                    else:
                        return False, f"Código de estado HTTP: {response.status}", 0.0
        
        except asyncio.TimeoutError:
            return False, "Timeout de conexión", 0.0
        except Exception as e:
            return False, f"Error: {str(e)}", 0.0
    
    async def test_all_proxies(self, test_url: str = "http://httpbin.org/ip") -> Dict[str, Dict[str, Any]]:
        """
        Prueba todos los proxies configurados.
        
        Args:
            test_url: URL para probar los proxies
            
        Returns:
            Dict con resultados de las pruebas
        """
        if not self.proxies:
            logger.warning("No hay proxies para probar")
            return {}
        
        logger.info(f"Probando {len(self.proxies)} proxies...")
        
        results = {}
        tasks = []
        
        # Crear tareas para probar todos los proxies en paralelo
        for proxy in self.proxies:
            task = self.test_proxy(proxy, test_url)
            tasks.append((proxy['original_string'], task))
        
        # Ejecutar todas las pruebas
        for proxy_str, task in tasks:
            try:
                success, message, response_time = await task
                results[proxy_str] = {
                    'success': success,
                    'message': message,
                    'response_time': response_time
                }
                
                if success:
                    logger.info(f"✓ {proxy_str}: {message} ({response_time:.2f}s)")
                else:
                    logger.warning(f"✗ {proxy_str}: {message}")
                    
            except Exception as e:
                results[proxy_str] = {
                    'success': False,
                    'message': f"Error en prueba: {str(e)}",
                    'response_time': 0.0
                }
                logger.error(f"✗ {proxy_str}: Error en prueba: {str(e)}")
        
        # Actualizar lista de proxies fallidos basado en los resultados
        self.failed_proxies.clear()
        for proxy_str, result in results.items():
            if not result['success']:
                self.failed_proxies.add(proxy_str)
        
        working_count = sum(1 for r in results.values() if r['success'])
        logger.info(f"Pruebas completadas: {working_count}/{len(results)} proxies funcionando")
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso de proxies.
        
        Returns:
            Dict con estadísticas
        """
        total_proxies = len(self.proxies)
        failed_proxies = len(self.failed_proxies)
        working_proxies = total_proxies - failed_proxies
        
        return {
            'enabled': self.enabled,
            'total_proxies': total_proxies,
            'working_proxies': working_proxies,
            'failed_proxies': failed_proxies,
            'rotation_enabled': self.rotation_enabled,
            'current_proxy_index': self.current_proxy_index,
            'proxy_stats': self.proxy_stats.copy()
        }
    
    def reset_failed_proxies(self):
        """Limpia la lista de proxies fallidos."""
        self.failed_proxies.clear()
        logger.info("Lista de proxies fallidos limpiada")
    
    def set_rotation_enabled(self, enabled: bool):
        """
        Habilita o deshabilita la rotación de proxies.
        
        Args:
            enabled: True para habilitar rotación, False para usar siempre el mismo proxy
        """
        self.rotation_enabled = enabled
        logger.info(f"Rotación de proxies {'habilitada' if enabled else 'deshabilitada'}")
    
    def set_timeout(self, timeout: int):
        """
        Establece el timeout para las conexiones de proxy.
        
        Args:
            timeout: Timeout en segundos
        """
        self.timeout = max(1, timeout)
        logger.info(f"Timeout de proxy establecido a {self.timeout} segundos")
    
    def set_max_retries(self, max_retries: int):
        """
        Establece el número máximo de reintentos.
        
        Args:
            max_retries: Número máximo de reintentos
        """
        self.max_retries = max(0, max_retries)
        logger.info(f"Máximo de reintentos establecido a {self.max_retries}")
