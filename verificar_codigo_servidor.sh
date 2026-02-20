#!/bin/bash

# ==============================================================================
# Script para VERIFICAR y ACTUALIZAR el código en el servidor remoto
# ==============================================================================
# Ejecutar en el servidor Ubuntu: cd /opt/docuscraper && ./verificar_codigo_servidor.sh
# ==============================================================================

echo "🔍 VERIFICANDO CÓDIGO EN EL SERVIDOR..."

# 1. Verificar que el código de filtrado está presente
echo ""
echo "📝 Verificando result_manager.py..."
if grep -q "filtered_result = {}" utils/scraper/result_manager.py; then
    echo "  ✅ Código de filtrado presente"
else
    echo "  ❌ CÓDIGO DE FILTRADO NO ENCONTRADO - ACTUALIZANDO..."
    sudo chown -R $USER:$USER /opt/docuscraper/.git
    sudo chmod -R 755 /opt/docuscraper/.git
    git fetch origin
    git reset --hard origin/patch-monitor
fi

# 2. Verificar CSV_COLUMNS
echo ""
echo "📝 Verificando CSV_COLUMNS..."
if grep -q "'lang'" utils/scraper/result_manager.py; then
    echo "  ✅ Columna 'lang' presente en CSV_COLUMNS"
else
    echo "  ❌ COLUMNA 'lang' NO ENCONTRADA - ACTUALIZANDO..."
    git fetch origin
    git reset --hard origin/patch-monitor
fi

# 3. Verificar _process_single_result
echo ""
echo "📝 Verificando _process_single_result en scraper_controller.py..."
if grep -q "'lang': result.get('lang'" controllers/scraper_controller.py; then
    echo "  ✅ Código de lang presente en _process_single_result"
else
    echo "  ❌ CÓDIGO DE LANG NO ENCONTRADO - ACTUALIZANDO..."
    git fetch origin
    git reset --hard origin/patch-monitor
fi

# 4. Mostrar las columnas que se van a escribir
echo ""
echo "📊 COLUMNAS QUE SE ESCRIBIRÁN EN EL CSV:"
echo "   - sic_code"
echo "   - course_name"
echo "   - title"
echo "   - description"
echo "   - url"
echo "   - total_words"
echo "   - lang"

# 5. Limpiar caché de Python
echo ""
echo "🧹 Limpiando caché de Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "  ✅ Caché limpiada"

# 6. Reconstruir contenedor Docker
echo ""
echo "🐳 Reconstruyendo contenedor Docker..."
docker compose down
docker compose build --no-cache
docker compose up -d

# 7. Verificar que el servidor está funcionando
echo ""
echo "🔍 Verificando servidor..."
sleep 5
if curl -s http://localhost:8001/api/ping > /dev/null; then
    echo "  ✅ Servidor funcionando correctamente"
else
    echo "  ⚠️  El servidor puede estar iniciando, verifica con: docker compose logs -f"
fi

echo ""
echo "===================================================================="
echo "✅ VERIFICACIÓN COMPLETADA"
echo "===================================================================="
echo ""
echo "AHORA PUEDES EJECUTAR UN NUEVO SCRAPING DE PRUEBA."
echo "EL CSV DEBERÍA TENER SOLO 7 COLUMNAS."
echo "===================================================================="
