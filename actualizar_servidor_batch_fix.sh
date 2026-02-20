#!/bin/bash
# Script para actualizar el servidor remoto con la corrección del parámetro batch
# El error: "ScraperController.run_scraping() got an unexpected keyword argument 'batch'"
# Ocurre porque el scraper_controller.py remoto no tiene el parámetro batch

set -e

REMOTE_HOST="europa.docuscraper.cloud"
REMOTE_USER="root"
REMOTE_DIR="/opt/docuscraper"
CONTAINER_NAME="europa-scraper-prod"

echo "=================================================="
echo "ACTUALIZANDO SERVIDOR REMOTO - FIX PARÁMETRO BATCH"
echo "=================================================="

# 1. Verificar que scraper_controller.py tiene el parámetro batch
echo ""
echo "1. Verificando scraper_controller.py local..."
if grep -q "batch: Optional" controllers/scraper_controller.py; then
    echo "   ✅ El archivo local TIENE el parámetro batch"
else
    echo "   ❌ ERROR: El archivo local NO tiene el parámetro batch"
    echo "   Verificando firma del método run_scraping..."
    grep -n "async def run_scraping" controllers/scraper_controller.py
    exit 1
fi

# 2. Subir el archivo corregido al servidor
echo ""
echo "2. Subiendo scraper_controller.py al servidor remoto..."
scp controllers/scraper_controller.py ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/controllers/

# 3. Subir también server.py por si acaso
echo ""
echo "3. Subiendo server.py al servidor remoto..."
scp server/server.py ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/server/

# 4. Verificar que los archivos se subieron correctamente
echo ""
echo "4. Verificando archivos en el servidor remoto..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "grep -n 'batch: Optional' ${REMOTE_DIR}/controllers/scraper_controller.py | head -1"

# 5. Copiar archivos al contenedor Docker
echo ""
echo "5. Copiando archivos al contenedor Docker..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "docker cp ${REMOTE_DIR}/controllers/scraper_controller.py ${CONTAINER_NAME}:/app/controllers/"
ssh ${REMOTE_USER}@${REMOTE_HOST} "docker cp ${REMOTE_DIR}/server/server.py ${CONTAINER_NAME}:/app/server/"

# 6. Verificar que el archivo dentro del contenedor tiene el parámetro batch
echo ""
echo "6. Verificando archivo DENTRO del contenedor Docker..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "docker exec ${CONTAINER_NAME} grep -n 'batch: Optional' /app/controllers/scraper_controller.py | head -1"

# 7. Reiniciar el contenedor
echo ""
echo "7. Reiniciando el contenedor Docker..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "docker restart ${CONTAINER_NAME}"

# 8. Esperar a que el contenedor esté listo
echo ""
echo "8. Esperando a que el contenedor esté listo (15 segundos)..."
sleep 15

# 9. Verificar que el contenedor está corriendo
echo ""
echo "9. Verificando estado del contenedor..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "docker ps | grep ${CONTAINER_NAME}"

# 10. Verificar logs del contenedor
echo ""
echo "10. Últimas 10 líneas del log del contenedor:"
ssh ${REMOTE_USER}@${REMOTE_HOST} "docker logs --tail 10 ${CONTAINER_NAME}"

echo ""
echo "=================================================="
echo "✅ ACTUALIZACIÓN COMPLETADA"
echo "=================================================="
echo ""
echo "El servidor remoto ha sido actualizado con:"
echo "  - scraper_controller.py (con parámetro batch)"
echo "  - server.py (que pasa el parámetro batch)"
echo ""
echo "Prueba iniciar el scraping nuevamente desde el cliente."
