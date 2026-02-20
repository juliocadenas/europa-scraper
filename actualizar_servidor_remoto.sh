#!/bin/bash

# ==============================================================================
# Script para actualizar el servidor remoto - Solución error 'batch'
# ==============================================================================

echo "🔧 Actualizando servidor remoto para solucionar error 'batch'..."

# 1. Eliminar archivos duplicados que causan conflictos
echo "📁 Eliminando archivos duplicados..."

# Eliminar utils/scraper_controller.py si existe
if [ -f "utils/scraper_controller.py" ]; then
    rm -f utils/scraper_controller.py
    echo "  ✅ Eliminado: utils/scraper_controller.py"
fi

# Eliminar utils/scraper/controller.py si existe
if [ -f "utils/scraper/controller.py" ]; then
    rm -f utils/scraper/controller.py
    echo "  ✅ Eliminado: utils/scraper/controller.py"
fi

# 2. Limpiar caché de Python
echo "🧹 Limpiando caché de Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "  ✅ Caché limpiada"

# 3. Reconstruir el contenedor Docker
echo "🐳 Reconstruyendo contenedor Docker..."
docker compose down
docker compose up -d --build

echo "===================================================================="
echo "✅ ACTUALIZACIÓN COMPLETADA"
echo "===================================================================="
echo "El servidor ha sido actualizado. El error 'batch' debería estar resuelto."
echo ""
echo "Comandos útiles:"
echo " - Ver logs: docker compose logs -f"
echo " - Verificar: curl http://localhost:8001/api/ping"
echo "===================================================================="
