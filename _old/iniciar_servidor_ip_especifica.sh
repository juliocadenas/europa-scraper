#!/bin/bash

echo "🚀 INICIANDO SERVIDOR CON IP ESPECÍFICA"
echo "=========================================="

# Obtener IP de WSL
WSL_IP=$(ip route show | grep -i default | awk '{ print $3}')

echo "🌐 IP de WSL detectada: $WSL_IP"

# Ir al directorio del servidor
cd "$(dirname "$0")/server"

echo "📁 Directorio de trabajo: $(pwd)"

# Iniciar servidor en la IP específica en lugar de 0.0.0.0
echo "✅ Iniciando servidor en: http://$WSL_IP:8001"
echo "🌐 Servidor disponible en: http://$WSL_IP:8001"
echo "🏓 Endpoint de ping: http://$WSL_IP:8001/ping"
echo "📊 Endpoint de scraping: http://$WSL_IP:8001/start_scraping"
echo "=================================================="
echo "📝 Presione Ctrl+C para detener el servidor"
echo ""

# Iniciar el servidor con la IP específica
python3 main_wsl_corregido.py --host $WSL_IP --port 8001