#!/bin/bash
# Script para iniciar Cloudflared Tunnel y exponer el servidor de resultados
# Este script crea un túnel seguro sin necesidad de abrir puertos en el firewall

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Cloudflared Tunnel - Resultados Viewer${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

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

# Puerto del servidor (debe coincidir con el puerto del servidor principal)
SERVER_PORT=${SERVER_PORT:-8001}
echo -e "${YELLOW}Puerto del servidor: $SERVER_PORT${NC}"

# Verificar que el servidor está corriendo
echo -e "${YELLOW}Verificando que el servidor está corriendo...${NC}"
sleep 2

if ! curl -s "http://localhost:$SERVER_PORT/ping" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: El servidor no está corriendo en el puerto $SERVER_PORT${NC}"
    echo "Por favor, inicia el servidor primero con: python server/main.py"
    exit 1
fi

echo -e "${GREEN}✓ Servidor detectado y funcionando${NC}"
echo ""

# Iniciar cloudflared
echo -e "${GREEN}Iniciando túnel de Cloudflare...${NC}"
echo -e "${YELLOW}Esto creará una URL pública segura para acceder a los resultados${NC}"
echo ""
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  INSTRUCCIONES DE USO${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo "1. Espera a que cloudflared genere la URL pública"
echo "2. Copia la URL que aparece (termina en .trycloudflare.com)"
echo "3. Abre esa URL en tu navegador"
echo "4. Agrega '/viewer' al final de la URL para ver el visor de resultados"
echo ""
echo "Ejemplo: https://random-string.trycloudflare.com/viewer"
echo ""
echo -e "${YELLOW}Para detener el túnel, presiona Ctrl+C${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo ""

# Iniciar cloudflared en modo quick tunnel (subdominio gratuito)
$CLOUDFLARED tunnel --url "http://localhost:$SERVER_PORT"
