#!/bin/bash

# Script para iniciar el servidor Europa Scraper en Linux/WSL
echo "Iniciando servidor Europa Scraper en Linux/WSL..."

# Ir al directorio del proyecto
cd "$(dirname "$0")"
echo "Directorio actual: $(pwd)"

# Ir al directorio del servidor
cd server
echo "Cambiado al directorio del servidor: $(pwd)"

# Verificar si Python está disponible
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 no está instalado"
    exit 1
fi

# Verificar si el archivo main.py existe
if [ ! -f "main.py" ]; then
    echo "ERROR: No se encuentra el archivo main.py en $(pwd)"
    exit 1
fi

# Iniciar el servidor
echo "Iniciando servidor con Python3..."
python3 main.py

echo "Servidor detenido."