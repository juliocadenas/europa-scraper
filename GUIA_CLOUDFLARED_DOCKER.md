# Guía Paso a Paso: Visualización de Resultados con Cloudflared (Docker)

## Tu Situación
- **Frontend**: Corre en tu máquina local (Windows)
- **Servidor**: Corre en Docker en el servidor01 (remoto)
- **Puerto mapeado**: 8001 (host) → 8001 (container)
- **Objetivo**: Ver los archivos CSV generados en el servidor01 desde tu navegador local

---

## Paso 1: Conectarte al Servidor Remoto

Abre PowerShell o CMD y ejecuta:

```bash
ssh julio@servidor01
```

---

## Paso 2: Verificar que el Contenedor Docker Está Corriendo

Una vez conectado al servidor01, verifica que el contenedor está activo:

```bash
docker ps
```

Deberías ver algo como:

```
CONTAINER ID   IMAGE                    COMMAND                  CREATED        STATUS        PORTS                    NAMES
abc123def456   europa-scraper-prod      "python server/main.py"   2 hours ago    Up 2 hours    0.0.0.0:8001->8001/tcp   europa-scraper-prod
```

**IMPORTANTE:** El contenedor debe estar en estado "Up" y el puerto 8001 debe estar mapeado.

### Si el contenedor NO está corriendo:

Inícialo con:

```bash
docker-compose up -d
```

O si usas docker run directamente:

```bash
docker start europa-scraper-prod
```

---

## Paso 3: Verificar que el Servidor Responde

Prueba que el servidor está respondiendo en el puerto 8001:

```bash
curl http://localhost:8001/ping
```

Deberías ver:
```
EUROPA_SCRAPER_SERVER_PONG
```

Si ves este mensaje, el servidor está funcionando correctamente.

---

## Paso 4: Descargar cloudflared en el Servidor01

Si cloudflared no está instalado en el servidor01, descárgalo:

```bash
# Descargar cloudflared para Linux AMD64
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64

# Moverlo a /usr/local/bin y darle permisos
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared
```

Verificar la instalación:

```bash
cloudflared --version
```

---

## Paso 5: Iniciar Cloudflared Tunnel

Ahora inicia cloudflared para exponer el puerto 8001:

```bash
cloudflared tunnel --url http://localhost:8001
```

Cloudflared generará una URL como esta:

```
https://random-string.trycloudflare.com
```

**COPIA ESTA URL** - La necesitarás para acceder desde tu navegador local.

Ejemplo real:
```
https://abc123def456.trycloudflare.com
```

---

## Paso 6: Acceder al Visor desde tu Navegador Local

En tu navegador (en tu máquina Windows), abre la URL que copiaste y agrega `/viewer` al final:

```
https://abc123def456.trycloudflare.com/viewer
```

¡Listo! Ahora deberías ver el visor de resultados con todos los archivos CSV generados.

---

## Resumen de Comandos

| Paso | Comando | ¿Dónde? |
|------|---------|---------|
| 1 | `ssh julio@servidor01` | Tu PC local |
| 2 | `docker ps` | Servidor01 |
| 3 | `curl http://localhost:8001/ping` | Servidor01 |
| 4 | `cloudflared tunnel --url http://localhost:8001` | Servidor01 |
| 5 | Copiar URL | Servidor01 |
| 6 | Abrir URL en navegador | Tu PC local |

---

## Diagrama de Flujo

```
┌─────────────────┐
│  Tu PC Local    │
│  (Windows)      │
└────────┬────────┘
         │
         │ 1. SSH al servidor01
         ▼
┌─────────────────┐
│  Servidor01     │
│  (Host Linux)   │
└────────┬────────┘
         │
         │ 2. Docker Container (europa-scraper-prod)
         │    Puerto 8001 mapeado
         │
         │ 3. Cloudflared Tunnel
         │    cloudflared tunnel --url http://localhost:8001
         │
         │ 4. Obtener URL pública
         ▼
┌─────────────────┐
│  Cloudflare     │
│  Tunnel         │
└────────┬────────┘
         │
         │ 5. URL HTTPS pública
         ▼
┌─────────────────┐
│  Tu Navegador   │
│  (Chrome/Edge)  │
└─────────────────┘
```

---

## Comandos Útiles de Docker

### Ver logs del contenedor:

```bash
docker logs -f europa-scraper-prod
```

### Entrar al contenedor:

```bash
docker exec -it europa-scraper-prod bash
```

### Reiniciar el contenedor:

```bash
docker restart europa-scraper-prod
```

### Ver archivos results en el host:

```bash
ls -la results/
```

---

## Solución de Problemas

### Problema: "docker ps" no muestra el contenedor

**Causa:** El contenedor no está corriendo.

**Solución:**
```bash
# Ver todos los contenedores (incluso los detenidos)
docker ps -a

# Iniciar el contenedor
docker start europa-scraper-prod

# O usar docker-compose
docker-compose up -d
```

### Problema: "curl http://localhost:8001/ping" no responde

**Causa:** El servidor dentro del contenedor no está iniciado.

**Solución:**
1. Verifica los logs del contenedor:
   ```bash
   docker logs europa-scraper-prod
   ```
2. Si hay errores, reinicia el contenedor:
   ```bash
   docker restart europa-scraper-prod
   ```

### Problema: "cloudflared: command not found"

**Causa:** cloudflared no está instalado en el servidor01.

**Solución:**
```bash
# Descargar e instalar cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared
```

### Problema: Cloudflared no genera URL

**Causa:** Sin conexión a internet o puerto bloqueado.

**Solución:**
1. Verifica conexión a internet:
   ```bash
   ping google.com
   ```
2. Verifica que el puerto 8001 está accesible:
   ```bash
   curl http://localhost:8001/ping
   ```

### Problema: La URL no funciona en mi navegador

**Causa:** Cloudflared no está corriendo o se detuvo.

**Solución:**
1. Verifica que cloudflared sigue corriendo (no cierres la terminal)
2. Si se detuvo, reinícialo:
   ```bash
   cloudflared tunnel --url http://localhost:8001
   ```

### Problema: No aparecen archivos en el visor

**Causa:** No se han generado archivos CSV aún.

**Solución:**
1. Verifica que hay archivos en la carpeta results:
   ```bash
   ls -la results/
   ```
2. Ejecuta un trabajo de scraping desde el frontend
3. Espera a que se generen los archivos

---

## Notas Importantes

1. **El contenedor Docker debe estar corriendo** (`docker ps` debe mostrarlo)
2. **No cierres la terminal de cloudflared** mientras quieras acceder a los resultados
3. **La URL cambia** cada vez que reinicias cloudflared
4. **Los archivos CSV se guardan en el host** en la carpeta `results/` (mapeada desde el contenedor)
5. **Solo necesitas cloudflared en el servidor01**, no en tu PC local

---

## ¿Necesitas Ayuda?

Si tienes problemas, verifica:
1. ¿Estás conectado al servidor01?
2. ¿El contenedor Docker está corriendo (`docker ps`)?
3. ¿El servidor responde (`curl http://localhost:8001/ping`)?
4. ¿Cloudflared está corriendo?
5. ¿Copiaste la URL correctamente?
6. ¿Agregaste `/viewer` al final de la URL?
