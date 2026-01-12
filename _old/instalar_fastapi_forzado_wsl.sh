#!/bin/bash

echo "🚀 INSTALACIÓN FORZADA DE FASTAPI PARA WSL"
echo "=========================================="
echo "⚠️  Este script usará --break-system-packages como última opción"
echo

# Ir al directorio del proyecto
cd "$(dirname "$0")"
echo "📁 Directorio del proyecto: $(pwd)"

# Verificar si estamos en un entorno virtual
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "🔧 Detectado entorno virtual: $VIRTUAL_ENV"
    echo "📦 Instalando en el entorno virtual con --break-system-packages..."
    python3 -m pip install --break-system-packages \
        fastapi \
        uvicorn[standard] \
        requests \
        python-multipart \
        pydantic \
        aiofiles
else
    echo "🔧 Entorno del sistema detectado"
    echo "📦 Intentando instalación forzada (--break-system-packages)..."
    python3 -m pip install --break-system-packages \
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
    print('✅ FastAPI y dependencias instaladas correctamente')
    print(f'FastAPI version: {fastapi.__version__}')
    print(f'Uvicorn version: {uvicorn.__version__}')
except ImportError as e:
    print(f'❌ Error importando módulo: {e}')
    print('💡 Intenta activar un entorno virtual primero:')
    print('   source venv_wsl/bin/activate')
    exit(1)
"

echo "✅ Instalación completada"
echo "🎯 Ahora puedes iniciar el servidor con: ./iniciar_servidor_wsl_simple.sh"