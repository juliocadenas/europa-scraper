# Visualización de Resultados con Cloudflared Tunnel

## Descripción

Esta solución permite visualizar los archivos CSV generados por el scraper desde cualquier lugar, sin necesidad de configurar firewalls o puertos. Utiliza **Cloudflared Tunnel** para crear un túnel seguro y gratuito.

## Características

- ✅ **100% Gratuito** - No requiere dominio propio ni pago
- ✅ **Sin configuración de firewall** - Funciona a través de NAT
- ✅ **Acceso desde cualquier lugar** - Desde casa, trabajo, móvil
- ✅ **Auto-refresh** - Los archivos se actualizan automáticamente
- ✅ **Vista previa** - Previsualiza los CSVs antes de descargar
- ✅ **Descarga directa** - Descarga archivos individuales o todos en ZIP

## Requisitos

1. **cloudflared.exe** - Ya incluido en el proyecto
2. **Servidor corriendo** - El servidor principal debe estar activo
3. **Conexión a internet** - Para el túnel de Cloudflare

## Endpoints Disponibles

| Endpoint | Descripción |
|----------|-------------|
| `/viewer` | Página web principal con visor de resultados |
| `/api/list_results` | Lista todos los archivos CSV disponibles |
| `/api/download_file?filename=X` | Descarga un archivo individual |
| `/api/preview_csv?filename=X&rows=N` | Vista previa de un CSV (primeras N filas) |

## Instrucciones de Uso

### Paso 1: Iniciar el Servidor Principal

```bash
# En Linux/WSL
python server/main.py

# En Windows
python server\main.py
```

El servidor se iniciará en `http://localhost:8001`

### Paso 2: Iniciar Cloudflared Tunnel

#### En Windows:
```bash
INICIAR_CLOUDFLARED.bat
```

#### En Linux/WSL:
```bash
chmod +x iniciar_cloudflared.sh
./iniciar_cloudflared.sh
```

### Paso 3: Obtener la URL Pública

Cloudflared generará una URL como:
```
https://random-string.trycloudflare.com
```

**IMPORTANTE:** Copia esta URL, la necesitarás para acceder a los resultados.

### Paso 4: Acceder al Visor de Resultados

En tu navegador, abre la URL generada y agrega `/viewer` al final:

```
https://random-string.trycloudflare.com/viewer
```

## Uso del Visor Web

### Interfaz Principal

El visor muestra una tabla con todos los archivos CSV generados:

| Columna | Descripción |
|---------|-------------|
| Nombre | Nombre del archivo CSV |
| Tamaño | Tamaño del archivo en formato legible |
| Modificado | Fecha y hora de última modificación |
| Acciones | Botones para ver y descargar |

### Auto-Refresh

Puedes configurar el intervalo de actualización automática:

- **Desactivado** - No actualiza automáticamente
- **5 segundos** - Actualiza cada 5 segundos
- **10 segundos** - Actualiza cada 10 segundos (recomendado)
- **30 segundos** - Actualiza cada 30 segundos
- **1 minuto** - Actualiza cada minuto

### Vista Previa

1. Haz clic en el botón **👁️ Ver** de cualquier archivo
2. Se abrirá un modal con las primeras 50 filas del CSV
3. Puedes hacer scroll para ver más datos
4. Desde el modal también puedes descargar el archivo

### Descarga

Hay dos formas de descargar archivos:

1. **Individual**: Botón **⬇️ Descargar** en la tabla principal
2. **Desde la vista previa**: Botón **Descargar** en el modal

## API Directa (Opcional)

Si prefieres usar la API directamente desde tu código o con curl:

### Listar archivos:
```bash
curl https://random-string.trycloudflare.com/api/list_results
```

### Descargar archivo:
```bash
curl -O https://random-string.trycloudflare.com/api/download_file?filename=results.csv
```

### Vista previa:
```bash
curl "https://random-string.trycloudflare.com/api/preview_csv?filename=results.csv&rows=10"
```

## Solución de Problemas

### El servidor no está corriendo

**Error:** `El servidor no está corriendo en el puerto 8001`

**Solución:** Asegúrate de iniciar el servidor principal primero:
```bash
python server/main.py
```

### Cloudflared no genera URL

**Error:** No aparece ninguna URL después de iniciar cloudflared

**Solución:**
1. Verifica que tienes conexión a internet
2. Asegúrate de que cloudflared.exe tiene permisos de ejecución
3. Intenta descargar una versión más reciente de cloudflared

### La URL no funciona

**Error:** No se puede acceder a la URL generada

**Solución:**
1. Asegúrate de que cloudflared sigue corriendo (no cierres la terminal)
2. Verifica que el servidor principal sigue corriendo
3. Intenta recargar la página del navegador

### No aparecen archivos en el visor

**Error:** La tabla muestra "No hay archivos aún"

**Solución:**
1. Verifica que el scraping se haya ejecutado correctamente
2. Revisa que los archivos CSV estén en la carpeta `server/results/`
3. Asegúrate de que los archivos tengan extensión `.csv`

## Seguridad

- El túnel de Cloudflare es **HTTPS** (encriptado)
- La URL generada es **temporal** (cambia cada vez que reinicias cloudflared)
- Para mayor seguridad, considera usar un dominio propio con Cloudflare

## Notas Importantes

1. **No cierres la terminal de cloudflared** mientras quieras acceder a los resultados
2. **La URL cambia** cada vez que reinicias cloudflared
3. **El túnel es gratuito** pero tiene límites de uso (suficientes para uso personal)
4. **Los archivos se generan en el servidor** y se sirven a través del túnel

## Alternativa: Acceso Local

Si solo necesitas acceder desde la misma red local, puedes acceder directamente sin cloudflared:

```
http://localhost:8001/viewer
```

O desde otra computadora en la misma red:

```
http://IP_DEL_SERVIDOR:8001/viewer
```

## Soporte

Si tienes problemas, revisa los logs del servidor en la carpeta `logs/` o contacta al administrador del sistema.
