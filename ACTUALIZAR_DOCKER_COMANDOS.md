# Comandos para Reconstruir el Contenedor Docker

## Paso 1: Subir los archivos modificados al servidor01

Desde tu PC local (PowerShell), navega al directorio del proyecto y ejecuta:

```powershell
cd C:\Users\julio\Documents\DOCUPLAY\Proyecto\Python\EUROPA\V3.1-LINUX
scp server/server.py julio@servidor01:~/europa/
```

## Paso 2: En el servidor01, reconstruir el contenedor

Conéctate al servidor01:

```bash
ssh julio@servidor01
```

Navega al directorio del proyecto:

```bash
cd ~/europa
```

Detener y eliminar el contenedor actual:

```bash
docker-compose down
```

Reconstruir y iniciar el contenedor:

```bash
docker-compose up -d --build
```

Verificar que el contenedor está corriendo:

```bash
docker ps
```

Verificar que el servidor responde:

```bash
curl http://localhost:8001/ping
```

Deberías ver: `EUROPA_SCRAPER_SERVER_PONG`

## Paso 3: Verificar que los nuevos endpoints funcionan

Probar el endpoint del visor:

```bash
curl http://localhost:8001/viewer
```

Deberías ver código HTML.

## Paso 4: Reiniciar cloudflared (si es necesario)

Si cloudflared se detuvo, inícialo de nuevo:

```bash
~/iniciar_cloudflared_docker.sh
```

O simplemente:

```bash
cloudflared tunnel --url http://localhost:8001 &
```

## Paso 5: Acceder desde tu navegador

Abre en tu navegador:

```
https://receives-drives-absent-francis.trycloudflare.com/viewer
```

O la nueva URL que genere cloudflared.

---

## Resumen de Comandos

### Desde tu PC local:
```powershell
cd C:\Users\julio\Documents\DOCUPLAY\Proyecto\Python\EUROPA\V3.1-LINUX
scp server/server.py julio@servidor01:~/europa/
```

### Desde el servidor01:
```bash
ssh julio@servidor01
cd ~/europa
docker-compose down
docker-compose up -d --build
docker ps
curl http://localhost:8001/ping
curl http://localhost:8001/viewer
```

### Si cloudflared se detuvo:
```bash
cloudflared tunnel --url http://localhost:8001 &
```
