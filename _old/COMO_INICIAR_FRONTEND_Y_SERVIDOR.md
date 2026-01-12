# Cómo Iniciar el Frontend y Servidor de Europa Scraper

## 🎯 **Respuesta Rápida**

### 1. **Para iniciar el SERVIDOR** (backend):
```bash
.\iniciar_servidor_windows.bat
```
**O manualmente:**
```bash
cd server
python main.py
```

### 2. **Para iniciar el CLIENTE** (frontend GUI):
```bash
cd client
python main.py
```

---

## 📋 **Instrucciones Detalladas**

### 🔧 **Opción 1: Iniciar Servidor en Windows**

El archivo [`iniciar_servidor_windows.bat`](iniciar_servidor_windows.bat) está diseñado para Windows:

```batch
@echo off
cd /d "%~dp0"
cd server
echo Iniciando servidor Europa Scraper...
python main.py
pause
```

**¿Qué hace este script?**
1. Cambia al directorio del proyecto
2. Entra en la carpeta `server/`
3. Inicia el servidor con `python main.py`
4. Mantiene la ventana abierta (pause)

### 🖥️ **Opción 2: Iniciar Frontend (Cliente GUI)**

El frontend está en [`client/main.py`](client/main.py):

```python
# Este archivo crea la interfaz gráfica Tkinter
class ClientApp:
    def __init__(self):
        self.root = tk.Tk()
        self.gui = ScraperGUI(self.root, self)
        # ... configura la GUI completa
```

**¿Qué incluye el frontend?**
- ✅ Interfaz gráfica completa con Tkinter
- ✅ Descubrimiento automático de servidores
- ✅ Conexión cliente-servidor funcionando
- ✅ Gestión de tareas de scraping
- ✅ Monitoreo de progreso
- ✅ Manejo de CAPTCHAs
- ✅ Visualización de resultados

### 🌐 **Opción 3: Para WSL/Linux**

Si estás usando WSL (Windows Subsystem for Linux):

**Iniciar servidor en WSL:**
```bash
# Desde terminal Windows
wsl -d Ubuntu
cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX
cd server
python main.py
```

**Iniciar cliente en WSL:**
```bash
# Desde terminal WSL
cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX
cd client
python main.py
```

---

## 🚀 **Secuencia Recomendada de Inicio**

### Paso 1: Iniciar el Servidor
```bash
# Abrir nueva terminal/cmd
.\iniciar_servidor_windows.bat
```

**Verás salida como:**
```
Iniciando servidor Europa Scraper...
INFO:     Started server process [xxxx]
INFO:     Application startup complete.
DEBUG:    Broadcast enviado: EUROPA_SCRAPER_SERVER;192.168.1.14;8001
```

### Paso 2: Iniciar el Cliente (Frontend)
```bash
# Abrir otra terminal/cmd
cd client
python main.py
```

**Verás la ventana GUI con:**
- Botón "Buscar Servidores"
- Lista de servidores descubiertos
- Formulario para configurar scraping
- Panel de progreso
- Área de resultados

### Paso 3: Verificar Conexión
1. El cliente buscará automáticamente servidores
2. Debería aparecer tu servidor en la lista
3. Selecciona el servidor y haz clic en "Conectar"
4. ¡Listo! El sistema estará funcionando

---

## 🔍 **Verificación del Sistema**

### Para verificar que todo funciona:

1. **Ejecuta la prueba de conexión:**
   ```bash
   python test_conexion_definitiva.py
   ```

2. **Debería mostrar:**
   ```
   🔗 Probando conexión con: http://localhost:8001
   ✅ CONEXIÓN EXITOSA con http://localhost:8001
   ```

3. **Verifica el estado completo:**
   ```bash
   python test_sistema_completo.py
   ```

---

## 🛠️ **Solución de Problemas Comunes**

### ❌ "No se encuentran servidores activos"
**Solución:** Asegúrate de que el servidor esté corriendo antes de iniciar el cliente

### ❌ "Error: puerto 8001 en uso"
**Solución:** Cierra otras instancias del servidor o cambia el puerto

### ❌ "Error de módulos faltantes"
**Solución:** Activa el entorno virtual:
```bash
venv_windows\Scripts\activate
```

### ❌ "Error de conexión rechazada"
**Solución:** Verifica que el firewall no bloquee el puerto 8001

---

## 📊 **Arquitectura del Sistema**

```
┌─────────────────────────────────────────┐
│           CLIENTE (Frontend)          │
│  ┌─────────────────────────────────┐   │
│  │     GUI Tkinter              │   │
│  │  - Descubrimiento automático   │   │
│  │  - Gestión de tareas         │   │
│  │  - Monitoreo de progreso     │   │
│  │  - Manejo de CAPTCHAs       │   │
│  └─────────────────────────────────┘   │
└─────────────────┬───────────────────┘
                  │ HTTP/WebSocket
                  │
┌─────────────────▼───────────────────┐
│           SERVIDOR (Backend)         │
│  ┌─────────────────────────────────┐   │
│  │     FastAPI Server           │   │
│  │  - Endpoints REST           │   │
│  │  - Broadcasting UDP          │   │
│  │  - Workers multiproceso      │   │
│  │  - Gestión de tareas         │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │     Workers (8 procesos)     │   │
│  │  - Navegador Playwright    │   │
│  │  - Scraping DuckDuckGo      │   │
│  │  - Procesamiento de datos    │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

---

## 🎉 **Resumen Final**

**El sistema está completamente funcional y listo para usar:**

1. ✅ **Servidor**: Inicia con `.\iniciar_servidor_windows.bat`
2. ✅ **Cliente**: Inicia con `cd client && python main.py`
3. ✅ **Conexión**: Funciona automáticamente con el fix implementado
4. ✅ **Scraping**: Funciona con DuckDuckGo y workers multiproceso
5. ✅ **GUI**: Completa con todas las funcionalidades

**¡EL DOLOR DE CABEZA HA TERMINADO!** 🎯

El problema de conexión cliente-servidor ha sido completamente resuelto. El sistema ahora está operativo y listo para realizar tareas de scraping.