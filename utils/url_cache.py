import os
import logging
import hashlib
import time
import shutil
import tempfile
from typing import Dict, Optional, Any, Tuple
import json

logger = logging.getLogger(__name__)

class URLCache:
    """
    Implementa un sistema de caché para URLs y archivos descargados.
    """
    
    def __init__(self, cache_dir: Optional[str] = None, max_age: int = 86400, max_size: int = 1024 * 1024 * 100):
        """
        Inicializa el sistema de caché.
        
        Args:
            cache_dir: Directorio para almacenar la caché (opcional)
            max_age: Tiempo máximo de vida de los elementos en caché en segundos (por defecto: 1 día)
            max_size: Tamaño máximo de la caché en bytes (por defecto: 100 MB)
        """
        # Si no se especifica un directorio, usar un subdirectorio en el directorio temporal
        if cache_dir is None:
            cache_dir = os.path.join(tempfile.gettempdir(), "url_cache")
        
        self.cache_dir = cache_dir
        self.max_age = max_age
        self.max_size = max_size
        
        # Crear el directorio de caché si no existe
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Directorio para archivos
        self.files_dir = os.path.join(self.cache_dir, "files")
        os.makedirs(self.files_dir, exist_ok=True)
        
        # Directorio para metadatos
        self.meta_dir = os.path.join(self.cache_dir, "meta")
        os.makedirs(self.meta_dir, exist_ok=True)
        
        # Cargar el índice de caché
        self.cache_index: Dict[str, Dict[str, Any]] = self._load_cache_index()
        
        logger.info(f"Inicializado URLCache en {self.cache_dir} (max_age={max_age}s, max_size={max_size/1024/1024:.1f}MB)")
        
        # Limpiar la caché al inicio
        self._clean_cache()
    
    def _load_cache_index(self) -> Dict[str, Dict[str, Any]]:
        """
        Carga el índice de caché desde el disco.
        
        Returns:
            Diccionario con el índice de caché
        """
        index_path = os.path.join(self.cache_dir, "index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando índice de caché: {str(e)}")
        
        return {}
    
    def _save_cache_index(self) -> None:
        """
        Guarda el índice de caché en el disco.
        """
        index_path = os.path.join(self.cache_dir, "index.json")
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache_index, f)
        except Exception as e:
            logger.error(f"Error guardando índice de caché: {str(e)}")
    
    def _get_cache_key(self, url: str) -> str:
        """
        Genera una clave de caché para una URL.
        
        Args:
            url: URL para la que se genera la clave
            
        Returns:
            Clave de caché (hash MD5 de la URL)
        """
        return hashlib.md5(url.encode('utf-8')).hexdigest()
    
    def _clean_cache(self) -> None:
        """
        Limpia la caché eliminando elementos antiguos o si se supera el tamaño máximo.
        """
        try:
            # Eliminar elementos caducados
            now = time.time()
            expired_keys = []
            
            for key, meta in self.cache_index.items():
                if now - meta.get('timestamp', 0) > self.max_age:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_from_cache(key)
            
            # Verificar el tamaño total de la caché
            total_size = 0
            items = []
            
            for key, meta in self.cache_index.items():
                size = meta.get('size', 0)
                timestamp = meta.get('timestamp', 0)
                items.append((key, size, timestamp))
                total_size += size
            
            # Si se supera el tamaño máximo, eliminar los elementos más antiguos
            if total_size > self.max_size:
                # Ordenar por timestamp (más antiguo primero)
                items.sort(key=lambda x: x[2])
                
                # Eliminar elementos hasta que el tamaño sea aceptable
                for key, size, _ in items:
                    self._remove_from_cache(key)
                    total_size -= size
                    if total_size <= self.max_size * 0.8:  # Dejar un margen del 20%
                        break
            
            logger.info(f"Limpieza de caché completada. Tamaño actual: {total_size/1024/1024:.1f}MB")
        
        except Exception as e:
            logger.error(f"Error limpiando caché: {str(e)}")
    
    def _remove_from_cache(self, key: str) -> None:
        """
        Elimina un elemento de la caché.
        
        Args:
            key: Clave del elemento a eliminar
        """
        try:
            meta = self.cache_index.get(key, {})
            
            # Eliminar archivo
            file_path = meta.get('file_path')
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
            
            # Eliminar metadatos
            meta_path = os.path.join(self.meta_dir, f"{key}.json")
            if os.path.exists(meta_path):
                os.unlink(meta_path)
            
            # Eliminar del índice
            if key in self.cache_index:
                del self.cache_index[key]
            
            logger.debug(f"Eliminado elemento de caché: {key}")
        
        except Exception as e:
            logger.error(f"Error eliminando elemento de caché {key}: {str(e)}")
    
    def put_file(self, url: str, file_path: str) -> None:
        """
        Añade un archivo a la caché.
        
        Args:
            url: URL asociada al archivo
            file_path: Ruta al archivo
        """
        try:
            key = self._get_cache_key(url)
            
            # Crear una copia del archivo en el directorio de caché
            cache_file_path = os.path.join(self.files_dir, key)
            shutil.copy2(file_path, cache_file_path)
            
            # Obtener el tamaño del archivo
            size = os.path.getsize(cache_file_path)
            
            # Guardar metadatos
            meta = {
                'url': url,
                'file_path': cache_file_path,
                'timestamp': time.time(),
                'size': size
            }
            
            # Guardar en el índice
            self.cache_index[key] = meta
            
            # Guardar metadatos en un archivo separado
            meta_path = os.path.join(self.meta_dir, f"{key}.json")
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f)
            
            # Guardar el índice
            self._save_cache_index()
            
            logger.debug(f"Archivo añadido a caché: {url} -> {cache_file_path}")
        
        except Exception as e:
            logger.error(f"Error añadiendo archivo a caché para {url}: {str(e)}")
    
    def get_file(self, url: str) -> Optional[str]:
        """
        Obtiene un archivo de la caché.
        
        Args:
            url: URL asociada al archivo
            
        Returns:
            Ruta al archivo en caché o None si no está en caché
        """
        try:
            key = self._get_cache_key(url)
            
            # Verificar si está en caché
            if key not in self.cache_index:
                return None
            
            meta = self.cache_index[key]
            file_path = meta.get('file_path')
            
            # Verificar si el archivo existe
            if not file_path or not os.path.exists(file_path):
                # Eliminar de la caché si el archivo no existe
                self._remove_from_cache(key)
                return None
            
            # Verificar si ha caducado
            timestamp = meta.get('timestamp', 0)
            if time.time() - timestamp > self.max_age:
                # Eliminar de la caché si ha caducado
                self._remove_from_cache(key)
                return None
            
            # Actualizar el timestamp
            meta['timestamp'] = time.time()
            self.cache_index[key] = meta
            
            # Guardar metadatos actualizados
            meta_path = os.path.join(self.meta_dir, f"{key}.json")
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f)
            
            logger.debug(f"Archivo obtenido de caché: {url} -> {file_path}")
            
            return file_path
        
        except Exception as e:
            logger.error(f"Error obteniendo archivo de caché para {url}: {str(e)}")
            return None
    
    def get(self, url: str) -> Optional[str]:
        """
        Obtiene el contenido en caché para una URL.
        
        Args:
            url: URL a buscar en la caché
            
        Returns:
            Contenido en caché o None si no está en caché
        """
        try:
            key = self._get_cache_key(url)
            
            # Verificar si está en caché
            if key not in self.cache_index:
                return None
            
            meta = self.cache_index[key]
            
            # Verificar si ha caducado
            timestamp = meta.get('timestamp', 0)
            if time.time() - timestamp > self.max_age:
                # Eliminar de la caché si ha caducado
                self._remove_from_cache(key)
                return None
            
            # Obtener el contenido
            content_path = os.path.join(self.files_dir, f"{key}.content")
            if not os.path.exists(content_path):
                return None
            
            # Leer el contenido
            with open(content_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Actualizar el timestamp
            meta['timestamp'] = time.time()
            self.cache_index[key] = meta
            
            # Guardar metadatos actualizados
            meta_path = os.path.join(self.meta_dir, f"{key}.json")
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f)
            
            logger.debug(f"Contenido obtenido de caché: {url}")
            
            return content
        
        except Exception as e:
            logger.error(f"Error obteniendo contenido de caché para {url}: {str(e)}")
            return None
    
    def put(self, url: str, content: str) -> None:
        """
        Añade contenido a la caché.
        
        Args:
            url: URL asociada al contenido
            content: Contenido a guardar
        """
        try:
            key = self._get_cache_key(url)
            
            # Guardar el contenido
            content_path = os.path.join(self.files_dir, f"{key}.content")
            with open(content_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(content)
            
            # Obtener el tamaño del contenido
            size = len(content.encode('utf-8'))
            
            # Guardar metadatos
            meta = {
                'url': url,
                'content_path': content_path,
                'timestamp': time.time(),
                'size': size
            }
            
            # Guardar en el índice
            self.cache_index[key] = meta
            
            # Guardar metadatos en un archivo separado
            meta_path = os.path.join(self.meta_dir, f"{key}.json")
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f)
            
            # Guardar el índice
            self._save_cache_index()
            
            logger.debug(f"Contenido añadido a caché: {url}")
        
        except Exception as e:
            logger.error(f"Error añadiendo contenido a caché para {url}: {str(e)}")
    
    def invalidate(self, url: str) -> None:
        """
        Invalida una URL en la caché.
        
        Args:
            url: URL a invalidar
        """
        key = self._get_cache_key(url)
        self._remove_from_cache(key)
        logger.debug(f"Invalidada URL en caché: {url}")
    
    def clear(self) -> None:
        """
        Limpia toda la caché.
        """
        try:
            # Eliminar todos los archivos
            for key in list(self.cache_index.keys()):
                self._remove_from_cache(key)
            
            # Limpiar el índice
            self.cache_index = {}
            self._save_cache_index()
            
            logger.info("Caché limpiada completamente")
        
        except Exception as e:
            logger.error(f"Error limpiando caché: {str(e)}")
