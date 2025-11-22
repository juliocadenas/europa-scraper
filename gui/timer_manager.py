"""
Timer Manager
------------
Gestiona el temporizador para el scraping.
"""

import time
import threading
import logging

logger = logging.getLogger(__name__)

class TimerManager:
    """Gestiona el temporizador para el scraping."""
    
    def __init__(self, update_callback=None):
        """
        Inicializa el gestor de temporizador.
        
        Args:
            update_callback: Función para actualizar la interfaz con el tiempo transcurrido
        """
        self.update_callback = update_callback
        self.timer_running = False
        self.start_time = 0
        self.elapsed_time = 0
        self.timer_thread = None
    
    def start(self):
        """Inicia el temporizador."""
        self.timer_running = True
        self.start_time = time.time()
        self.elapsed_time = 0
        self.timer_thread = threading.Thread(target=self._update_timer, daemon=True)
        self.timer_thread.start()
    
    def stop(self):
        """Detiene el temporizador."""
        if self.timer_running:
            self.timer_running = False
            logger.info("Timer detenido")
            if self.timer_thread and self.timer_thread.is_alive():
                try:
                    self.timer_thread.join(timeout=1.0)
                    if self.timer_thread.is_alive():
                        logger.warning("El hilo del timer no se detuvo correctamente")
                except Exception as e:
                    logger.error(f"Error al detener el timer: {str(e)}")
    
    def _update_timer(self):
        """Actualiza el temporizador en un hilo separado."""
        while self.timer_running:
            self.elapsed_time = time.time() - self.start_time
            hours, remainder = divmod(int(self.elapsed_time), 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"Tiempo: {hours:02}:{minutes:02}:{seconds:02}"
            
            # Llamar al callback para actualizar la interfaz
            if self.update_callback:
                self.update_callback(time_str)
            
            time.sleep(1)
