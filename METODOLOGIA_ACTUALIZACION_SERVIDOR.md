# METODOLOGÍA DE ACTUALIZACIÓN DEL SERVIDOR

## FLUJO DE TRABAJO

1. **Desarrollador**: Hace cambios → Commit → Push al repo
2. **Usuario**: Ejecuta comandos en el servidor

---

## COMANDOS EN EL SERVIDOR (siempre en este orden):

```bash
cd /opt/docuscraper
git pull
docker restart europa-scraper-prod
```

---

## SI HAY ERROR DE PERMISOS EN GIT:

```bash
cd /opt/docuscraper
sudo chown -R $USER:$USER .git
git pull
docker restart europa-scraper-prod
```

---

## DATOS IMPORTANTES:

| Item | Valor |
|------|-------|
| Directorio proyecto | `/opt/docuscraper` |
| Contenedor Docker | `europa-scraper-prod` |
| Puerto servidor | 8001 |
| Branch Git | `patch-monitor` |

---

## VERIFICACIÓN DESPUÉS DE ACTUALIZAR:

```bash
# Ver logs
docker logs --tail 20 europa-scraper-prod

# Verificar cambio en archivo
docker exec europa-scraper-prod grep "TEXTO_BUSCADO" /app/controllers/scraper_controller.py
```

---

## LIMPIAR CACHE SI HAY PROBLEMAS:

```bash
docker exec -it europa-scraper-prod rm -rf /app/__pycache__ /app/controllers/__pycache__ /app/utils/__pycache__
```
