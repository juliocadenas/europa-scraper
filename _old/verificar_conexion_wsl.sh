#!/bin/bash

echo "🔍 VERIFICANDO CONEXIÓN WSL-WINDOWS"
echo "==================================="

echo "📊 Estado del servidor:"
echo "1. Verificando si el servidor está corriendo en WSL..."
if curl -s http://localhost:8001/ > /dev/null; then
    echo "✅ Servidor respondiendo en WSL (localhost:8001)"
else
    echo "❌ Servidor no responde en WSL"
    exit 1
fi

echo "2. Verificando dirección IP de WSL..."
WSL_IP=$(ip route show | grep -i default | awk '{ print $3}')
echo "🌐 IP de WSL: $WSL_IP"

echo "3. Verificando conexión desde Windows..."
echo "🔧 Para conectar desde Windows, usa:"
echo "   http://$WSL_IP:8001"
echo "   o"
echo "   http://localhost:8001 (si el reenvío de puertos está configurado)"

echo "4. Verificando endpoints..."
echo "📡 Testing /ping endpoint:"
curl -s http://localhost:8001/ping
echo ""

echo "📡 Testing /health endpoint:"
curl -s http://localhost:8001/
echo ""

echo "✅ Verificación completada"
echo "💡 Si Windows no puede conectar, prueba:"
echo "   1. Configurar el firewall de Windows"
echo "   2. Usar la IP: $WSL_IP:8001 en el cliente"
echo "   3. Verificar que el servidor esté corriendo en 0.0.0.0:8001"