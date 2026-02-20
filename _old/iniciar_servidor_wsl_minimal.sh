#!/bin/bash
echo "========================================="
echo "  INICIANDO SERVIDOR WSL MINIMAL"
echo "========================================="
echo

# Detectar WSL
if grep -q Microsoft /proc/version; then
    echo "✅ WSL detectado"
    export DISPLAY=:99
else
    echo "ℹ️ WSL no detectado"
fi

# Activar entorno virtual
if [ -d "venv_wsl_minimal" ]; then
    echo "Activando entorno virtual minimal..."
    source venv_wsl_minimal/bin/activate
else
    echo "❌ Entorno virtual minimal no encontrado"
    exit 1
fi

echo "Iniciando servidor minimal..."
cd server
python main_wsl_minimal.py
