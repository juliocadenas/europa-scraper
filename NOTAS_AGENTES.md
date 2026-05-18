# Notas para Agentes (AI)

## Configuración de Red Tailscale

**IMPORTANTE:** El usuario trabaja con dos redes de Tailscale simultáneamente. Antes de ejecutar cualquier comando que interactúe con el servidor remoto (SSH, curl, scp, etc.), se debe cambiar a la red correcta:

```bash
tailscale switch juliocadenas@gmail.com
```

**Esto se ejecuta automáticamente en `INICIAR_FRONTEND.bat` antes de iniciar la GUI.**

También aplica para:
- Conexiones SSH al servidor
- curl a endpoints del servidor (ej: `http://<tailscale-ip>:8001/api/...`)
- Deploy de código al servidor
- Cualquier operación que requiera acceso remoto

## Servidor Remoto

El servidor de scraping se ejecuta en un VPS accesible vía Tailscale. La IP y configuración están en `client/server_config.json`.

## Estructura del Proyecto

- `client/` - Cliente GUI (Tkinter) + lógica de conexión
- `server/` - Servidor FastAPI con workers multiproceso
- `gui/` - Componentes de la interfaz gráfica
- `controllers/` - Controladores del scraper
- `utils/` - Utilidades (result_manager, search_engine, etc.)
- `plans/` - Planes de diagnóstico y fixes

## Problemas Conocidos (Resueltos)

- `ResultManager.cleanup_if_empty()` - Método faltante agregado (commit 1f238d1)
- `TimerManager.sync_from_server` - No existe, protegido con hasattr
- `is_resetting` bloqueando renderizado - Eliminado de 5 métodos
- Polling no iniciaba sin conexión - Ahora inicia incondicionalmente a los 4s
- `_monitor_job_completion` sin timeout - Agregado timeout de 2 horas
