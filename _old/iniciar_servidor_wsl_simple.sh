#!/bin/bash

echo "🚀 Iniciando servidor..."

# Matar procesos anteriores
pkill -f "python.*iniciar_servidor" 2>/dev/null

# Esperar un momento
sleep 1

# Iniciar servidor
cd "$(dirname "$0")"
python3 iniciar_servidor_corregido.py
