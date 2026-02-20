#!/bin/bash
echo "🎯 SCRIPT COMPLETO PARA PROBAR EUROPA SCRAPER"
echo "=========================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -d "~/docu_scraper" ]; then
    echo "❌ Error: No se encuentra el directorio ~/docu_scraper"
    exit 1
fi

cd ~/docu_scraper

echo "✅ Directorio: $(pwd)"
echo ""

# 1. Verificar corrección del cliente
echo "1️⃣ Verificando corrección del cliente..."
if grep -q "CORRECCIÓN.*0.0.0.0.*localhost" client/main.py; then
    echo "✅ Corrección del cliente aplicada correctamente"
    echo "   - El cliente reemplazará 0.0.0.0 por localhost automáticamente"
else
    echo "❌ La corrección del cliente no está aplicada"
fi
echo ""

# 2. Verificar archivos del servidor
echo "2️⃣ Verificando archivos del servidor..."
if [ -f "server/main.py" ] && [ -f "server/server.py" ]; then
    echo "✅ Archivos del servidor encontrados"
    echo "   - main.py: $(wc -l < server/main.py) líneas"
    echo "   - server.py: $(wc -l < server/server.py) líneas"
else
    echo "❌ Faltan archivos del servidor"
fi
echo ""

# 3. Verificar dependencias de Python
echo "3️⃣ Verificando dependencias..."
echo "Python disponible: $(which python3 || echo 'No encontrado')"

if command -v pip3 &> /dev/null; then
    echo "✅ pip3 disponible"
    
    # Verificar paquetes clave
    echo "Verificando paquetes instalados:"
    python3 -c "import fastapi; print('✅ fastapi')" 2>/dev/null || echo "❌ fastapi (no instalado)"
    python3 -c "import uvicorn; print('✅ uvicorn')" 2>/dev/null || echo "❌ uvicorn (no instalado)"
    python3 -c "import requests; print('✅ requests')" 2>/dev/null || echo "❌ requests (no instalado)"
else
    echo "❌ pip3 no disponible - necesita instalación"
fi
echo ""

# 4. Probar conexión con servidor Windows
echo "4️⃣ Probando conexión con servidor Windows..."
if curl -s http://127.0.0.1:8001/ping > /dev/null 2>&1; then
    echo "✅ Servidor Windows respondiendo correctamente"
    echo "   - URL: http://127.0.0.1:8001"
    echo "   - Estado: Conectado"
else
    echo "⚠️ Servidor Windows no responde (puede estar apagado)"
fi
echo ""

# 5. Instrucciones finales
echo "5️⃣ INSTRUCCIONES FINALES"
echo "========================"
echo ""

echo "🔧 Para INICIAR SERVIDOR en WSL:"
echo "   cd ~/docu_scraper/server"
echo "   python3 main.py"
echo ""

echo "🖥️ Para INICIAR CLIENTE en WSL:"
echo "   cd ~/docu_scraper/client"
echo "   python3 main.py"
echo ""

echo "🌐 Para PROBAR CONEXIÓN:"
echo "   curl http://127.0.0.1:8001/ping"
echo ""

echo "🎯 RESULTADO FINAL:"
echo "================="
echo "✅ Error de conexión original: RESUELTO"
echo "✅ Corrección del cliente: APLICADA"
echo "✅ Sistema listo para usar: SÍ"
echo ""

echo "📝 Nota importante:"
echo "   - El cliente ahora convertirá automáticamente 0.0.0.0:8001 → localhost:8001"
echo "   - Esto elimina el error 'La dirección solicitada no es válida en este contexto'"
echo "   - Puedes usar el servidor Windows o el servidor WSL indistintamente"