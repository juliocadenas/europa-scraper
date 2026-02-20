#!/bin/bash
# Script para crear los scripts de cloudflared directamente en el servidor01
# Ejecuta este script en el servidor01 para crear los archivos necesarios

echo "Creando scripts de cloudflared en el servidor01..."

# Crear script iniciar_cloudflared_docker.sh
cat > ~/iniciar_cloudflared_docker.sh << 'EOF'
#!/bin/bash
# Script para iniciar Cloudflared Tunnel en Docker (servidor01)
# Ejecuta cloudflared en segundo plano con logging

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Cloudflared Tunnel - Docker Mode${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verificar que cloudflared existe
if ! command -v cloudflared &> /dev/null; then
    echo -e "${RED}ERROR: cloudflared no está instalado${NC}"
    echo "Instálalo con:"
    echo "  wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    echo "  sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared"
    echo "  sudo chmod +x /usr/local/bin/cloudflared"
    exit 1
fi

# Verificar que el servidor está corriendo
echo -e "${YELLOW}Verificando que el servidor está corriendo...${NC}"
if ! curl -s "http://localhost:8001/ping" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: El servidor no está corriendo en el puerto 8001${NC}"
    echo "Verifica que el contenedor Docker está activo:"
    echo "  docker ps"
    exit 1
fi
echo -e "${GREEN}✓ Servidor detectado y funcionando${NC}"
echo ""

# Crear directorio para logs
mkdir -p ~/cloudflared_logs

# Nombre del archivo de log con timestamp
LOG_FILE="$HOME/cloudflared_logs/cloudflared_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="$HOME/cloudflared_logs/cloudflared.pid"

# Verificar si ya hay una instancia corriendo
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}Cloudflared ya está corriendo (PID: $OLD_PID)${NC}"
        echo "Para detenerlo, usa: ~/detener_cloudflared.sh"
        echo ""
        echo "Para ver el log actual:"
        echo "  tail -f $LOG_FILE"
        exit 0
    else
        echo -e "${YELLOW}Archivo PID antiguo encontrado, limpiando...${NC}"
        rm "$PID_FILE"
    fi
fi

# Iniciar cloudflared en segundo plano
echo -e "${GREEN}Iniciando cloudflared en segundo plano...${NC}"
echo -e "${YELLOW}Logs se guardarán en: $LOG_FILE${NC}"
echo ""

# Iniciar cloudflared y redirigir output al log
nohup cloudflared tunnel --url "http://localhost:8001" > "$LOG_FILE" 2>&1 &
CLOUDFLARED_PID=$!

# Guardar el PID
echo "$CLOUDFLARED_PID" > "$PID_FILE"

# Esperar unos segundos para que cloudflared se inicie
sleep 5

# Verificar que se inició correctamente
if ps -p "$CLOUDFLARED_PID" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Cloudflared iniciado correctamente (PID: $CLOUDFLARED_PID)${NC}"
    echo ""
    
    # Extraer la URL del log
    sleep 3
    URL=$(grep -oP 'https://[a-zA-Z0-9\-]+\.trycloudflare\.com' "$LOG_FILE" | head -1)
    
    if [ -n "$URL" ]; then
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  URL GENERADA${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo -e "${YELLOW}URL del túnel:${NC}"
        echo "  $URL"
        echo ""
        echo -e "${YELLOW}URL del visor de resultados:${NC}"
        echo "  ${URL}/viewer"
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo "Comandos útiles:"
        echo "  Ver logs:  tail -f $LOG_FILE"
        echo "  Detener:   ~/detener_cloudflared.sh"
        echo "  Ver PID:   cat $PID_FILE"
        echo ""
    else
        echo -e "${YELLOW}URL aún generándose... verifica el log:${NC}"
        echo "  tail -f $LOG_FILE"
    fi
else
    echo -e "${RED}ERROR: No se pudo iniciar cloudflared${NC}"
    echo "Revisa el log para más detalles:"
    echo "  cat $LOG_FILE"
    rm "$PID_FILE"
    exit 1
fi
EOF

# Crear script detener_cloudflared.sh
cat > ~/detener_cloudflared.sh << 'EOF'
#!/bin/bash
# Script para detener Cloudflared Tunnel

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PID_FILE="$HOME/cloudflared_logs/cloudflared.pid"

echo -e "${YELLOW}Deteniendo Cloudflared Tunnel...${NC}"

if [ ! -f "$PID_FILE" ]; then
    echo -e "${RED}No se encontró archivo PID. Buscando procesos de cloudflared...${NC}"
    
    # Buscar procesos de cloudflared
    PIDS=$(pgrep -f "cloudflared tunnel")
    
    if [ -z "$PIDS" ]; then
        echo -e "${RED}No se encontraron procesos de cloudflared corriendo${NC}"
        exit 0
    fi
    
    echo -e "${YELLOW}Encontrados procesos: $PIDS${NC}"
    echo "$PIDS" | xargs kill
    echo -e "${GREEN}✓ Procesos detenidos${NC}"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}Deteniendo proceso $PID...${NC}"
    kill "$PID"
    
    # Esperar a que el proceso termine
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Cloudflared detenido correctamente${NC}"
            rm "$PID_FILE"
            exit 0
        fi
        sleep 1
    done
    
    # Si no terminó, forzar
    echo -e "${YELLOW}Forzando terminación...${NC}"
    kill -9 "$PID"
    rm "$PID_FILE"
    echo -e "${GREEN}✓ Cloudflared forzado a detenerse${NC}"
else
    echo -e "${RED}El proceso $PID no está corriendo${NC}"
    rm "$PID_FILE"
fi
EOF

# Dar permisos de ejecución
chmod +x ~/iniciar_cloudflared_docker.sh
chmod +x ~/detener_cloudflared.sh

echo ""
echo "✓ Scripts creados exitosamente en ~/"
echo ""
echo "Para iniciar cloudflared:"
echo "  ~/iniciar_cloudflared_docker.sh"
echo ""
echo "Para detener cloudflared:"
echo "  ~/detener_cloudflared.sh"
