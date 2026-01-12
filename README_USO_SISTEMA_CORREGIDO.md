# Europa Scraper - Sistema Corregido

## 🚀 Inicio Rápido

### Opción 1: Usar los archivos .bat (Recomendado)

#### Para Windows normal:
```bash
# Iniciar el servidor
INICIAR_SERVIDOR.bat

# Iniciar el frontend (GUI)
INICIAR_FRONTEND.bat
```

#### Para WSL (Windows Subsystem for Linux):
```bash
# Iniciar el servidor (optimizado para WSL)
INICIAR_SERVIDOR_WSL.bat

# Iniciar el frontend (GUI) en WSL
INICIAR_FRONTEND_WSL.bat
```

### Opción 2: Usar los scripts Python

```bash
# Iniciar el servidor
python iniciar_servidor_corregido.py

# Iniciar el frontend
python gui/scraper_gui.py
```

### Opción 3: Inicio automático completo

```bash
python iniciar_gui_con_servidor_corregido.py
```

## ✅ ¿Qué está corregido?

1. **Problema original**: El servidor respondía correctamente pero con código HTTP 200
2. **Error del cliente**: La GUI esperaba código 202 para considerar éxito
3. **Solución**: Servidor ahora devuelve código 202 explícitamente
4. **Resultado**: ✅ Sin más mensajes de error falsos

## 📋 Pasos para Usar el Sistema

### Paso 1: Iniciar el Servidor
Ejecuta `INICIAR_SERVIDOR.bat` o `python iniciar_servidor_corregido.py`
- Verás: "🚀 Iniciando Servidor Europa Scraper Corregido"
- El servidor iniciará en el puerto 8001

### Paso 2: Iniciar el Frontend
Ejecuta `INICIAR_FRONTEND.bat` o `python gui/scraper_gui.py`
- La GUI se conectará automáticamente al servidor
- Verás: "Conectado" en verde

### Paso 3: Usar el Sistema
1. En la GUI, haz clic en "CARGAR CURSOS (CSV/XLS)" si necesitas cargar datos
2. Selecciona los rangos de códigos SIC
3. Elige el motor de búsqueda (DuckDuckGo, Google, etc.)
4. Haz clic en "Iniciar Scraping"
5. Los resultados se guardarán en la carpeta `results/`

## 🔧 Configuración

### Servidor
- **Puerto**: 8001
- **Host**: 0.0.0.0 (accesible desde cualquier red)
- **Endpoints**:
  - Ping: `http://localhost:8001/ping`
  - Scraping: `http://localhost:8001/start_scraping`
  - Cursos: `http://localhost:8001/get_all_courses`

### Cliente GUI
- **URL del servidor**: `http://localhost:8001` (configurado automáticamente)
- **Formato de datos**: JSON anidado `{"job_params": {...}}`
- **Códigos de estado**: 202 = éxito, otros = error

## 🐛 Solución de Problemas

### "No se puede conectar al servidor"
1. Asegúrate que el servidor esté corriendo
2. Verifica que el puerto 8001 esté libre
3. Ejecuta `python probar_servidor_actual.py` para diagnóstico

### "El servidor ya está corriendo"
El script `iniciar_servidor_corregido.py` detecta y limpia automáticamente procesos en el puerto 8001.

### "Error de dependencias"
Ejecuta:
```bash
pip install psutil fastapi uvicorn requests
```

### "La GUI no muestra los cursos"
1. Conéctate al servidor en la pestaña "Configuración del Servidor"
2. Haz clic en "Refrescar Lista de Cursos"

## 📁 Archivos Importantes

```
📁 INICIAR_SERVIDOR.bat          # Inicia el servidor corregido
📁 INICIAR_FRONTEND.bat           # Inicia la GUI
📁 iniciar_servidor_corregido.py   # Script de inicio del servidor
📁 gui/scraper_gui.py             # Interfaz gráfica
📁 server/main_wsl_corregido.py   # Servidor corregido
📁 results/                        # Carpeta de resultados
```

## 🎯 Flujo de Trabajo

1. **Inicio**: `INICIAR_SERVIDOR.bat`
2. **Frontend**: `INICIAR_FRONTEND.bat`
3. **Carga**: Cargar cursos desde archivo si es necesario
4. **Selección**: Elegir rangos SIC
5. **Scraping**: Iniciar el proceso
6. **Resultados**: Revisar archivos CSV generados

## 📊 Ejemplo de Uso

```bash
# 1. Iniciar servidor
INICIAR_SERVIDOR.bat

# 2. Esperar a que inicie (verás los logs)

# 3. Iniciar GUI
INICIAR_FRONTEND.bat

# 4. En la GUI:
#    - Conectar a http://localhost:8001
#    - Cargar cursos si es necesario
#    - Seleccionar rango 600 a 604
#    - Elegir DuckDuckGo
#    - Hacer clic en "Iniciar Scraping"

# 5. Resultado:
#    ✅ "Scraping corregido completado. Se generaron 5 resultados"
#    📁 results/corregidos_600_to_604_DuckDuckGo_YYYYMMDD_HHMMSS.csv
```

---
**Estado**: ✅ Sistema funcionando correctamente  
**Versión**: v3.1-LINUX Corregida  
**Fecha**: 25/11/2025