#!/bin/bash

# ====================================
#   INICIANDO FRONTEND EUROPA SCRAPER (WSL)
# ====================================

echo "🖥️  Iniciando interfaz gráfica Europa Scraper en WSL..."

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
pkill -f "python.*scraper_gui" 2>/dev/null
sleep 2

# Cambiar al directorio del proyecto
echo "📁 Cambiando al directorio del proyecto..."
cd "$(dirname "$0")"

# Esperar a que el servidor esté disponible
echo "⏳ Esperando a que el servidor esté disponible..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8001/ping > /dev/null 2>&1; then
        echo "✅ Servidor detectado en el intento $attempt"
        break
    fi
    
    echo "⏳ Intento $attempt de $max_attempts... esperando 2 segundos"
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ No se pudo detectar el servidor después de $max_attempts intentos"
    echo "🚀 Iniciando GUI de todas formas..."
else
    echo "✅ Servidor disponible, iniciando GUI..."
fi

# Iniciar la GUI
echo "🖥️  Iniciando interfaz gráfica..."
python3 gui/scraper_gui.py

echo "✅ Frontend detenido"