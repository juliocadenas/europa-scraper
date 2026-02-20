#!/bin/bash
# Script de diagnóstico completo para el visor de resultados

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Diagnóstico del Visor de Resultados${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 1. Verificar procesos corriendo
echo -e "${YELLOW}[1] Procesos corriendo:${NC}"
echo "   Visor de resultados:"
ps aux | grep results_viewer_completo | grep -v grep || echo "   ${RED}No está corriendo${NC}"
echo ""
echo "   Cloudflared:"
ps aux | grep cloudflared | grep -v grep || echo "   ${RED}No está corriendo${NC}"
echo ""

# 2. Verificar puertos
echo -e "${YELLOW}[2] Puertos en uso:${NC}"
netstat -tlnp 2>/dev/null | grep -E ":(8888|8001)" || echo "   ${RED}No se encontraron puertos 8888 o 8001${NC}"
echo ""

# 3. Verificar archivos del visor
echo -e "${YELLOW}[3] Archivos del visor:${NC}"
if [ -f ~/results_viewer_completo.py ]; then
    echo "   ${GREEN}✓ ~/results_viewer_completo.py existe${NC}"
    ls -lh ~/results_viewer_completo.py
else
    echo "   ${RED}✗ ~/results_viewer_completo.py NO existe${NC}"
fi
echo ""

# 4. Verificar logs del visor
echo -e "${YELLOW}[4] Log del visor:${NC}"
if [ -f ~/results_viewer.log ]; then
    echo "   ${GREEN}✓ ~/results_viewer.log existe${NC}"
    echo "   --- Últimas 20 líneas ---"
    tail -20 ~/results_viewer.log
else
    echo "   ${RED}✗ ~/results_viewer.log NO existe${NC}"
fi
echo ""

# 5. Buscar archivos CSV
echo -e "${YELLOW}[5] Archivos CSV encontrados:${NC}"
CSV_FILES=$(find ~ -name "*.csv" -type f 2>/dev/null | head -20)
if [ -n "$CSV_FILES" ]; then
    echo "$CSV_FILES" | while read file; do
        echo "   - $file"
    done
else
    echo "   ${RED}No se encontraron archivos CSV${NC}"
fi
echo ""

# 6. Buscar directorios results y omitidos
echo -e "${YELLOW}[6] Directorios results y omitidos:${NC}"
RESULTS_DIRS=$(find ~ -type d -name "results" 2>/dev/null)
OMITIDOS_DIRS=$(find ~ -type d -name "omitidos" 2>/dev/null)

if [ -n "$RESULTS_DIRS" ]; then
    echo "   Directorios 'results' encontrados:"
    echo "$RESULTS_DIRS" | while read dir; do
        echo "   - $dir"
        ls -la "$dir" | head -10
    done
else
    echo "   ${RED}No se encontró directorio 'results'${NC}"
fi
echo ""

if [ -n "$OMITIDOS_DIRS" ]; then
    echo "   Directorios 'omitidos' encontrados:"
    echo "$OMITIDOS_DIRS" | while read dir; do
        echo "   - $dir"
        ls -la "$dir" | head -10
    done
else
    echo "   ${RED}No se encontró directorio 'omitidos'${NC}"
fi
echo ""

# 7. Buscar cloudflared
echo -e "${YELLOW}[7] Ubicación de cloudflared:${NC}"
CLOUDFLARED_PATHS=$(find ~ -name "cloudflared" -type f 2>/dev/null)
if [ -n "$CLOUDFLARED_PATHS" ]; then
    echo "   Cloudflared encontrado en:"
    echo "$CLOUDFLARED_PATHS" | while read path; do
        echo "   - $path"
        ls -lh "$path"
    done
else
    echo "   ${RED}No se encontró cloudflared${NC}"
fi
echo ""

# 8. Logs de cloudflared
echo -e "${YELLOW}[8] Logs de cloudflared:${NC}"
if [ -d /home/julio/cloudflared_logs ]; then
    echo "   ${GREEN}✓ Directorio de logs existe${NC}"
    ls -lht /home/julio/cloudflared_logs/ | head -10
    if [ "$(ls -A /home/julio/cloudflared_logs/)" ]; then
        echo "   --- Último log (últimas 10 líneas) ---"
        tail -10 /home/julio/cloudflared_logs/$(ls -t /home/julio/cloudflared_logs/ | head -1)
    fi
else
    echo "   ${RED}✗ Directorio de logs NO existe${NC}"
fi
echo ""

# 9. Verificar permisos
echo -e "${YELLOW}[9] Permisos del usuario:${NC}"
id
echo ""

# 10. Verificar espacio en disco
echo -e "${YELLOW}[10] Espacio en disco:${NC}"
df -h ~
echo ""

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Fin del diagnóstico${NC}"
echo -e "${CYAN}========================================${NC}"
