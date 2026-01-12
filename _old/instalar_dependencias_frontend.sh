#!/bin/bash
echo "=================================================="
echo "   INSTALANDO DEPENDENCIAS PARA FRONTEND"
echo "=================================================="
echo

# Detectar Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python no encontrado. Por favor instale Python primero."
    exit 1
fi

echo "🐍 Usando Python: $PYTHON_CMD"
echo

# Instalar pandas para archivos Excel
echo "📦 Instalando pandas para procesamiento de archivos Excel..."
$PYTHON_CMD -m pip install pandas openpyxl

# Instalar dependencias del frontend si no existen
echo "📦 Instalando dependencias del frontend..."
$PYTHON_CMD -m pip install requests tkinter

echo
echo "=================================================="
echo "   ✅ DEPENDENCIAS INSTALADAS"
echo "=================================================="
echo
echo "📋 Dependencias instaladas:"
echo "   - pandas: Para procesar archivos Excel"
echo "   - openpyxl: Para leer archivos .xlsx"
echo "   - requests: Para comunicación con servidor"
echo "   - tkinter: Para interfaz gráfica"
echo
echo "🚀 Ahora puedes ejecutar el frontend:"
echo "   cd client && python main.py"
echo "=================================================="