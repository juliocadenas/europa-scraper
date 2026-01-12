#!/bin/bash
echo "========================================="
echo "  INICIANDO SERVIDOR WSL CORREGIDO"
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
if [ -d "venv_wsl_corregido" ]; then
    echo "Activando entorno virtual corregido..."
    source venv_wsl_corregido/bin/activate
else
    echo "ℹ️ Creando entorno virtual corregido..."
    python3 -m venv venv_wsl_corregido
    source venv_wsl_corregido/bin/activate
    
    # Instalar dependencias mínimas
    pip install fastapi uvicorn
fi

echo "Iniciando servidor WSL corregido..."
cd server
python main_wsl_corregido.py