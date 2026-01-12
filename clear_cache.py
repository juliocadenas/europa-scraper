import os
import shutil

def clear_pycache(root_dir):
    """
    Finds and removes all __pycache__ directories within a given directory.
    """
    for root, dirs, files in os.walk(root_dir):
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            print(f"Eliminando: {pycache_path}")
            try:
                shutil.rmtree(pycache_path)
                print(f"Eliminado con éxito.")
            except OSError as e:
                print(f"Error eliminando {pycache_path}: {e}")

if __name__ == "__main__":
    project_directory = os.path.dirname(os.path.abspath(__file__))
    print(f"Iniciando limpieza de la caché de Python en: {project_directory}")
    clear_pycache(project_directory)
    print("\nLimpieza completada.")
