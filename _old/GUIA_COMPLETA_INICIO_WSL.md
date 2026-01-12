# 🚀 Guía Completa de Inicio - Europa Scraper para WSL

## 📋 Resumen del Sistema

He creado un sistema completo y optimizado para Europa Scraper con solución específica para WSL y manejo de memoria.

## 🎯 Problemas Resueltos

### ✅ Problema Original
- **Problema**: Servidor devolvía código 200 en lugar de 202
- **Solución**: Servidor ahora devuelve código 202 explícitamente
- **Resultado**: ✅ Sistema funciona sin mensajes de error falsos

### ✅ Problema de Dependencias
- **Problema**: Script optimizado dependía de `psutil` que no estaba disponible
- **Solución**: Modificado `iniciar_servidor_corregido.py` para que psutil sea opcional
- **Resultado**: ✅ Sistema funciona con o sin psutil, usando métodos alternativos

### ✅ Problema de FastAPI
- **Problema**: `ModuleNotFoundError: No module named 'fastapi'`
- **Solución**: Usar script existente `instalar_dependencias_wsl.sh`
- **Resultado**: ✅ Todas las dependencias instaladas correctamente

## 📁 Scripts Disponibles

### Scripts Principales
| Script | Tipo | Descripción | Dependencias |
|--------|------|-------------|-------------|
| `iniciar_servidor_wsl_simple.sh` | WSL | Servidor simple sin dependencias | Ninguna ✅ |
| `iniciar_servidor_wsl_optimizado.sh` | WSL | Servidor con optimización avanzada | psutil opcional ✅ |
| `iniciar_frontend_wsl.sh` | WSL | Frontend con espera inteligente | Ninguna ✅ |

### Scripts de Acceso desde Windows
| Script | Tipo | Descripción |
|--------|------|-------------|
| `INICIAR_SERVIDOR_SIMPLE_WSL.bat` | Windows | Lanza servidor simple WSL |
| `INICIAR_SERVIDOR_WSL.bat` | Windows | Lanza servidor optimizado WSL |
| `INICIAR_FRONTEND_WSL.bat` | Windows | Lanza frontend WSL |
| `HACER_EJECUTABLES_WSL.ps1` | PowerShell | Hace ejecutables los .sh |

## 🚀 Métodos de Inicio

### ⚠️ PASO OBLIGATORIO - Instalar Dependencias

**ANTES de usar cualquier método, instala las dependencias:**

#### Desde Windows:
```bash
instalar_dependencias_wsl.bat
```

#### Desde WSL:
```bash
chmod +x instalar_dependencias_wsl.sh
./instalar_dependencias_wsl.sh
```

### Método 1: Recomendado (Simple sin Dependencias)

#### Desde Windows:
```bash
# 1. Preparar (solo la primera vez)
powershell -ExecutionPolicy Bypass -File HACER_EJECUTABLES_WSL.ps1

# 2. Iniciar servidor
INICIAR_SERVIDOR_SIMPLE_WSL.bat

# 3. En otra terminal, iniciar frontend
INICIAR_FRONTEND_WSL.bat
```

#### Desde WSL:
```bash
# 1. Hacer ejecutables (solo la primera vez)
chmod +x iniciar_servidor_wsl_simple.sh iniciar_frontend_wsl.sh

# 2. Iniciar servidor
./iniciar_servidor_wsl_simple.sh

# 3. En otra terminal, iniciar frontend
./iniciar_frontend_wsl.sh
```

### Método 2: Optimizado (psutil opcional)

**✅ Ahora funciona con o sin psutil**

#### Si quieres psutil para mejor monitoreo:
```bash
# Opción 1: Con venv activado
pip install psutil

# Opción 2: A nivel de sistema (si tienes permisos)
sudo apt update && sudo apt install python3-psutil
```

#### Desde Windows:
```bash
# 1. Iniciar servidor optimizado
INICIAR_SERVIDOR_WSL.bat

# 2. En otra terminal, iniciar frontend
INICIAR_FRONTEND_WSL.bat
```

#### Desde WSL:
```bash
# 1. Hacer ejecutables
chmod +x iniciar_servidor_wsl_optimizado.sh iniciar_frontend_wsl.sh

# 2. Iniciar servidor optimizado
./iniciar_servidor_wsl_optimizado.sh

# 3. En otra terminal, iniciar frontend
./iniciar_frontend_wsl.sh
```

## 🔧 Optimizaciones Implementadas

### Script Simple (Recomendado)
```bash
export PYTHONOPTIMIZE=1
export MALLOC_TRIM_THRESHOLD_=100000
ulimit -vS 1048576
```

### Script Optimizado
```bash
export PYTHONOPTIMIZE=1
export MALLOC_TRIM_THRESHOLD_=100000
export MALLOC_ARENA_MAX=131072
ulimit -vS 1048576
# + Limpieza automática con psutil
```

## 📊 Características del Sistema

### ✅ Características Principales
- **Servidor corregido**: Devuelve código 202 correctamente
- **Manejo de memoria**: Optimizado para WSL
- **Limpieza automática**: Mata procesos previos
- **Conexión inteligente**: Frontend espera a servidor
- **Múltiples opciones**: Simple u optimizado
- **Acceso desde Windows**: Scripts .bat incluidos

### 🔧 Características Técnicas
- **Puerto**: 8001 por defecto
- **Host**: 0.0.0.0 (accesible desde Windows)
- **Optimización**: PYTHONOPTIMIZE=1
- **Memoria**: Límites configurados
- **Reintentos**: 3 intentos con espera de 2s

## 🛠️ Solución de Problemas

### Problemas Comunes

#### 1. "psutil not found"
**Solución**: Usar script simple
```bash
./iniciar_servidor_wsl_simple.sh
```

#### 2. "Permission denied"
**Solución**: Hacer ejecutable
```bash
chmod +x iniciar_servidor_wsl_simple.sh
```

#### 3. "Address already in use"
**Solución**: El script limpia automáticamente, pero si persiste:
```bash
pkill -f "python.*iniciar_servidor"
```

#### 4. Frontend no conecta
**Solución**: Verificar que el servidor esté corriendo
```bash
curl http://localhost:8001/health
```

## 📝 Logs y Monitoreo

### Ubicación de Logs
- **Servidor**: Consola donde se inició
- **Frontend**: Consola donde se inició
- **Resultados**: `server/results/`

### Verificar Estado
```bash
# Ver procesos del servidor
ps aux | grep iniciar_servidor

# Ver puerto en uso
netstat -tlnp | grep 8001

# Probar conexión
curl http://localhost:8001/health
```

## 🎯 Flujo de Trabajo Recomendado

### Para Desarrollo Diario:
1. Usar **Método 1 (Simple)** - más estable
2. Abrir dos terminales
3. Iniciar servidor en una
4. Iniciar frontend en la otra
5. Trabajar normalmente

### Para Producción:
1. Usar **Método 2 (Optimizado)** si psutil disponible
2. Monitorear consumo de memoria
3. Revisar logs periódicamente
4. Usar scripts .bat desde Windows para facilidad

## 🔄 Actualizaciones Futuras

El sistema está diseñado para ser:
- **Modular**: Fácil de extender
- **Robusto**: Manejo de errores
- **Flexible**: Múltiples opciones de inicio
- **Compatible**: Funciona en Windows y WSL

## 📞 Soporte

Si encounteras problemas:
1. Revisa esta guía
2. Usa el script simple (menos dependencias)
3. Verifica que WSL esté funcionando
4. Revisa permisos de los scripts

---

**🟢 ESTADO: SISTEMA COMPLETO Y FUNCIONAL**

✅ Servidor corregido con código 202  
✅ Scripts simples sin dependencias  
✅ Optimización de memoria para WSL  
✅ Múltiples opciones de inicio  
✅ Documentación completa  
✅ Acceso desde Windows y WSL