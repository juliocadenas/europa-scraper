#!/bin/bash

echo "🌐 OBTENIENDO IP DE WSL PARA CONEXIÓN DESDE WINDOWS"
echo "===================================================="

# Obtener la IP de WSL
WSL_IP=$(ip route show | grep -i default | awk '{ print $3}')

echo "📡 IP de WSL: $WSL_IP"
echo ""
echo "🔧 CONFIGURACIÓN PARA EL CLIENTE WINDOWS:"
echo "===================================="
echo "Usa esta dirección en el cliente:"
echo "   $WSL_IP:8001"
echo ""
echo "O si tienes problemas, prueba:"
echo "   localhost:8001"
echo ""
echo "📝 Para configurar en el cliente:"
echo "1. Inicia el cliente en Windows"
echo "2. Busca el campo de dirección del servidor"
echo "3. Ingresa: $WSL_IP:8001"
echo "4. Intenta conectar"
echo ""
echo "🔍 VERIFICANDO CONEXIÓN:"
echo "curl -s http://localhost:8001/ping"
curl -s http://localhost:8001/ping
echo ""
echo "✅ IP obtenida: $WSL_IP"
echo "💡 Guarda esta IP para configurar el cliente Windows"