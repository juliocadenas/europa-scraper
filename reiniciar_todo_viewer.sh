#!/bin/bash
# Script completo para reiniciar el visor de resultados y cloudflared
# Este script hace todo automáticamente: verifica, reinicia y muestra la URL

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Reiniciando Visor de Resultados${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Crear directorio para logs
mkdir -p /home/julio/cloudflared_logs

# Paso 1: Detener procesos anteriores
echo -e "${YELLOW}[1/5] Deteniendo procesos anteriores...${NC}"
pkill -f results_viewer_completo.py 2>/dev/null
pkill -f cloudflared 2>/dev/null
sleep 2
echo -e "${GREEN}✓ Procesos detenidos${NC}"
echo ""

# Paso 2: Verificar que el script del visor existe
echo -e "${YELLOW}[2/5] Verificando script del visor...${NC}"
if [ ! -f ~/results_viewer_completo.py ]; then
    echo -e "${RED}ERROR: No se encuentra ~/results_viewer_completo.py${NC}"
    echo "Por favor, copia el script desde results_viewer_script_para_copiar.txt"
    exit 1
fi
echo -e "${GREEN}✓ Script encontrado${NC}"
echo ""

# Paso 3: Iniciar el visor de resultados
echo -e "${YELLOW}[3/5] Iniciando visor de resultados en puerto 8888...${NC}"
nohup ~/results_viewer_completo.py > ~/results_viewer.log 2>&1 &
VIEWER_PID=$!
echo -e "${GREEN}✓ Visor iniciado (PID: $VIEWER_PID)${NC}"

# Esperar a que el visor inicie
sleep 3

# Verificar que el visor está corriendo
if ! ps -p $VIEWER_PID > /dev/null 2>&1; then
    echo -e "${RED}ERROR: El visor no se inició correctamente${NC}"
    echo "Revisa el log: ~/results_viewer.log"
    echo ""
    tail -20 ~/results_viewer.log
    exit 1
fi

# Verificar que el puerto 8888 está escuchando
if ! netstat -tlnp 2>/dev/null | grep -q ":8888 "; then
    echo -e "${RED}ERROR: El puerto 8888 no está escuchando${NC}"
    echo "Revisa el log: ~/results_viewer.log"
    exit 1
fi

echo -e "${GREEN}✓ Visor funcionando correctamente${NC}"
echo ""

# Paso 4: Buscar cloudflared
echo -e "${YELLOW}[4/5] Buscando cloudflared...${NC}"
CLOUDFLARED_PATH=""

# Buscar en ubicaciones comunes
for path in \
    ~/cloudflared \
    ~/europa/cloudflared \
    /usr/local/bin/cloudflared \
    /usr/bin/cloudflared \
    ./cloudflared; do
    if [ -f "$path" ]; then
        CLOUDFLARED_PATH="$path"
        echo -e "${GREEN}✓ Cloudflared encontrado en: $CLOUDFLARED_PATH${NC}"
        break
    fi
done

if [ -z "$CLOUDFLARED_PATH" ]; then
    echo -e "${RED}ERROR: No se encontró cloudflared${NC}"
    echo "Buscando en todo el sistema..."
    find ~ -name cloudflared -type f 2>/dev/null
    echo ""
    echo "Por favor, descarga cloudflared desde:"
    echo "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    exit 1
fi

# Paso 5: Iniciar cloudflared
echo -e "${YELLOW}[5/5] Iniciando túnel de Cloudflare...${NC}"
echo ""

LOG_FILE="/home/julio/cloudflared_logs/cloudflared_$(date +%Y%m%d_%H%M%S).log"

# Iniciar cloudflared en segundo plano
nohup "$CLOUDFLARED_PATH" tunnel --url http://localhost:8888 > "$LOG_FILE" 2>&1 &
CLOUDFLARED_PID=$!

echo -e "${GREEN}✓ Cloudflared iniciado (PID: $CLOUDFLARED_PID)${NC}"
echo ""

# Esperar a que cloudflared genere la URL
echo -e "${YELLOW}Esperando a que cloudflared genere la URL...${NC}"
for i in {1..30}; do
    if grep -q "trycloudflare.com" "$LOG_FILE" 2>/dev/null; then
        echo -e "${GREEN}✓ URL generada!${NC}"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Extraer y mostrar la URL
URL=$(grep -oP 'https://[a-zA-Z0-9\-]+\.trycloudflare\.com' "$LOG_FILE" | head -1)

if [ -n "$URL" ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ¡URL DE ACCESO!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${CYAN}$URL${NC}"
    echo ""
    echo -e "${YELLOW}Abre esta URL en tu navegador${NC}"
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Logs del visor: ~/results_viewer.log"
    echo "Logs de cloudflared: $LOG_FILE"
    echo ""
    echo -e "${YELLOW}Para detener todo, ejecuta:${NC}"
    echo "  pkill -f results_viewer_completo.py"
    echo "  pkill -f cloudflared"
    echo ""
else
    echo -e "${RED}No se pudo generar la URL. Revisa el log:${NC}"
    echo "$LOG_FILE"
    echo ""
    tail -30 "$LOG_FILE"
fi
