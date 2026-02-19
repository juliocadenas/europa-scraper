"""
Scraper Controller Base
----------------------
Clase base para el controlador de scraping.
"""

import logging
import asyncio
from typing import Dict, Any, Callable, List, Optional

logger = logging.getLogger(__name__)

class ScraperControllerBase:
    """Clase base para el controlador de scraping."""
    
    def __init__(self):
        """Inicializa el controlador base."""
        self.stop_requested = False
    
    async def run_scraping(self, params: Dict[str, Any], progress_callback: Optional[Callable] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Ejecuta el proceso de scraping.
        
        Args:
            params: Parámetros de scraping
            progress_callback: Callback para actualizaciones de progreso
            **kwargs: Otros argumentos opcionales (worker_id, batch, etc.)
            
        Returns:
            Lista de diccionarios de resultados
        """
        # Este método debe ser implementado por las clases derivadas
        raise NotImplementedError("Este método debe ser implementado por las clases derivadas")
    
    def stop_scraping(self):
        """Detiene el proceso de scraping."""
        self.stop_requested = True
        logger.info("Detención solicitada por el usuario")
