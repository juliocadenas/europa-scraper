#!/bin/bash

# Script para instalar dependencias del servidor Europa Scraper en WSL/Linux
echo "Instalando dependencias para Europa Scraper en WSL/Linux..."

# Ir al directorio del proyecto
cd "$(dirname "$0")"
echo "Directorio del proyecto: $(pwd)"

# Verificar si estamos en WSL
if grep -q Microsoft /proc/version 2>/dev/null; then
    echo "Detectado WSL, instalando dependencias..."
elif [[ "$WSL_DISTRO_NAME" != "" ]] || [[ -f "/proc/version" ]]; then
    echo "Entorno Linux detectado, continuando con instalación..."
else
    echo "⚠️  No se pudo detectar WSL/Linux, pero continuando con instalación..."
    echo "Si estás en un entorno compatible, presiona Enter para continuar o Ctrl+C para cancelar"
    read -r
fi

# Actualizar paquetes del sistema
echo "Actualizando paquetes del sistema..."
sudo apt update && sudo apt upgrade -y

# Instalar Python3 y pip si no están instalados
echo "Verificando Python3..."
if ! command -v python3 &> /dev/null; then
    echo "Instalando Python3..."
    sudo apt install python3 python3-pip python3-venv -y
fi

# Instalar dependencias del sistema para Playwright
echo "Instalando dependencias del sistema para Playwright..."
sudo apt install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    software-properties-common \
    build-essential \
    python3-dev \
    libnss3-dev \
    libatk-bridge2.0-dev \
    libdrm-dev \
    libxkbcommon-dev \
    libxcomposite-dev \
    libxdamage-dev \
    libxrandr-dev \
    libgbm-dev \
    libxss-dev \
    libasound2-dev

# Instalar dependencias de Python
echo "Instalando dependencias de Python..."
python3 -m pip install --upgrade pip

# Instalar dependencias básicas
echo "Instalando dependencias básicas..."
python3 -m pip install \
    fastapi \
    uvicorn[standard] \
    requests \
    pandas \
    beautifulsoup4 \
    lxml \
    openpyxl \
    sqlite3 \
    python-multipart \
    aiofiles \
    python-dotenv \
    pydantic

# Instalar Playwright
echo "Instalando Playwright..."
python3 -m pip install playwright

# Instalar navegadores de Playwright
echo "Instalando navegadores de Playwright..."
python3 -m playwright install chromium

# Verificar instalación
echo "Verificando instalación..."
python3 -c "
try:
    import fastapi
    import uvicorn
    import requests
    import pandas
    import playwright
    print('✅ Todas las dependencias principales instaladas correctamente')
except ImportError as e:
    print(f'❌ Error importando módulo: {e}')
    exit(1)
"

echo "✅ Dependencias instaladas correctamente en WSL/Linux"
echo "Ahora puedes iniciar el servidor con: ./iniciar_servidor_linux.sh"