# ============================================================
# COMANDOS PARA ACTUALIZAR TODO EL SERVIDOR
# ============================================================
# Ejecutar estos comandos en el shell de Proxmox
# ============================================================

# 1. Entrar al directorio
cd /opt/docuscraper

# 2. Traer TODOS los cambios de GitHub
git pull origin patch-monitor

# 3. Verificar que result_manager.py tiene el filtrado
grep -n "filtered_result = {}" utils/scraper/result_manager.py

# 4. Copiar TODOS los archivos actualizados al contenedor
docker cp utils/scraper/result_manager.py europa-scraper-prod:/app/utils/scraper/
docker cp controllers/scraper_controller.py europa-scraper-prod:/app/controllers/
docker cp server/server.py europa-scraper-prod:/app/server/

# 5. Verificar que el filtrado está dentro del contenedor
docker exec europa-scraper-prod grep -n "filtered_result = {}" /app/utils/scraper/result_manager.py

# 6. Reiniciar el contenedor
docker restart europa-scraper-prod

# 7. Verificar que inició
sleep 15
docker logs --tail 10 europa-scraper-prod

# ============================================================
# VERIFICACIÓN ESPERADA:
# - El paso 3 y 5 deben mostrar: "183:            filtered_result = {}"
# - Esto confirma que el filtrado de columnas está activo
# - El CSV resultante tendrá SOLO 7 columnas
# ============================================================
