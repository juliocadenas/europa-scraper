#!/bin/bash
echo "========================================="
echo "  INICIANDO SERVIDOR WSL DEFINITIVO"
echo "========================================="
echo

# Detectar WSL
if grep -q Microsoft /proc/version 2>/dev/null; then
    echo "✅ WSL detectado"
    export DISPLAY=:99
else
    echo "ℹ️ WSL no detectado (ejecutando desde Windows)"
fi

# Activar entorno virtual si existe
if [ -d "venv_wsl_definitivo" ]; then
    echo "Activando entorno virtual definitivo..."
    source venv_wsl_definitivo/bin/activate
else
    echo "ℹ️ Creando entorno virtual definitivo..."
    python3 -m venv venv_wsl_definitivo
    source venv_wsl_definitivo/bin/activate
    
    # Instalar dependencias mínimas
    pip install fastapi uvicorn
fi

echo "Iniciando servidor WSL definitivo..."
cd server
python main_wsl_definitivo.py
