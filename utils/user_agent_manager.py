import random
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class UserAgentManager:
    """
    Gestiona una lista de User-Agents y proporciona métodos para obtener User-Agents aleatorios.
    """
    
    def __init__(self):
        """
        Inicializa el gestor de User-Agents.
        """
        # Lista actualizada de User-Agents comunes (2024-2025)
        self.desktop_user_agents = [
            # Chrome (actualizados)
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",

            # Firefox (actualizados)
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",

            # Safari (actualizados)
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",

            # Edge (actualizados)
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",

            # Opera
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 OPR/115.0.0.0",

            # Brave
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        ]
        
        self.mobile_user_agents = [
            # Android (actualizados)
            "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/18.0 Chrome/99.0.4844.88 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; SM-S916B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",

            # iOS (actualizados)
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
        ]
        
        self.tablet_user_agents = [
            # iPad
            "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
            
            # Android Tablet
            "Mozilla/5.0 (Linux; Android 11; SM-T870) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Safari/537.36",
            "Mozilla/5.0 (Linux; Android 10; SM-T500) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.115 Safari/537.36"
        ]
        
        # Combinar todas las listas
        self.all_user_agents = self.desktop_user_agents + self.mobile_user_agents + self.tablet_user_agents

        # Track recently used user agents to avoid patterns
        self.recently_used = []
        self.max_recent = 10  # Keep track of last 10 used agents

        logger.info(f"Inicializado UserAgentManager con {len(self.all_user_agents)} User-Agents")
    
    def get_random_user_agent(self, device_type: Optional[str] = None) -> str:
        """
        Obtiene un User-Agent aleatorio intentando evitar los usados recientemente.

        Args:
            device_type: Tipo de dispositivo ('desktop', 'mobile', 'tablet', o None para cualquiera)

        Returns:
            User-Agent aleatorio
        """
        # Get the appropriate pool
        if device_type == 'desktop':
            pool = self.desktop_user_agents
        elif device_type == 'mobile':
            pool = self.mobile_user_agents
        elif device_type == 'tablet':
            pool = self.tablet_user_agents
        else:
            pool = self.all_user_agents

        # Try to find a user agent that hasn't been recently used
        attempts = 0
        max_attempts = len(pool)

        while attempts < max_attempts:
            candidate = random.choice(pool)
            if candidate not in self.recently_used:
                # Add to recently used
                self.recently_used.append(candidate)
                if len(self.recently_used) > self.max_recent:
                    self.recently_used.pop(0)  # Remove oldest
                logger.debug(f"Selected fresh user agent: {candidate[:60]}...")
                return candidate
            attempts += 1

        # If all have been recently used, just return a random one
        candidate = random.choice(pool)
        logger.debug(f"Using recently used user agent: {candidate[:60]}...")
        return candidate
    
    def get_all_user_agents(self, device_type: Optional[str] = None) -> List[str]:
        """
        Obtiene todos los User-Agents disponibles.
        
        Args:
            device_type: Tipo de dispositivo ('desktop', 'mobile', 'tablet', o None para todos)
            
        Returns:
            Lista de User-Agents
        """
        if device_type == 'desktop':
            return self.desktop_user_agents.copy()
        elif device_type == 'mobile':
            return self.mobile_user_agents.copy()
        elif device_type == 'tablet':
            return self.tablet_user_agents.copy()
        else:
            return self.all_user_agents.copy()
    
    def add_user_agent(self, user_agent: str, device_type: str = 'desktop'):
        """
        Añade un User-Agent a la lista.
        
        Args:
            user_agent: User-Agent a añadir
            device_type: Tipo de dispositivo ('desktop', 'mobile', 'tablet')
        """
        if device_type == 'desktop' and user_agent not in self.desktop_user_agents:
            self.desktop_user_agents.append(user_agent)
            self.all_user_agents.append(user_agent)
            logger.info(f"User-Agent de escritorio añadido: {user_agent[:30]}...")
        elif device_type == 'mobile' and user_agent not in self.mobile_user_agents:
            self.mobile_user_agents.append(user_agent)
            self.all_user_agents.append(user_agent)
            logger.info(f"User-Agent móvil añadido: {user_agent[:30]}...")
        elif device_type == 'tablet' and user_agent not in self.tablet_user_agents:
            self.tablet_user_agents.append(user_agent)
            self.all_user_agents.append(user_agent)
            logger.info(f"User-Agent de tablet añadido: {user_agent[:30]}...")
