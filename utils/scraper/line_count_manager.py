"""
LineCountManager: Gestiona el conteo de líneas de archivos CSV en background.
Actualiza el conteo periódicamente sin bloquear el hilo principal del GUI.
"""

import os
import threading
import logging
import time
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class LineCountManager:
    """
    Gestiona el conteo de líneas de todos los archivos CSV en la carpeta results.
    Opera en un hilo de fondo para no bloquear la UI.
    """

    def __init__(self, results_dir: Optional[str] = None):
        self._counts: Dict[str, int] = {}  # {filepath: line_count}
        self._total_lines: int = 0
        self._lock = threading.Lock()
        self._callback: Optional[Callable] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._interval = 30.0
        self._batch_size = 5

        # Detectar la carpeta results automáticamente
        if results_dir:
            self._results_dir = results_dir
        else:
            # Intentar encontrar la carpeta results o server/results relativa al script
            base = os.path.dirname(os.path.abspath(__file__))
            # Subir hasta la raíz del proyecto
            found = False
            for _ in range(4):
                candidate_server = os.path.join(base, "server", "results")
                candidate_root = os.path.join(base, "results")
                
                # Preferir server/results si existe y tiene archivos, sino usar results normal
                if os.path.isdir(candidate_server):
                    self._results_dir = candidate_server
                    found = True
                    break
                elif os.path.isdir(candidate_root):
                    self._results_dir = candidate_root
                    found = True
                    break
                base = os.path.dirname(base)
                
            if not found:
                self._results_dir = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "..", "..", "results"
                )

        logger.info(f"LineCountManager: carpeta results = {self._results_dir}")

    def set_callback(self, callback: Callable):
        """Establece la función callback que se llama cuando hay actualizaciones."""
        self._callback = callback

    def start(self, interval: float = 30.0, batch_size: int = 5):
        """Inicia el hilo de conteo en background."""
        if self._running:
            return
        self._interval = interval
        self._batch_size = batch_size
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="LineCountManager-Thread"
        )
        self._thread.start()
        logger.info("LineCountManager iniciado en background.")

    def stop(self):
        """Detiene el hilo de conteo."""
        self._running = False
        logger.info("LineCountManager detenido.")

    def get_total_lines(self) -> int:
        """Retorna el total de líneas contadas en todos los CSV."""
        with self._lock:
            return self._total_lines

    def get_all_counts(self) -> Dict[str, int]:
        """Retorna el diccionario completo {filepath: count}."""
        with self._lock:
            return dict(self._counts)

    def _run_loop(self):
        """Bucle principal del hilo de background."""
        # Primera pasada inmediata
        self._scan_files()

        while self._running:
            time.sleep(self._interval)
            if not self._running:
                break
            self._scan_files()

    def _scan_files(self):
        """Escanea los archivos CSV y actualiza los conteos."""
        if not os.path.isdir(self._results_dir):
            logger.warning(f"LineCountManager: carpeta no encontrada: {self._results_dir}")
            return

        try:
            csv_files = [
                os.path.join(self._results_dir, f)
                for f in os.listdir(self._results_dir)
                if f.lower().endswith(".csv")
            ]
        except Exception as e:
            logger.error(f"LineCountManager: error listando archivos: {e}")
            return

        new_counts = {}
        total = 0

        for fpath in csv_files:
            try:
                count = self._count_lines(fpath)
                new_counts[fpath] = count
                total += count
            except Exception as e:
                logger.debug(f"LineCountManager: error contando {fpath}: {e}")
                new_counts[fpath] = 0

        with self._lock:
            self._counts = new_counts
            self._total_lines = total

        logger.debug(f"LineCountManager: {len(csv_files)} archivos, {total:,} líneas totales")

        # Notificar al callback si existe
        if self._callback:
            try:
                status_dict = {
                    "total_lines": total,
                    "file_count": len(csv_files),
                    "counts": new_counts,
                }
                self._callback(status_dict)
            except Exception as e:
                logger.error(f"LineCountManager: error en callback: {e}")

    def _count_lines(self, fpath: str) -> int:
        """Cuenta las líneas de un archivo CSV de forma eficiente."""
        count = 0
        try:
            with open(fpath, "rb") as f:
                # Leer en chunks para mayor eficiencia con archivos grandes
                buf_size = 1024 * 1024  # 1MB
                buf = f.read(buf_size)
                while buf:
                    count += buf.count(b"\n")
                    buf = f.read(buf_size)
            # Restar 1 por la cabecera si el archivo tiene contenido
            if count > 0:
                count -= 1
        except Exception:
            count = 0
        return max(0, count)


# Instancia global singleton para importar desde cualquier módulo
line_count_manager = LineCountManager()
