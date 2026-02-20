#!/bin/bash
# Script para detener el visor de resultados y cloudflared

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Deteniendo servicios del visor de resultados...${NC}"
echo ""

# Detener cloudflared
echo -e "${YELLOW}Deteniendo cloudflared...${NC}"
pkill -f cloudflared
echo -e "${GREEN}✓ Cloudflared detenido${NC}"

# Detener visor de resultados
echo -e "${YELLOW}Deteniendo visor de resultados...${NC}"
pkill -f results_viewer_completo.py
echo -e "${GREEN}✓ Visor de resultados detenido${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Todos los servicios detenido${NC}"
echo -e "${GREEN}========================================${NC}"
