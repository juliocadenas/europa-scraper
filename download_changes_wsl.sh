#!/bin/bash

# Script para descargar los cambios del Europa Scraper a WSL
echo "=== Descargando cambios del Europa Scraper para WSL ==="

# Crear directorio si no existe
mkdir -p ~/europa_scraper

# Descargar los archivos modificados
echo "Descargando client/main.py..."
curl -o ~/europa_scraper/client/main.py https://raw.githubusercontent.com/tu-usuario/europa-scraper/main/fix/client/main.py

echo "Descargando server/server.py..."
curl -o ~/europa_scraper/server/server.py https://raw.githubusercontent.com/tu-usuario/europa-scraper/main/fix/server/server.py

# Nota: Reemplaza "tu-usuario" con tu nombre de usuario de GitHub real

echo "¡Cambios descargados exitosamente!"
echo ""
echo "Archivos descargados en:"
echo "  ~/europa_scraper/client/main.py"
echo "  ~/europa_scraper/server/server.py"
echo ""
echo "Para aplicar los cambios en WSL:"
echo "1. Copia los archivos a tu proyecto en WSL"
echo "2. Ejecuta: cd ~/europa_scraper && git status"
echo "3. Si los archivos están actualizados, listo!"