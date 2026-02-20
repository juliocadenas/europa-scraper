#!/bin/bash

# ====================================
#   INICIANDO SERVIDOR EUROPA SCRAPER (WSL)
# ====================================

echo "🚀 Iniciando servidor Europa Scraper en WSL optimizado..."

# Optimizar memoria para WSL
echo "🔧 Optimizando memoria para WSL..."

# Variables de optimización
export PYTHONOPTIMIZE=1
export MALLOC_TRIM_THRESHOLD_=100000
export MALLOC_ARENA_MAX=131072

# Limitar uso de memoria si es necesario
ulimit -vS 1048576 2>/dev/null

# Limpiar procesos Python anteriores
echo "🧹 Limpiando procesos Python anteriores..."
pkill -f "python.*iniciar_servidor" 2>/dev/null
sleep 2

# Cambiar al directorio del proyecto
echo "📁 Cambiando al directorio del proyecto..."
cd "$(dirname "$0")"

# Iniciar el servidor corregido
echo "🚀 Iniciando servidor corregido..."
python3 iniciar_servidor_corregido.py

echo "✅ Servidor detenido"