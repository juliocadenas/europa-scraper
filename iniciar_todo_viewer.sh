#!/bin/bash
# Script completo para iniciar el visor de resultados y cloudflared
# Este script inicia ambos servicios automáticamente

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Iniciando Visor de Resultados${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Crear directorio para logs
mkdir -p /home/julio/cloudflared_logs

# Paso 1: Iniciar el visor de resultados
echo -e "${YELLOW}[1/2] Iniciando visor de resultados en puerto 8888...${NC}"
pkill -f results_viewer_completo.py 2>/dev/null
nohup ~/results_viewer_completo.py > ~/results_viewer.log 2>&1 &
VIEWER_PID=$!
echo -e "${GREEN}✓ Visor iniciado (PID: $VIEWER_PID)${NC}"

# Esperar a que el visor inicie
sleep 3

# Verificar que el visor está corriendo
if ! curl -s "http://localhost:8888/" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: El visor no se inició correctamente${NC}"
    echo "Revisa el log: ~/results_viewer.log"
    exit 1
fi

echo -e "${GREEN}✓ Visor funcionando correctamente${NC}"
echo ""

# Paso 2: Iniciar cloudflared
echo -e "${YELLOW}[2/2] Iniciando túnel de Cloudflare...${NC}"

# Verificar que cloudflared existe
if [ ! -f "./cloudflared.exe" ] && [ ! -f "./cloudflared" ]; then
    echo -e "${RED}ERROR: No se encontró cloudflared${NC}"
    echo "Por favor, descarga cloudflared desde: https://github.com/cloudflare/cloudflared/releases"
    exit 1
fi

# Determinar el ejecutable correcto según el sistema operativo
if [ -f "./cloudflared.exe" ]; then
    CLOUDFLARED="./cloudflared.exe"
else
    CLOUDFLARED="./cloudflared"
fi

# Generar nombre de archivo de log con timestamp
LOG_FILE="/home/julio/cloudflared_logs/cloudflared_$(date +%Y%m%d_%H%M%S).log"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  INSTRUCCIONES DE USO${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "1. Espera a que cloudflared genere la URL pública"
echo "2. Copia la URL que aparece (termina en .trycloudflare.com)"
echo "3. Abre esa URL en tu navegador"
echo ""
echo "Ejemplo: https://random-string.trycloudflare.com"
echo ""
echo -e "${YELLOW}Para detener todo, presiona Ctrl+C${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Logs del visor: ~/results_viewer.log"
echo "Logs de cloudflared: $LOG_FILE"
echo ""

# Iniciar cloudflared en modo quick tunnel
$CLOUDFLARED tunnel --url "http://localhost:8888" 2>&1 | tee "$LOG_FILE"

# Al detener cloudflared, también detener el visor
echo ""
echo -e "${YELLOW}Deteniendo visor de resultados...${NC}"
pkill -f results_viewer_completo.py
echo -e "${GREEN}✓ Todos los servicios detenido${NC}"
