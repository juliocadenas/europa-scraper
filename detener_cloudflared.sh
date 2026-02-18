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
