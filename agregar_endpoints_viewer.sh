#!/bin/bash
# Script para agregar los nuevos endpoints de visualización al contenedor Docker
# Este script copia los métodos necesarios dentro del contenedor

echo "Agregando endpoints de visualización al contenedor Docker..."

# Primero, verificar que el contenedor está corriendo
CONTAINER_ID=$(docker ps -q -f name=europa-scraper-prod)

if [ -z "$CONTAINER_ID" ]; then
    echo "ERROR: El contenedor europa-scraper-prod no está corriendo"
    echo "Inícialo con: docker-compose up -d"
    exit 1
fi

echo "Contenedor encontrado: $CONTAINER_ID"

# Crear un script Python con los nuevos métodos
cat > /tmp/add_viewer_endpoints.py << 'PYEOF'
import re

# Leer el archivo server.py
with open('/app/server/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Verificar si ya se agregaron los endpoints
if '/api/list_results' in content:
    print("Los endpoints ya están agregados. No se necesitan cambios.")
    exit(0)

# 1. Agregar importaciones si no existen
if 'from fastapi import FastAPI, HTTPException, UploadFile, File' in content:
    content = content.replace(
        'from fastapi import FastAPI, HTTPException, UploadFile, File',
        'from fastapi import FastAPI, HTTPException, UploadFile, File, Query'
    )
if 'from fastapi.responses import FileResponse' in content:
    content = content.replace(
        'from fastapi.responses import FileResponse',
        'from fastapi.responses import FileResponse, HTMLResponse'
    )
if 'import shutil' not in content:
    content = content.replace(
        'import threading',
        'import threading\nimport shutil'
    )

# 2. Encontrar el método cleanup_files_endpoint y agregar los nuevos métodos después
cleanup_pattern = r'(    async def cleanup_files_endpoint\(self\):.*?raise HTTPException\(status_code=500, detail=f"Error limpiando archivos: \{str\(e\)\}"\n)'

new_methods = r'''\1

    async def list_results_files(self):
        """Lista todos los archivos CSV en la carpeta results con información detallada."""
        try:
            results_dir = os.path.join(project_root, 'results')
            if not os.path.exists(results_dir):
                return {"files": [], "message": "La carpeta results no existe aún."}
            
            files_info = []
            for filename in os.listdir(results_dir):
                if filename.endswith('.csv'):
                    filepath = os.path.join(results_dir, filename)
                    stat = os.stat(filepath)
                    files_info.append({
                        "name": filename,
                        "size": stat.st_size,
                        "size_human": self._human_readable_size(stat.st_size),
                        "modified": stat.st_mtime,
                        "modified_human": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
                    })
            
            # Ordenar por fecha de modificación (más reciente primero)
            files_info.sort(key=lambda x: x['modified'], reverse=True)
            
            return {
                "files": files_info,
                "total": len(files_info),
                "results_dir": results_dir
            }
        except Exception as e:
            self.logger.error(f"Error listando archivos: {e}")
            raise HTTPException(status_code=500, detail=f"Error listando archivos: {str(e)}")

    async def download_single_file(self, filename: str):
        """Descarga un archivo individual de la carpeta results."""
        try:
            results_dir = os.path.join(project_root, 'results')
            filepath = os.path.join(results_dir, filename)
            
            if not os.path.exists(filepath):
                raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {filename}")
            
            return FileResponse(filepath, filename=filename, media_type='text/csv')
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error descargando archivo {filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Error descargando archivo: {str(e)}")

    async def preview_csv(self, filename: str, rows: int = 10):
        """Muestra una vista previa de un archivo CSV (primeras N filas)."""
        try:
            results_dir = os.path.join(project_root, 'results')
            filepath = os.path.join(results_dir, filename)
            
            if not os.path.exists(filepath):
                raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {filename}")
            
            # Leer el CSV
            df = pd.read_csv(filepath, nrows=int(rows))
            
            # Convertir a HTML para visualización
            html_table = df.to_html(classes='table table-striped table-hover', index=False)
            
            # Obtener información del archivo
            stat = os.stat(filepath)
            total_rows = sum(1 for _ in open(filepath)) - 1  # -1 por el encabezado
            
            return {
                "filename": filename,
                "preview_html": html_table,
                "preview_rows": int(rows),
                "total_rows": total_rows,
                "columns": list(df.columns),
                "size_human": self._human_readable_size(stat.st_size)
            }
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error generando preview de {filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Error generando preview: {str(e)}")

    async def results_viewer_html(self):
        """Retorna una página HTML simple para visualizar los resultados con auto-refresh."""
        html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Europa Scraper - Resultados</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; background-color: #f5f5f5; }
        .card { margin-bottom: 20px; }
        .file-row { cursor: pointer; transition: background-color 0.2s; }
        .file-row:hover { background-color: #e9ecef; }
        .preview-container { max-height: 500px; overflow-y: auto; }
        .refresh-badge { position: fixed; bottom: 20px; right: 20px; }
        #previewModal .modal-dialog { max-width: 90vw; }
        #previewModal .modal-body { padding: 0; }
        .table-responsive { margin: 0; }
        table { font-size: 0.9em; }
        th { background-color: #0d6efd; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h4 class="mb-0">📊 Archivos de Resultados</h4>
                        <div>
                            <span class="badge bg-success" id="lastUpdate">Actualizado: --:--:--</span>
                            <button class="btn btn-sm btn-primary ms-2" onclick="loadFiles()">
                                🔄 Actualizar
                            </button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col-md-4">
                                <label>Auto-refresh:</label>
                                <select id="refreshInterval" class="form-select form-select-sm" onchange="setRefreshInterval()">
                                    <option value="0">Desactivado</option>
                                    <option value="5000">5 segundos</option>
                                    <option value="10000" selected>10 segundos</option>
                                    <option value="30000">30 segundos</option>
                                    <option value="60000">1 minuto</option>
                                </select>
                            </div>
                            <div class="col-md-8 text-end">
                                <span class="badge bg-info" id="fileCount">0 archivos</span>
                            </div>
                        </div>
                        <div class="table-responsive">
                            <table class="table table-sm table-hover">
                                <thead>
                                    <tr>
                                        <th>Nombre</th>
                                        <th>Tamaño</th>
                                        <th>Modificado</th>
                                        <th>Acciones</th>
                                    </tr>
                                </thead>
                                <tbody id="filesTableBody">
                                    <tr><td colspan="4" class="text-center">Cargando...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Preview Modal -->
    <div class="modal fade" id="previewModal" tabindex="-1">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="previewTitle">Vista Previa</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body preview-container" id="previewBody">
                    <div class="text-center p-4">Cargando vista previa...</div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                    <button type="button" class="btn btn-primary" id="downloadFromPreview">Descargar</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let refreshTimer = null;
        let currentPreviewFile = null;

        function loadFiles() {
            fetch('/api/list_results')
                .then(r => r.json())
                .then(data => {
                    const tbody = document.getElementById('filesTableBody');
                    const countBadge = document.getElementById('fileCount');
                    
                    if (data.files.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No hay archivos aún</td></tr>';
                        countBadge.textContent = '0 archivos';
                        return;
                    }
                    
                    tbody.innerHTML = data.files.map(f => `
                        <tr class="file-row">
                            <td><strong>${escapeHtml(f.name)}</strong></td>
                            <td>${f.size_human}</td>
                            <td>${f.modified_human}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-primary" onclick="previewFile('${escapeHtml(f.name)}')">👁️ Ver</button>
                                <button class="btn btn-sm btn-outline-success" onclick="downloadFile('${escapeHtml(f.name)}')">⬇️ Descargar</button>
                            </td>
                        </tr>
                    `).join('');
                    
                    countBadge.textContent = `${data.total} archivo${data.total !== 1 ? 's' : ''}`;
                    document.getElementById('lastUpdate').textContent = 'Actualizado: ' + new Date().toLocaleTimeString();
                })
                .catch(err => {
                    console.error('Error:', err);
                    document.getElementById('filesTableBody').innerHTML = 
                        '<tr><td colspan="4" class="text-center text-danger">Error cargando archivos</td></tr>';
                });
        }

        function previewFile(filename) {
            currentPreviewFile = filename;
            document.getElementById('previewTitle').textContent = 'Vista Previa: ' + filename;
            document.getElementById('previewBody').innerHTML = '<div class="text-center p-4"><div class="spinner-border"></div></div>';
            
            const modal = new bootstrap.Modal(document.getElementById('previewModal'));
            modal.show();
            
            fetch(`/api/preview_csv?filename=${encodeURIComponent(filename)}&rows=50`)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('previewBody').innerHTML = `
                        <div class="p-3">
                            <div class="mb-3">
                                <span class="badge bg-primary">${data.total_rows} filas totales</span>
                                <span class="badge bg-secondary">${data.size_human}</span>
                                <span class="badge bg-info">Mostrando primeras ${data.preview_rows} filas</span>
                            </div>
                            <div class="table-responsive">
                                ${data.preview_html}
                            </div>
                        </div>
                    `;
                })
                .catch(err => {
                    document.getElementById('previewBody').innerHTML = 
                        '<div class="text-center p-4 text-danger">Error cargando vista previa</div>';
                });
        }

        function downloadFile(filename) {
            window.location.href = `/api/download_file?filename=${encodeURIComponent(filename)}`;
        }

        document.getElementById('downloadFromPreview').addEventListener('click', () => {
            if (currentPreviewFile) {
                downloadFile(currentPreviewFile);
            }
        });

        function setRefreshInterval() {
            const interval = parseInt(document.getElementById('refreshInterval').value);
            if (refreshTimer) {
                clearInterval(refreshTimer);
                refreshTimer = null;
            }
            if (interval > 0) {
                refreshTimer = setInterval(loadFiles, interval);
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Cargar archivos al inicio
        loadFiles();
        setRefreshInterval();
    </script>
</body>
</html>"""
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)

    def _human_readable_size(self, size_bytes):
        """Convierte bytes a formato legible."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
'''

content = re.sub(cleanup_pattern, new_methods, content, flags=re.DOTALL)

# 3. Encontrar _setup_routes y agregar los nuevos endpoints
routes_pattern = r"(    def _setup_routes\(self\):.*?self\.app\.get\(\"/ping\"\)\(self\.ping_endpoint\)\n)"

new_routes = r'''\1
        # Nuevos endpoints para visualización de resultados
        self.app.get("/api/list_results")(self.list_results_files)
        self.app.get("/api/download_file")(self.download_single_file)
        self.app.get("/api/preview_csv")(self.preview_csv)
        self.app.get("/viewer")(self.results_viewer_html)
'''

content = re.sub(routes_pattern, new_routes, content, flags=re.DOTALL)

# Guardar el archivo modificado
with open('/app/server/server.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Endpoints agregados exitosamente")
print("Reiniciando el contenedor para aplicar los cambios...")
PYEOF

# Copiar el script al contenedor y ejecutarlo
docker cp /tmp/add_viewer_endpoints.py europa-scraper-prod:/app/

echo "Ejecutando script dentro del contenedor..."
docker exec europa-scraper-prod python /app/add_viewer_endpoints.py

# Reiniciar el contenedor para aplicar los cambios
echo "Reiniciando el contenedor..."
docker restart europa-scraper-prod

# Esperar a que el contenedor se inicie
echo "Esperando a que el contenedor se inicie..."
sleep 10

# Verificar que el servidor responde
echo "Verificando que el servidor responde..."
curl -s http://localhost:8001/ping

echo ""
echo "Verificando el endpoint /viewer..."
curl -s http://localhost:8001/viewer | head -20

echo ""
echo "✓ Proceso completado"
echo ""
echo "Ahora puedes acceder al visor en:"
echo "  https://$(grep -oP 'https://[a-zA-Z0-9\-]+\.trycloudflare\.com' ~/cloudflared_logs/*.log 2>/dev/null | tail -1)/viewer"
