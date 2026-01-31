#!/bin/bash

# ==============================================================================
# Script de Despliegue Automático para Ubuntu Server - EUROPA SCRAPER
# Optimized for: 48 Threads / 300GB RAM
# ==============================================================================

set -e

echo "🚀 Iniciando despliegue de Europa Scraper..."

# 1. Actualizar sistema e instalar dependencias básicas
echo "📦 Actualizando paquetes del sistema..."
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git

# 2. Instalar Docker y Docker Compose si no están presentes
if ! command -v docker &> /dev/null; then
    echo "🐳 Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "Docker instalado correctamente."
else
    echo "✅ Docker ya está instalado."
fi

if ! docker compose version &> /dev/null; then
    echo "🐳 Instalando Docker Compose..."
    sudo apt-get install -y docker-compose-plugin
else
    echo "✅ Docker Compose ya está instalado."
fi

# 3. Preparar estructura de directorios y archivos de base de datos
echo "📁 Preparando directorios y archivos de datos..."
mkdir -p results logs client

# Crear archivos de base de datos vacíos si no existen para que Docker no los cree como directorios
touch courses.db counties.db

# 4. Asegurar que los permisos sean correctos
sudo chown -R $USER:$USER .

# 5. Construir e iniciar el contenedor
echo "🏗️ Construyendo e iniciando contenedores con Docker Compose..."
# Forzar la reconstrucción para asegurar que se aplican los cambios del Dockerfile
docker compose up -d --build

echo "===================================================================="
echo "✅ DESPLIEGUE COMPLETADO EXITOSAMENTE"
echo "===================================================================="
echo "🖥️ El servidor está corriendo en el puerto 8001"
echo "📡 El puerto UDP 6000 está abierto para descubrimiento automático"
echo "🧵 Configuración detectada: 48 hilos (el sistema usará 48 workers por defecto)"
echo "💾 Memoria reservada: hasta 250GB"
echo ""
echo "Comandos útiles:"
echo " - Ver logs: docker compose logs -f"
echo " - Detener: docker compose down"
echo " - Reiniciar: docker compose restart"
echo "===================================================================="
echo "⚠️ NOTA: Si es la primera vez que instalas docker, puede que necesites"
echo "cerrar sesión y volver a entrar para que los permisos de grupo surtan efecto,"
echo "o ejecutar comandos con 'sudo' por esta vez."
