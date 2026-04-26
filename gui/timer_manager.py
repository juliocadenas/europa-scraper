"""
Timer Manager
------------
Gestiona el temporizador para el scraping.
MEJORADO: Ahora soporta sincronización con el servidor para que el timer
persista aunque el cliente se cierre y se vuelva a abrir.
"""

import time
import threading
import logging

logger = logging.getLogger(__name__)

class TimerManager:
    """Gestiona el temporizador para el scraping con soporte de sincronización del servidor."""
    
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
        
        # NUEVO: Tiempo del servidor (persistente entre reinicios del cliente)
        self._server_accumulated_time = 0
        self._server_start_time_str = None
        self._use_server_time = False  # Bandera para usar tiempo del servidor
    
    def start(self):
        """Inicia el temporizador local."""
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

    def sync_from_server(self, accumulated_time, start_time_str=None):
        """
        Sincroniza el timer con los datos del servidor.
        Esto permite que el timer siga mostrando el tiempo correcto
        incluso si el cliente se cerró y se volvió a abrir.
        
        Args:
            accumulated_time: Segundos transcurridos según el servidor
            start_time_str: Cadena ISO de la hora de inicio del servidor
        """
        self._server_accumulated_time = accumulated_time
        self._server_start_time_str = start_time_str
        self._use_server_time = True
        
        # Si el timer local no está corriendo pero hay tiempo del servidor,
        # forzar actualización de la UI inmediatamente
        if not self.timer_running and accumulated_time > 0:
            self._format_and_emit(accumulated_time, start_time_str)

    def _format_and_emit(self, total_seconds, start_time_str=None):
        """Formatea el tiempo y lo envía al callback."""
        hours, remainder = divmod(int(total_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Construir cadena con hora de inicio si está disponible
        if start_time_str:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(start_time_str)
                start_display = f" | Inicio: {dt.strftime('%H:%M:%S (%d/%m)')}"
            except (ValueError, TypeError):
                start_display = ""
        else:
            start_display = ""
        
        time_str = f"⏱ {hours:02}:{minutes:02}:{seconds:02}{start_display}"
        
        if self.update_callback:
            self.update_callback(time_str)
    
    def _update_timer(self):
        """Actualiza el temporizador en un hilo separado."""
        while self.timer_running:
            if self._use_server_time and self._server_accumulated_time > 0:
                # Usar tiempo del servidor (más preciso y persistente)
                # El servidor ya calcula el tiempo acumulado correctamente
                self._format_and_emit(
                    self._server_accumulated_time, 
                    self._server_start_time_str
                )
            else:
                # Fallback: usar timer local
                self.elapsed_time = time.time() - self.start_time
                self._format_and_emit(self.elapsed_time)
            
            time.sleep(1)
