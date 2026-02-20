#!/bin/bash

# ==============================================================================
# Script para ejecutar en el SERVIDOR REMOTO - Corrección columnas CSV
# ==============================================================================
# Ejecutar este script en el servidor Ubuntu:
#   cd /opt/docuscraper && ./actualizar_servidor_remoto_columnas.sh
# ==============================================================================

echo "🔧 Actualizando servidor remoto - Corrección columnas CSV..."

# 1. Ir al directorio del proyecto
cd /opt/docuscraper

# 2. Detener el contenedor Docker
echo "🐳 Deteniendo contenedor Docker..."
docker compose down

# 3. Actualizar código desde GitHub
echo "📥 Actualizando código desde GitHub..."
git fetch origin
git reset --hard origin/patch-monitor

# 4. Limpiar caché de Python completamente
echo "🧹 Limpiando caché de Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "  ✅ Caché limpiada"

# 5. Verificar que el código correcto está presente
echo "📝 Verificando código de result_manager.py..."
if grep -q "filtered_result = {}" utils/scraper/result_manager.py; then
    echo "  ✅ Código de filtrado presente en result_manager.py"
else
    echo "  ❌ ERROR: El código de filtrado NO está presente"
    exit 1
fi

# 6. Verificar CSV_COLUMNS
if grep -q "'lang'" utils/scraper/result_manager.py; then
    echo "  ✅ Columna 'lang' presente en CSV_COLUMNS"
else
    echo "  ❌ ERROR: Columna 'lang' NO encontrada"
    exit 1
fi

# 7. Reconstruir el contenedor Docker SIN caché
echo "🐳 Reconstruyendo contenedor Docker (sin caché)..."
docker compose build --no-cache
docker compose up -d

# 8. Verificar que el servidor está funcionando
echo "🔍 Verificando servidor..."
sleep 5
if curl -s http://localhost:8001/api/ping > /dev/null; then
    echo "  ✅ Servidor funcionando correctamente"
else
    echo "  ⚠️  El servidor puede estar iniciando, verifica con: docker compose logs -f"
fi

echo "===================================================================="
echo "✅ ACTUALIZACIÓN COMPLETADA"
echo "===================================================================="
echo "El servidor ha sido actualizado con la corrección de columnas CSV."
echo ""
echo "Las columnas del CSV ahora serán SOLO:"
echo "  - sic_code"
echo "  - course_name"
echo "  - title"
echo "  - description"
echo "  - url"
echo "  - total_words"
echo "  - lang"
echo ""
echo "Comandos útiles:"
echo " - Ver logs: docker compose logs -f"
echo " - Verificar: curl http://localhost:8001/api/ping"
echo "===================================================================="
