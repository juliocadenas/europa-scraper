# Guía Paso a Paso: Visualización de Resultados con Cloudflared (Servidor Remoto)

## Tu Situación
- **Frontend**: Corre en tu máquina local (Windows)
- **Servidor**: Corre en el servidor01 (remoto)
- **Objetivo**: Ver los archivos CSV generados en el servidor01 desde tu navegador local

---

## Paso 1: Conectarte al Servidor Remoto

### Opción A: Usar SSH (si tienes acceso)

Abre PowerShell o CMD y ejecuta:

```bash
ssh usuario@servidor01
```

Reemplaza `usuario` con tu nombre de usuario en el servidor01.

### Opción B: Usar WSL (si está configurado)

Si ya tienes WSL configurado para conectarte al servidor01:

```bash
wsl
```

---

## Paso 2: Navegar al Directorio del Proyecto

Una vez conectado al servidor01, navega al directorio del proyecto:

```bash
cd /ruta/a/tu/proyecto/EUROPA/V3.1-LINUX
```

*Nota: La ruta puede variar según donde esté instalado el proyecto en el servidor01.*

---

## Paso 3: Verificar que el Servidor Principal Está Corriendo

El servidor principal debe estar corriendo en el puerto 8001. Verifica:

```bash
curl http://localhost:8001/ping
```

Si el servidor está corriendo, deberías ver:
```
EUROPA_SCRAPER_SERVER_PONG
```

### Si el servidor NO está corriendo:

Inícialo con:

```bash
python server/main.py
```

*Importante: Deja este comando corriendo en una terminal. No lo cierres.*

---

## Paso 4: Iniciar Cloudflared Tunnel (En el Servidor01)

Abre una NUEVA terminal conectada al servidor01 (mientras el servidor principal sigue corriendo en la primera terminal).

### En el servidor01 (Linux):

```bash
cd /ruta/a/tu/proyecto/EUROPA/V3.1-LINUX
chmod +x iniciar_cloudflared.sh
./iniciar_cloudflared.sh
```

### Si estás en WSL:

```bash
cd /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX
./iniciar_cloudflared.sh
```

---

## Paso 5: Copiar la URL Generada

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
| 1 | `ssh usuario@servidor01` | Tu máquina local |
| 2 | `cd /ruta/a/proyecto` | Servidor01 |
| 3 | `python server/main.py` | Servidor01 (Terminal 1) |
| 4 | `./iniciar_cloudflared.sh` | Servidor01 (Terminal 2) |
| 5 | Copiar URL | Servidor01 (Terminal 2) |
| 6 | Abrir URL en navegador | Tu máquina local |

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
│  (Remoto)       │
└────────┬────────┘
         │
         │ 2. Iniciar servidor (Terminal 1)
         │    python server/main.py
         │
         │ 3. Iniciar cloudflared (Terminal 2)
         │    ./iniciar_cloudflared.sh
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

## Solución de Problemas

### Problema: "El servidor no está corriendo en el puerto 8001"

**Causa:** El servidor principal no está iniciado.

**Solución:**
1. Inicia el servidor principal en una terminal:
   ```bash
   python server/main.py
   ```
2. Verifica que esté corriendo:
   ```bash
   curl http://localhost:8001/ping
   ```

### Problema: No puedo conectarme al servidor01 con SSH

**Causa:** No tienes acceso SSH configurado.

**Solución:**
1. Verifica que tienes las credenciales correctas
2. Si usas WSL, verifica que está configurado correctamente
3. Contacta al administrador del servidor01

### Problema: Cloudflared no genera URL

**Causa:** Sin conexión a internet o cloudflared no tiene permisos.

**Solución:**
1. Verifica conexión a internet en el servidor01:
   ```bash
   ping google.com
   ```
2. Asegúrate de que cloudflared tiene permisos de ejecución:
   ```bash
   chmod +x cloudflared
   ```

### Problema: La URL no funciona en mi navegador

**Causa:** Cloudflared no está corriendo o se detuvo.

**Solución:**
1. Verifica que cloudflared sigue corriendo en la Terminal 2
2. Si se detuvo, reinícialo:
   ```bash
   ./iniciar_cloudflared.sh
   ```

### Problema: No aparecen archivos en el visor

**Causa:** No se han generado archivos CSV aún.

**Solución:**
1. Ejecuta un trabajo de scraping desde el frontend
2. Verifica que los archivos se crearon en el servidor:
   ```bash
   ls -la server/results/
   ```

---

## Notas Importantes

1. **No cierres las terminales** mientras quieras acceder a los resultados
2. **La URL cambia** cada vez que reinicias cloudflared
3. **El túnel es gratuito** pero requiere conexión a internet
4. **Solo necesitas cloudflared en el servidor01**, no en tu PC local

---

## ¿Necesitas Ayuda?

Si tienes problemas, verifica:
1. ¿Estás conectado al servidor01?
2. ¿El servidor principal está corriendo (Terminal 1)?
3. ¿Cloudflared está corriendo (Terminal 2)?
4. ¿Copiaste la URL correctamente?
5. ¿Agregaste `/viewer` al final de la URL?
