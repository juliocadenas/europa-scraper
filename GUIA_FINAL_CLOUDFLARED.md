# Guía Final: Visualización de Resultados con Cloudflared (Paso a Paso)

## Situación
- **Frontend**: Tu PC local (Windows)
- **Servidor**: Docker en servidor01 (remoto)
- **Objetivo**: Ver archivos CSV desde tu navegador

---

## PASO 1: Desde tu PC local (PowerShell)

Los scripts están en tu PC local en:
```
C:\Users\julio\Documents\DOCUPLAY\Proyecto\Python\EUROPA\V3.1-LINUX
```

### Sube los scripts al servidor:

Abre PowerShell en tu PC local y ejecuta:

```powershell
cd C:\Users\julio\Documents\DOCUPLAY\Proyecto\Python\EUROPA\V3.1-LINUX
scp iniciar_cloudflared_docker.sh detener_cloudflared.sh julio@servidor01:~/
```

Te pedirá contraseña de julio en servidor01.

---

## PASO 2: Desde el servidor01 (SSH)

Conéctate al servidor:

```bash
ssh julio@servidor01
```

### Dar permisos de ejecución:

```bash
chmod +x ~/iniciar_cloudflared_docker.sh
chmod +x ~/detener_cloudflared.sh
```

### Iniciar cloudflared:

```bash
~/iniciar_cloudflared_docker.sh
```

Verás algo como:

```
========================================
  Cloudflared Tunnel - Docker Mode
========================================

Verificando que el servidor está corriendo...
✓ Servidor detectado y funcionando

Iniciando cloudflared en segundo plano...
Logs se guardarán en: /home/julio/cloudflared_logs/cloudflared_20260217_184500.log

✓ Cloudflared iniciado correctamente (PID: 12345)

========================================
  URL GENERADA
========================================

URL del túnel:
  https://xxx-xxx-xxx.trycloudflare.com

URL del visor de resultados:
  https://xxx-xxx-xxx.trycloudflare.com/viewer

========================================

Comandos útiles:
  Ver logs:  tail -f /home/julio/cloudflared_logs/cloudflared_20260217_184500.log
  Detener:   ~/detener_cloudflared.sh
  Ver PID:   cat /home/julio/cloudflared_logs/cloudflared.pid
```

---

## PASO 3: Desde tu navegador local (PC)

Copia la URL que te mostró el script y ábrela en tu navegador:

```
https://xxx-xxx-xxx.trycloudflare.com/viewer
```

¡Listo! Deberías ver el visor de resultados.

---

## RESUMEN DE COMANDOS

### Desde tu PC local (PowerShell):
```powershell
cd C:\Users\julio\Documents\DOCUPLAY\Proyecto\Python\EUROPA\V3.1-LINUX
scp iniciar_cloudflared_docker.sh detener_cloudflared.sh julio@servidor01:~/
```

### Desde el servidor01:
```bash
ssh julio@servidor01
chmod +x ~/iniciar_cloudflared_docker.sh ~/detener_cloudflared.sh
~/iniciar_cloudflared_docker.sh
```

### Para detener cloudflared (en servidor01):
```bash
~/detener_cloudflared.sh
```

### Para ver logs (en servidor01):
```bash
tail -f ~/cloudflared_logs/cloudflared_*.log
```

---

## DIAGRAMA

```
┌─────────────────────────────────────┐
│  Tu PC Local (Windows)            │
│  PowerShell                        │
│                                   │
│  1. scp scripts -> servidor01      │
└──────────────┬────────────────────┘
               │
               │ SSH
               ▼
┌─────────────────────────────────────┐
│  Servidor01                       │
│  Terminal SSH                     │
│                                   │
│  2. chmod +x scripts             │
│  3. ~/iniciar_cloudflared_docker.sh│
│                                   │
│  ┌─────────────────────────────┐  │
│  │  Docker Container          │  │
│  │  europa-scraper-prod       │  │
│  │  Puerto: 8001             │  │
│  └──────────────┬──────────────┘  │
│                 │                   │
│  ┌──────────────▼──────────────┐  │
│  │  Cloudflared (segundo plano) │  │
│  │  URL: https://xxx.try...   │  │
│  └──────────────┬──────────────┘  │
└─────────────────┼──────────────────┘
                  │
                  │ HTTPS
                  ▼
┌─────────────────────────────────────┐
│  Tu Navegador Local              │
│  https://xxx.trycloudflare.com/   │
│  viewer                          │
└─────────────────────────────────────┘
```

---

## SOLUCIÓN DE PROBLEMAS

### Problema: "scp: No such file or directory"

**Causa:** Estás ejecutando scp desde el servidor01, no desde tu PC local.

**Solución:**
1. Abre PowerShell en tu PC local (NO en SSH)
2. Navega al directorio del proyecto
3. Ejecuta el comando scp

### Problema: "permission denied while trying to connect to docker API"

**Causa:** Tu usuario no tiene acceso directo a Docker.

**Solución:** No es un problema. El contenedor sigue corriendo. Solo verifica:
```bash
curl http://localhost:8001/ping
```

### Problema: "ERR_TUNNEL_CONNECTION_FAILED" en el navegador

**Causa:** Cloudflared no está corriendo o se detuvo.

**Solución:**
1. Conéctate al servidor01
2. Verifica si cloudflared está corriendo:
   ```bash
   ps aux | grep cloudflared
   ```
3. Si no está corriendo, inícialo:
   ```bash
   ~/iniciar_cloudflared_docker.sh
   ```

### Problema: La URL no funciona

**Causa:** La URL cambió o cloudflared se reinició.

**Solución:**
1. Revisa el log más reciente:
   ```bash
   ls -lt ~/cloudflared_logs/ | head -1
   tail ~/cloudflared_logs/cloudflared_*.log | grep "trycloudflare.com"
   ```
2. Copia la nueva URL del log

---

## NOTAS IMPORTANTES

1. **Ejecuta scp desde tu PC local**, no desde el servidor01
2. **Cloudflared corre en segundo plano**, puedes cerrar la terminal SSH
3. **La URL cambia** cada vez que reinicias cloudflared
4. **Los logs se guardan** en `~/cloudflared_logs/` con timestamp
5. **Solo necesitas iniciar cloudflared una vez**, seguirá corriendo hasta que lo detengas

---

## COMANDOS RÁPIDOS DE REFERENCIA

| Acción | Comando (en servidor01) |
|--------|-------------------------|
| Iniciar cloudflared | `~/iniciar_cloudflared_docker.sh` |
| Detener cloudflared | `~/detener_cloudflared.sh` |
| Ver logs en vivo | `tail -f ~/cloudflared_logs/cloudflared_*.log` |
| Ver si está corriendo | `ps aux \| grep cloudflared` |
| Ver PID | `cat ~/cloudflared_logs/cloudflared.pid` |
| Verificar servidor | `curl http://localhost:8001/ping` |
| Ver contenedores Docker | `docker ps` |
