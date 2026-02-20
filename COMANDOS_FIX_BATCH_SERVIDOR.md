# ============================================================
# COMANDOS PARA EJECUTAR EN EL SHELL DE PROXMOX
# ============================================================
# Error: "ScraperController.run_scraping() got an unexpected keyword argument 'batch'"
# Causa: El servidor tiene una versión antigua del scraper_controller.py
# Solución: Actualizar desde GitHub
# ============================================================

# PASO 1: Entrar al directorio del proyecto
cd /opt/docuscraper

# PASO 2: Verificar si hay actualizaciones en GitHub
git fetch origin

# PASO 3: Ver qué rama estamos usando
git branch

# PASO 4: Traer los últimos cambios
git pull origin patch-monitor
# (O si estás en main: git pull origin main)

# PASO 5: Verificar que el archivo se actualizó
grep -n "batch: Optional" controllers/scraper_controller.py
# DEBE mostrar la línea 909 con el parámetro batch

# PASO 6: Copiar el archivo actualizado al contenedor Docker
docker cp controllers/scraper_controller.py europa-scraper-prod:/app/controllers/

# PASO 7: Verificar que el archivo dentro del contenedor tiene el parámetro
docker exec europa-scraper-prod grep -n "batch: Optional" /app/controllers/scraper_controller.py

# PASO 8: Reiniciar el contenedor
docker restart europa-scraper-prod

# PASO 9: Esperar 15 segundos y verificar
sleep 15
docker ps | grep europa-scraper-prod
docker logs --tail 20 europa-scraper-prod

# ============================================================
# SI git pull NO FUNCIONA (permisos o conflictos)
# ============================================================

# Opción A: Forzar actualización
git fetch origin
git reset --hard origin/patch-monitor

# Opción B: Descargar directamente desde GitHub
# (Solo si git no funciona)
curl -L "https://raw.githubusercontent.com/juliocastillopro/europa-scraper/V3.1-LINUX/controllers/scraper_controller.py" -o controllers/scraper_controller.py

# Luego repetir pasos 6-8

# ============================================================
# VERIFICACIÓN FINAL
# ============================================================
# Después de reiniciar, intentar el scraping nuevamente
# El error "unexpected keyword argument 'batch'" debe desaparecer
