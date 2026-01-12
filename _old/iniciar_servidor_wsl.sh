#!/bin/bash

# Script para iniciar el servidor en WSL
# =====================================

echo "🚀 Iniciando servidor en WSL..."

# Navegar al directorio del proyecto
cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX

# Activar entorno virtual de WSL
source venv_wsl/bin/activate

# Verificar que el entorno está activado
echo "📋 Entorno virtual activado: $(which python)"

# Iniciar el servidor
echo "🌐 Iniciando servidor en http://0.0.0.0:8001"
python server/main.py

echo "✅ Servidor iniciado correctamente"