#!/bin/bash
echo "========================================="
echo "  INICIANDO SERVIDOR WSL FINAL"
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
echo "Activando entorno virtual final..."
source venv_wsl/bin/activate

echo "Iniciando servidor WSL final..."
cd server
python main_wsl_real.py
