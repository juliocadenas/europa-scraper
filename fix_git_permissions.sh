#!/bin/bash

# ==============================================================================
# Script para arreglar permisos de git y actualizar el servidor
# ==============================================================================

echo "🔧 Arreglando permisos de git..."

# 1. Arreglar permisos del directorio .git
sudo chown -R $USER:$USER /opt/docuscraper/.git
sudo chmod -R 755 /opt/docuscraper/.git

# 2. Ir al directorio del proyecto
cd /opt/docuscraper

# 3. Actualizar código desde GitHub
echo "📥 Actualizando código desde GitHub..."
git fetch origin
git reset --hard origin/patch-monitor

# 4. Verificar que el código se actualizó
echo "📝 Verificando código de result_manager.py..."
if grep -q "filtered_result = {}" utils/scraper/result_manager.py; then
    echo "  ✅ Código de filtrado presente en result_manager.py"
else
    echo "  ❌ ERROR: El código de filtrado NO está presente"
    exit 1
fi

# 5. Limpiar caché de Python
echo "🧹 Limpiando caché de Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# 6. Reconstruir contenedor Docker
echo "🐳 Reconstruyendo contenedor Docker..."
docker compose down
docker compose build --no-cache
docker compose up -d

# 7. Verificar servidor
echo "🔍 Verificando servidor..."
sleep 5
curl -s http://localhost:8001/api/ping

echo ""
echo "===================================================================="
echo "✅ ACTUALIZACIÓN COMPLETADA"
echo "===================================================================="
