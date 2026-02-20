import asyncio
import logging
import random
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class AdaptiveDelay:
    """
    Implementa un sistema de retrasos adaptativos para evitar bloqueos.
    """
    
    def __init__(self, initial_delay: float = 1.0, max_delay: float = 30.0, jitter: float = 0.25):
        """
        Inicializa el sistema de retrasos adaptativos.
        
        Args:
            initial_delay: Retraso inicial en segundos
            max_delay: Retraso máximo en segundos
            jitter: Factor de variación aleatoria (0.0 a 1.0)
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.jitter = jitter
        
        # Diccionario para almacenar retrasos por dominio
        self.domain_delays: Dict[str, float] = {}
        
        # Diccionario para almacenar timestamps de últimas solicitudes por dominio
        self.last_request_time: Dict[str, float] = {}
        
        logger.info(f"Inicializado AdaptiveDelay con retraso inicial={initial_delay}s, máximo={max_delay}s, jitter={jitter}")
    
    async def wait(self, domain: Optional[str] = None) -> None:
        """
        Espera el tiempo adecuado antes de realizar una solicitud.
        
        Args:
            domain: Dominio para el que se realiza la solicitud (opcional)
        """
        # Si no se especifica un dominio, usar un valor predeterminado
        domain = domain or "default"
        
        # Obtener el retraso actual para este dominio
        current_delay = self.domain_delays.get(domain, self.initial_delay)
        
        # Aplicar jitter (variación aleatoria)
        jitter_amount = current_delay * self.jitter
        actual_delay = current_delay + random.uniform(-jitter_amount, jitter_amount)
        actual_delay = max(0.1, actual_delay)  # Asegurar un mínimo de 0.1 segundos
        
        # Calcular el tiempo transcurrido desde la última solicitud
        now = time.time()
        last_time = self.last_request_time.get(domain, 0)
        elapsed = now - last_time
        
        # Si no ha pasado suficiente tiempo, esperar
        if elapsed < actual_delay:
            wait_time = actual_delay - elapsed
            logger.debug(f"Esperando {wait_time:.2f}s para el dominio {domain}")
            await asyncio.sleep(wait_time)
        
        # Actualizar el timestamp de la última solicitud
        self.last_request_time[domain] = time.time()
    
    def increase_delay(self, domain: Optional[str] = None) -> None:
        """
        Aumenta el retraso para un dominio específico (por ejemplo, después de un error).
        
        Args:
            domain: Dominio para el que se aumenta el retraso
        """
        domain = domain or "default"
        current_delay = self.domain_delays.get(domain, self.initial_delay)
        
        # Aumentar el retraso (por ejemplo, duplicarlo)
        new_delay = min(current_delay * 2.0, self.max_delay)
        self.domain_delays[domain] = new_delay
        
        logger.info(f"Aumentado retraso para {domain} a {new_delay:.2f}s")
    
    def decrease_delay(self, domain: Optional[str] = None) -> None:
        """
        Disminuye el retraso para un dominio específico (por ejemplo, después de un éxito).
        
        Args:
            domain: Dominio para el que se disminuye el retraso
        """
        domain = domain or "default"
        current_delay = self.domain_delays.get(domain, self.initial_delay)
        
        # Disminuir el retraso (por ejemplo, reducirlo a la mitad)
        new_delay = max(current_delay * 0.5, self.initial_delay)
        self.domain_delays[domain] = new_delay
        
        logger.debug(f"Disminuido retraso para {domain} a {new_delay:.2f}s")
    
    def reset_delay(self, domain: Optional[str] = None) -> None:
        """
        Restablece el retraso para un dominio específico al valor inicial.
        
        Args:
            domain: Dominio para el que se restablece el retraso
        """
        domain = domain or "default"
        self.domain_delays[domain] = self.initial_delay
        
        logger.info(f"Restablecido retraso para {domain} a {self.initial_delay:.2f}s")
    
    def get_current_delay(self, domain: Optional[str] = None) -> float:
        """
        Obtiene el retraso actual para un dominio específico.
        
        Args:
            domain: Dominio para el que se obtiene el retraso
            
        Returns:
            Retraso actual en segundos
        """
        domain = domain or "default"
        return self.domain_delays.get(domain, self.initial_delay)
