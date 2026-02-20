# Instrucciones para el Visualizador de Resultados Completo

## Resumen

Este sistema permite visualizar los archivos CSV generados por el scraper desde cualquier lugar, usando un túnel seguro de Cloudflare. No requiere permisos de root ni configuración de firewall.

## Componentes

1. **results_viewer_completo.py** - Servidor HTTP independiente que sirve los archivos CSV
2. **cloudflared** - Túnel seguro que expone el visor a internet
3. **Script de inicio** - Inicia ambos servicios automáticamente

## Requisitos

- Python 3 instalado en el servidor
- cloudflared descargado en el servidor
- Acceso SSH al servidor

## Instalación Paso a Paso

### Paso 1: Copiar el script del visor al servidor

1. Abre el archivo `results_viewer_script_para_copiar.txt` en tu máquina local
2. Copia TODO el contenido del archivo
3. Conéctate al servidor01 via SSH
4. Pega el contenido en la terminal y presiona Enter

El script creará automáticamente:
- `~/results_viewer_completo.py` - El servidor del visor
- Iniciará el visor en segundo plano

### Paso 2: Descargar cloudflared (si no lo tienes)

```bash
# En el servidor01
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
mv cloudflared-linux-amd64 cloudflared
```

### Paso 3: Iniciar el visor y cloudflared

**Opción A: Usar el script completo (recomendado)**

```bash
# Copiar el archivo iniciar_todo_viewer.sh al servidor
chmod +x iniciar_todo_viewer.sh
./iniciar_todo_viewer.sh
```

**Opción B: Iniciar manualmente**

```bash
# 1. Iniciar el visor
nohup ~/results_viewer_completo.py > ~/results_viewer.log 2>&1 &

# 2. Iniciar cloudflared
./cloudflared tunnel --url http://localhost:8888
```

### Paso 4: Acceder al visor

1. Espera a que cloudflared genere una URL pública (aparecerá en la terminal)
2. La URL tendrá el formato: `https://random-string.trycloudflare.com`
3. Abre esa URL en tu navegador
4. ¡Listo! Podrás ver los archivos CSV en tiempo real

## Uso del Visor

### Pestañas

El visor tiene dos pestañas:

1. **Resultados Exitosos** - Archivos CSV de la carpeta `results/`
2. **Archivos Omitidos** - Archivos CSV de la carpeta `omitidos/`

### Funcionalidades

- **Auto-refresh**: Configurable (5s, 10s, 30s, 1 minuto)
- **Vista previa**: Ver las primeras 50 filas de cualquier CSV
- **Descarga**: Descargar archivos individuales
- **URL de Cloudflare**: Se muestra automáticamente en la página

### Comandos de Control

```bash
# Verificar que el visor está corriendo
ps aux | grep results_viewer_completo

# Ver logs del visor
tail -f ~/results_viewer.log

# Detener el visor
pkill -f results_viewer_completo.py

# Reiniciar el visor
pkill -f results_viewer_completo.py
nohup ~/results_viewer_completo.py > ~/results_viewer.log 2>&1 &

# Ver logs de cloudflared
tail -f /home/julio/cloudflared_logs/cloudflared_*.log

# Detener cloudflared
pkill -f cloudflared

# Detener todo (visor + cloudflared)
./detener_viewer.sh
```

## Endpoints del Visor

| Endpoint | Descripción |
|----------|-------------|
| `/` | Página principal con pestañas |
| `/api/list` | Lista archivos de results/ |
| `/api/list_omitidos` | Lista archivos de omitidos/ |
| `/api/download?filename=X` | Descarga un archivo |
| `/api/preview?filename=X&rows=N` | Vista previa de CSV |
| `/api/cloudflare_url` | Obtiene la URL de cloudflared |

## Solución de Problemas

### El visor no inicia

```bash
# Verificar que no hay otro proceso usando el puerto 8888
lsof -i :8888

# Ver logs del visor
cat ~/results_viewer.log
```

### Cloudflared no genera URL

```bash
# Verificar que cloudflared está corriendo
ps aux | grep cloudflared

# Ver logs de cloudflared
tail -f /home/julio/cloudflared_logs/cloudflared_*.log
```

### No puedo acceder a la URL

1. Verifica que cloudflared esté corriendo
2. Espera unos segundos a que la URL se propague
3. Intenta acceder directamente a `http://localhost:8888` desde el servidor

### La URL de cloudflared cambia

Esto es normal. Las URLs gratuitas de trycloudflare.com cambian cada vez que reinicias cloudflared. La página del visor muestra automáticamente la URL actual.

## Integración con el Servidor FastAPI

El servidor FastAPI principal (`server/server.py`) también tiene endpoints de visualización:

| Endpoint | Descripción |
|----------|-------------|
| `/viewer` | Visor con pestañas (results/omitidos) |
| `/api/list_results` | Lista archivos de results/ |
| `/api/list_omitidos` | Lista archivos de omitidos/ |
| `/api/download_file?filename=X` | Descarga un archivo |
| `/api/preview_csv?filename=X&rows=N` | Vista previa de CSV |
| `/api/cloudflare_url` | Obtiene la URL de cloudflared |

Para usar el visor del servidor FastAPI, inicia cloudflared en el puerto 8001:

```bash
./cloudflared tunnel --url http://localhost:8001
```

Luego accede a: `https://random-string.trycloudflare.com/viewer`

## Archivos Creados

- `results_viewer_completo.py` - Servidor HTTP del visor
- `iniciar_todo_viewer.sh` - Script para iniciar todo
- `iniciar_cloudflared_viewer.sh` - Script solo para cloudflared
- `detener_viewer.sh` - Script para detener todo
- `results_viewer_script_para_copiar.txt` - Script para copiar al servidor

## Notas Importantes

1. **Sin permisos de root**: Este sistema funciona sin permisos de administrador
2. **Sin configuración de firewall**: Cloudflared usa conexiones salientes, no requiere abrir puertos
3. **HTTPS automático**: Cloudflared proporciona HTTPS automáticamente
4. **URL temporal**: Las URLs gratuitas cambian al reiniciar cloudflared
5. **Logs guardados**: Todos los logs se guardan en `/home/julio/cloudflared_logs/`

## Soporte

Si tienes problemas:

1. Revisa los logs: `~/results_viewer.log`
2. Revisa los logs de cloudflared: `/home/julio/cloudflared_logs/`
3. Verifica que los procesos estén corriendo: `ps aux | grep -E "results_viewer|cloudflared"`
