#!/bin/bash

echo "🚀 INSTALACIÓN DIRECTA DE FASTAPI (SIN COMPLICACIONES)"
echo "======================================================"

# Ir al directorio del proyecto
cd "$(dirname "$0")"

echo "📦 Instalando FastAPI y dependencias con --break-system-packages..."
pip install --break-system-packages --no-warn-script-location \
    fastapi \
    uvicorn[standard] \
    requests \
    python-multipart \
    pydantic \
    aiofiles

echo "🔍 Verificando instalación..."
python3 -c "
try:
    import fastapi
    import uvicorn
    import requests
    import pydantic
    import aiofiles
    print('✅ FastAPI y dependencias instaladas correctamente')
    print(f'FastAPI version: {fastapi.__version__}')
except ImportError as e:
    print(f'❌ Error: {e}')
    exit(1)
"

echo "✅ Instalación completada. Ahora ejecuta: ./iniciar_servidor_wsl_simple.sh"