#!/bin/bash

# ==============================================================================
# Script para verificar el código DENTRO del contenedor Docker
# ==============================================================================

echo "🔍 VERIFICANDO CÓDIGO DENTRO DEL CONTENEDOR DOCKER..."

# 1. Verificar que el contenedor está corriendo
echo ""
echo "📋 Contenedores activos:"
docker ps

# 2. Verificar el código de result_manager.py DENTRO del contenedor
echo ""
echo "📝 Verificando result_manager.py DENTRO del contenedor..."
docker exec europa-scraper-prod grep -n "filtered_result = {}" /app/utils/scraper/result_manager.py

if [ $? -eq 0 ]; then
    echo "  ✅ Código de filtrado presente en el contenedor"
else
    echo "  ❌ CÓDIGO DE FILTRADO NO ENCONTRADO EN EL CONTENEDOR"
    echo ""
    echo "  Mostrando las líneas 180-195 del archivo en el contenedor:"
    docker exec europa-scraper-prod sed -n '180,195p' /app/utils/scraper/result_manager.py
fi

# 3. Verificar CSV_COLUMNS en el contenedor
echo ""
echo "📝 Verificando CSV_COLUMNS en el contenedor..."
docker exec europa-scraper-prod grep -n "CSV_COLUMNS = \[" /app/utils/scraper/result_manager.py

# 4. Verificar _process_single_result en el contenedor
echo ""
echo "📝 Verificando _process_single_result en el contenedor..."
docker exec europa-scraper-prod grep -n "'lang': result.get('lang'" /app/controllers/scraper_controller.py

if [ $? -eq 0 ]; then
    echo "  ✅ Código de lang presente en _process_single_result"
else
    echo "  ❌ CÓDIGO DE LANG NO ENCONTRADO"
fi

# 5. Mostrar el contenido completo de append_to_csv en el contenedor
echo ""
echo "📝 Mostrando método append_to_csv del contenedor:"
docker exec europa-scraper-prod sed -n '155,195p' /app/utils/scraper/result_manager.py

echo ""
echo "===================================================================="
echo "SI EL CÓDIGO NO ESTÁ PRESENTE, EJECUTA:"
echo "  cd /opt/docuscraper"
echo "  sudo chown -R \$USER:\$USER /opt/docuscraper/.git"
echo "  git fetch origin"
echo "  git reset --hard origin/patch-monitor"
echo "  docker compose down"
echo "  docker compose build --no-cache"
echo "  docker compose up -d"
echo "===================================================================="
