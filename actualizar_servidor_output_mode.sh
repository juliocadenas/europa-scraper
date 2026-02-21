#!/bin/bash
# ============================================================================
# ACTUALIZACIÓN DEL SERVIDOR - MODO DE SALIDA DE RESULTADOS
# ============================================================================
# Este script actualiza los archivos necesarios para soportar la configuración
# de modo de salida de resultados (Por curso vs Conglomerado)
# 
# Archivos modificados:
# - controllers/scraper_controller.py: Lee output_mode de params
# - server/server.py: Pasa results_output_mode a job_params_dict
# - utils/scraper/result_manager.py: Ya tiene soporte implementado
# ============================================================================

echo "=================================================="
echo "ACTUALIZANDO SERVIDOR - MODO SALIDA DE RESULTADOS"
echo "=================================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directorio del proyecto en el servidor
PROJECT_DIR="/root/europa-scraper"

# Verificar que estamos en el directorio correcto
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}Error: No se encuentra el directorio del proyecto en $PROJECT_DIR${NC}"
    exit 1
fi

cd "$PROJECT_DIR" || exit 1

echo -e "${YELLOW}Deteniendo contenedor Docker...${NC}"
docker stop europa-scraper 2>/dev/null || true

echo -e "${YELLOW}Actualizando código desde GitHub...${NC}"
git fetch origin
git reset --hard origin/main
git pull origin main

echo -e "${YELLOW}Verificando archivos actualizados...${NC}"

# Verificar que los archivos se actualizaron
echo "Verificando controllers/scraper_controller.py..."
if grep -q "output_mode = params.get('results_output_mode'" controllers/scraper_controller.py; then
    echo -e "${GREEN}✓ scraper_controller.py actualizado correctamente${NC}"
else
    echo -e "${RED}✗ scraper_controller.py necesita actualización manual${NC}"
fi

echo "Verificando server/server.py..."
if grep -q "'results_output_mode': results_output_mode" server/server.py; then
    echo -e "${GREEN}✓ server.py actualizado correctamente${NC}"
else
    echo -e "${RED}✗ server.py necesita actualización manual${NC}"
fi

echo "Verificando utils/scraper/result_manager.py..."
if grep -q "def __init__(self, output_mode: str = \"Por curso\"):" utils/scraper/result_manager.py; then
    echo -e "${GREEN}✓ result_manager.py tiene soporte para output_mode${NC}"
else
    echo -e "${RED}✗ result_manager.py necesita actualización manual${NC}"
fi

echo -e "${YELLOW}Reconstruyendo contenedor Docker...${NC}"
docker build -t europa-scraper .

echo -e "${YELLOW}Iniciando contenedor Docker...${NC}"
docker run -d \
    --name europa-scraper \
    --restart unless-stopped \
    -p 8001:8001 \
    -v $(pwd)/results:/app/results \
    -v $(pwd)/logs:/app/logs \
    -v $(pwd)/courses.db:/app/courses.db \
    europa-scraper

echo -e "${GREEN}=================================================="
echo "ACTUALIZACIÓN COMPLETADA"
echo "==================================================${NC}"
echo ""
echo "El servidor ahora soporta dos modos de salida de resultados:"
echo "  1. 'Por curso' (por defecto): Un archivo CSV por cada curso procesado"
echo "  2. 'Conglomerado': Un solo archivo CSV con todos los resultados"
echo ""
echo "La configuración se realiza desde el cliente en la pestaña de Configuración."
