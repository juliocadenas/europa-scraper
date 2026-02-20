#!/bin/bash
# Script para iniciar Cloudflared Tunnel para el visor de resultados (puerto 8888)
# Este script crea un túnel seguro sin necesidad de abrir puertos en el firewall
# El visor de resultados corre en el puerto 8888

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Cloudflared Tunnel - Resultados Viewer${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Crear directorio para logs
mkdir -p /home/julio/cloudflared_logs

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

# Puerto del visor de resultados
VIEWER_PORT=8888
echo -e "${YELLOW}Puerto del visor de resultados: $VIEWER_PORT${NC}"

# Verificar que el visor está corriendo
echo -e "${YELLOW}Verificando que el visor está corriendo...${NC}"
sleep 2

if ! curl -s "http://localhost:$VIEWER_PORT/" > /dev/null 2>&1; then
    echo -e "${RED}ADVERTENCIA: El visor no está corriendo en el puerto $VIEWER_PORT${NC}"
    echo "Por favor, inicia el visor primero con: ~/results_viewer_completo.py"
    echo "Continuando de todas formas..."
fi

echo -e "${GREEN}✓ Iniciando túnel de Cloudflare...${NC}"
echo ""

# Generar nombre de archivo de log con timestamp
LOG_FILE="/home/julio/cloudflared_logs/cloudflared_$(date +%Y%m%d_%H%M%S).log"

# Iniciar cloudflared en modo quick tunnel (subdominio gratuito)
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  INSTRUCCIONES DE USO${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo "1. Espera a que cloudflared genere la URL pública"
echo "2. Copia la URL que aparece (termina en .trycloudflare.com)"
echo "3. Abre esa URL en tu navegador"
echo ""
echo "Ejemplo: https://random-string.trycloudflare.com"
echo ""
echo -e "${YELLOW}Para detener el túnel, presiona Ctrl+C${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Logs guardados en: $LOG_FILE"
echo ""

# Iniciar cloudflared y guardar logs
$CLOUDFLARED tunnel --url "http://localhost:$VIEWER_PORT" 2>&1 | tee "$LOG_FILE"
