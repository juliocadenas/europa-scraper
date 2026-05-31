#!/bin/bash
# =============================================================
# DEPLOY: Google AI Scraper (ScrapeGraphAI + Ollama + site:usa.gov)
# =============================================================
# Ejecutar desde SERVIDOR01 (Xeon): ssh julio@100.83.253.87
# =============================================================

set -e

echo "========================================="
echo "  DEPLOY Google AI Scraper en SERVIDOR01"
echo "========================================="

# 1. Ir al repo
cd ~/europa-scraper 2>/dev/null || cd ~/V3.1-LINUX 2>/dev/null || {
    echo "❌ No encuentro el repo del scraper. ¿En qué path está?"
    echo "   Buscando..."
    find /home -name "server.py" -path "*/server/*" 2>/dev/null | head -5
    find /opt -name "server.py" -path "*/server/*" 2>/dev/null | head -5
    exit 1
}

REPO_DIR=$(pwd)
echo "📁 Repo encontrado en: $REPO_DIR"

# 2. Pull del código actualizado
echo ""
echo "📥 Haciendo git pull..."
git pull origin main

# 3. Instalar dependencias nuevas
echo ""
echo "📦 Instalando dependencias (scrapegraphai, langchain)..."
pip install scrapegraphai langchain langchain-community beautifulsoup4 lxml 2>&1 | tail -5

# 4. Verificar conectividad con Ollama en NAB9 (IA SERVER)
echo ""
echo "🔍 Verificando conexión con Ollama en NAB9 (192.168.1.42:11434)..."
if curl -s --max-time 5 http://192.168.1.42:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama accesible en NAB9"
    echo "   Modelos disponibles:"
    curl -s http://192.168.1.42:11434/api/tags | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for m in data.get('models', []):
        print(f'   - {m[\"name\"]}')
except: print('   (no se pudieron listar)')
" 2>/dev/null || echo "   (no se pudieron listar)"
else
    echo "⚠️  No se puede conectar a Ollama en 192.168.1.42:11434"
    echo "   Verificar en NAB9 que Ollama escuche en 0.0.0.0:"
    echo "   → ssh pepe@192.168.1.42"
    echo "   → sudo systemctl edit ollama"
    echo "   → Agregar: Environment=\"OLLAMA_HOST=0.0.0.0\""
    echo "   → sudo systemctl restart ollama"
fi

# 5. Reiniciar el servidor
echo ""
echo "🔄 Reiniciando servidor Europa Scraper..."
if systemctl is-active --quiet europa-scraper 2>/dev/null; then
    sudo systemctl restart europa-scraper
    echo "✅ Servicio systemd reiniciado"
elif [ -f "INICIAR_SERVIDOR.bat" ] || [ -f "iniciar_servidor_wsl_final.sh" ]; then
    echo "⚠️  No se detectó servicio systemd. Reiniciar manualmente:"
    echo "   cd $REPO_DIR && python -m server.main"
else
    echo "⚠️  Reiniciar el servidor manualmente según tu configuración"
fi

# 6. Verificar que arrancó
echo ""
echo "🏥 Verificando servidor en puerto 8001..."
sleep 3
if curl -s --max-time 5 http://localhost:8001/ > /dev/null 2>&1; then
    echo "✅ Servidor escuchando en puerto 8001"
else
    echo "⚠️  No se detectó el servidor en puerto 8001"
    echo "   Puede que necesite más tiempo para arrancar"
fi

echo ""
echo "========================================="
echo "  ✅ DEPLOY COMPLETADO"
echo "========================================="
echo ""
echo "Para usar Google AI Scraper:"
echo "  1. Abrir el cliente GUI"
echo "  2. Seleccionar 'Google AI' en el dropdown de motores"
echo "  3. Las búsquedas usarán site:usa.gov automáticamente"
echo ""