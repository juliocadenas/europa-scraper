#!/bin/bash

echo "🚀 Instalando FastAPI y dependencias esenciales para WSL..."
echo "=================================================="

# Ir al directorio del proyecto
cd "$(dirname "$0")"
echo "📁 Directorio del proyecto: $(pwd)"

# Instalar dependencias esenciales con pip
echo "📦 Instalando FastAPI y dependencias esenciales..."

# Verificar si estamos en un entorno virtual
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "🔧 Detectado entorno virtual: $VIRTUAL_ENV"
    echo "📦 Instalando en el entorno virtual..."
    python3 -m pip install \
        fastapi \
        uvicorn[standard] \
        requests \
        python-multipart \
        pydantic \
        aiofiles
else
    echo "🔧 No se detectó entorno virtual, intentando instalación con --user..."
    python3 -m pip install --user \
        fastapi \
        uvicorn[standard] \
        requests \
        python-multipart \
        pydantic \
        aiofiles
fi

# Verificar instalación
echo "🔍 Verificando instalación..."
python3 -c "
try:
    import fastapi
    import uvicorn
    import requests
    import pydantic
    import aiofiles
    print('✅ FastAPI y dependencias esenciales instaladas correctamente')
    print(f'FastAPI version: {fastapi.__version__}')
    print(f'Uvicorn version: {uvicorn.__version__}')
except ImportError as e:
    print(f'❌ Error importando módulo: {e}')
    exit(1)
"

echo "✅ Instalación completada"
echo "🎯 Ahora puedes iniciar el servidor con: ./iniciar_servidor_wsl_simple.sh"