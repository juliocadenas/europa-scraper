#!/bin/bash
echo "========================================="
echo "  INICIANDO SERVIDOR WSL ABSOLUTO"
echo "========================================="
echo

# Detectar WSL
if grep -q Microsoft /proc/version 2>/dev/null; then
    echo "✅ WSL detectado"
    export DISPLAY=:99
else
    echo "ℹ️ WSL no detectado (ejecutando desde Windows)"
fi

# Activar entorno virtual
echo "Activando entorno virtual absoluto..."
source venv_wsl_absoluto/bin/activate

echo "Iniciando servidor WSL absoluto..."
cd server
python main_wsl_corregido.py
