#!/bin/bash

# ==============================================================================
# Script para actualizar el servidor remoto - CORRECCIÓN COLUMNAS CSV
# ==============================================================================
# Este script asegura que el servidor tenga el código correcto que filtra
# las columnas del CSV para incluir SOLO las columnas INAMOVIBLES.
# ==============================================================================

echo "🔧 Actualizando servidor remoto - Corrección columnas CSV..."

# 1. Limpiar caché de Python completamente
echo "🧹 Limpiando caché de Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "  ✅ Caché limpiada"

# 2. Verificar que el código correcto está presente
echo "📝 Verificando código de result_manager.py..."
if grep -q "filtered_result = {}" utils/scraper/result_manager.py; then
    echo "  ✅ Código de filtrado presente en result_manager.py"
else
    echo "  ❌ ERROR: El código de filtrado NO está presente"
    exit 1
fi

# 3. Verificar CSV_COLUMNS
if grep -q "CSV_COLUMNS = \[" utils/scraper/result_manager.py; then
    echo "  ✅ CSV_COLUMNS definido correctamente"
else
    echo "  ❌ ERROR: CSV_COLUMNS no encontrado"
    exit 1
fi

# 4. Detener el contenedor Docker
echo "🐳 Deteniendo contenedor Docker..."
docker compose down
echo "  ✅ Contenedor detenido"

# 5. Reconstruir el contenedor Docker SIN caché
echo "🐳 Reconstruyendo contenedor Docker (sin caché)..."
docker compose build --no-cache
docker compose up -d

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
