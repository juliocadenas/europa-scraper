#!/bin/bash
# =============================================================
# SETUP: Ollama en NAB9 (IA SERVER con RTX 5080)
# =============================================================
# Ejecutar en NAB9: ssh pepe@192.168.1.42
# =============================================================

echo "========================================="
echo "  SETUP Ollama en NAB9 (IA SERVER GPU)"
echo "========================================="

# 1. Verificar que Ollama está instalado
echo ""
echo "🔍 Verificando Ollama..."
if command -v ollama &> /dev/null; then
    echo "✅ Ollama instalado: $(ollama --version 2>/dev/null || echo 'versión desconocida')"
else
    echo "❌ Ollama no está instalado."
    echo "   Instalar con: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

# 2. Verificar/crear servicio systemd
echo ""
echo "🔧 Configurando Ollama para escuchar en toda la red LAN (0.0.0.0)..."

# Crear override de systemd si no existe
OVERRIDES_DIR="/etc/systemd/system/ollama.service.d"
OVERRIDE_FILE="$OVERRIDES_DIR/override.conf"

if [ ! -d "$OVERRIDES_DIR" ]; then
    sudo mkdir -p "$OVERRIDES_DIR"
fi

if grep -q "OLLAMA_HOST=0.0.0.0" "$OVERRIDE_FILE" 2>/dev/null; then
    echo "✅ Ollama ya configurado para 0.0.0.0"
else
    echo "[Service]" | sudo tee "$OVERRIDE_FILE" > /dev/null
    echo "Environment=\"OLLAMA_HOST=0.0.0.0\"" | sudo tee -a "$OVERRIDE_FILE" > /dev/null
    echo "✅ Override creado: $OVERRIDE_FILE"
fi

# 3. Reiniciar Ollama
echo ""
echo "🔄 Reiniciando Ollama..."
sudo systemctl daemon-reload
sudo systemctl restart ollama
sleep 2

# 4. Verificar que está corriendo
if sudo systemctl is-active --quiet ollama; then
    echo "✅ Ollama service activo"
else
    echo "❌ Ollama no arrancó. Ver logs: journalctl -u ollama -n 20"
    exit 1
fi

# 5. Verificar que escucha en 0.0.0.0:11434
echo ""
echo "🌐 Verificando que escucha en 0.0.0.0:11434..."
if ss -tlnp | grep -q "0.0.0.0:11434"; then
    echo "✅ Ollama escuchando en 0.0.0.0:11434 (accesible desde LAN)"
elif ss -tlnp | grep -q "11434"; then
    echo "⚠️  Ollama escuchando pero no en 0.0.0.0. Verificar override."
    ss -tlnp | grep "11434"
else
    echo "❌ No se detecta Ollama en puerto 11434"
    exit 1
fi

# 6. Descargar modelo llama3.1 si no existe
echo ""
echo "🤖 Verificando modelo llama3.1..."
if ollama list | grep -q "llama3.1"; then
    echo "✅ Modelo llama3.1 ya disponible"
else
    echo "📥 Descargando modelo llama3.1 (puede tardar varios minutos)..."
    ollama pull llama3.1
    echo "✅ Modelo descargado"
fi

# 7. Listar modelos disponibles
echo ""
echo "📋 Modelos disponibles:"
ollama list

# 8. Probar conectividad desde localhost
echo ""
echo "🧪 Probando API..."
RESP=$(curl -s http://localhost:11434/api/tags)
if echo "$RESP" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
    echo "✅ API respondiendo correctamente"
else
    echo "⚠️  API no respondió como esperado: $RESP"
fi

echo ""
echo "========================================="
echo "  ✅ OLLAMA SETUP COMPLETADO"
echo "========================================="
echo ""
echo "Ollama accesible desde:"
echo "  - Local:    http://localhost:11434"
echo "  - LAN:      http://192.168.1.42:11434"
echo ""
echo "Ahora ejecutar deploy_google_ai.sh en SERVIDOR01"
echo ""