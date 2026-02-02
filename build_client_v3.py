
import os
import subprocess
import sys

def build_client():
    print("🚀 Preparando la compilación del cliente...")

    # Asegurarse de que PyInstaller esté instalado
    try:
        import PyInstaller
    except ImportError:
        print("📦 Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Definir rutas
    project_root = os.path.dirname(os.path.abspath(__file__))
    entry_point = os.path.join(project_root, "client", "main.py")
    
    # Comando de PyInstaller
    # --onefile: Genera un solo archivo .exe
    # --noconsole: No abre ventana de comandos al iniciar (solo el GUI)
    # --add-data: Incluye archivos de configuración y módulos necesarios
    
    # En Windows el separador de add-data es ';'
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name=Docuscraper_Client",
        f"--add-data=client/config.json;client",
        f"--add-data=client/server_config.json;client",
        # Incluir directorios necesarios
        f"--add-data=gui;gui",
        f"--add-data=utils;utils",
        # Punto de entrada
        entry_point
    ]

    print(f"🛠️  Ejecutando: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ COMPILACIÓN COMPLETADA EXITOSAMENTE")
        print("📂 Puedes encontrar el archivo en: dist\\Docuscraper_Client.exe")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error durante la compilación: {e}")

if __name__ == "__main__":
    build_client()
