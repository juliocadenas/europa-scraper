# Solución Alternativa: Visor de Resultados sin Modificar Docker

## Situación
- Tu usuario `julio` no tiene permisos de Docker
- No se pueden agregar los endpoints al contenedor
- Necesitas una solución alternativa

## Solución: Servidor HTTP Independiente

Vamos a crear un servidor HTTP simple en el host del servidor01 (fuera de Docker) que sirva los archivos de la carpeta `results/`.

---

## PASO 1: Crear el servidor HTTP independiente

Copia y pega este comando en el servidor01:

```bash
cat > ~/results_viewer_server.py << 'PYEOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import pandas as pd
from urllib.parse import parse_qs, urlparse

RESULTS_DIR = "/home/julio/europa/results"

class ResultsHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/' or path == '':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.get_index_html().encode('utf-8'))
        elif path == '/api/list':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(self.list_files()).encode('utf-8'))
        elif path.startswith('/api/download'):
            filename = parse_qs(parsed_path.query).get('filename', [''])[0]
            self.download_file(filename)
        elif path.startswith('/api/preview'):
            filename = parse_qs(parsed_path.query).get('filename', [''])[0]
            rows = int(parse_qs(parsed_path.query).get('rows', ['10'])[0])
            self.preview_file(filename, rows)
        else:
            super().do_GET()
    
    def list_files(self):
        if not os.path.exists(RESULTS_DIR):
            return {"files": [], "message": "La carpeta results no existe aun."}
        
        files_info = []
        for filename in os.listdir(RESULTS_DIR):
            if filename.endswith('.csv'):
                filepath = os.path.join(RESULTS_DIR, filename)
                stat = os.stat(filepath)
                files_info.append({
                    "name": filename,
                    "size": stat.st_size,
                    "size_human": self.human_readable_size(stat.st_size),
                    "modified": stat.st_mtime,
                    "modified_human": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
                })
        
        files_info.sort(key=lambda x: x['modified'], reverse=True)
        return {"files": files_info, "total": len(files_info)}
    
    def download_file(self, filename):
        filepath = os.path.join(RESULTS_DIR, filename)
        if not os.path.exists(filepath):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Archivo no encontrado')
            return
        
        self.send_response(200)
        self.send_header('Content-type', 'text/csv')
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        with open(filepath, 'rb') as f:
            self.wfile.write(f.read())
    
    def preview_file(self, filename, rows):
        filepath = os.path.join(RESULTS_DIR, filename)
        if not os.path.exists(filepath):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Archivo no encontrado')
            return
        
        try:
            df = pd.read_csv(filepath, nrows=rows)
            html_table = df.to_html(classes='table table-striped table-hover', index=False)
            stat = os.stat(filepath)
            total_rows = sum(1 for _ in open(filepath)) - 1
            
            data = {
                "filename": filename,
                "preview_html": html_table,
                "preview_rows": rows,
                "total_rows": total_rows,
                "columns": list(df.columns),
                "size_human": self.human_readable_size(stat.st_size)
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f'Error: {str(e)}'.encode('utf-8'))
    
    def human_readable_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def get_index_html(self):
        return """<!DOCTYPE html>
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
                        <h4 class="mb-0">Archivos de Resultados</h4>
                        <div>
                            <span class="badge bg-success" id="lastUpdate">Actualizado: --:--:--</span>
                            <button class="btn btn-sm btn-primary ms-2" onclick="loadFiles()">Actualizar</button>
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
            fetch('/api/list')
                .then(r => r.json())
                .then(data => {
                    const tbody = document.getElementById('filesTableBody');
                    const countBadge = document.getElementById('fileCount');
                    
                    if (data.files.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No hay archivos aun</td></tr>';
                        countBadge.textContent = '0 archivos';
                        return;
                    }
                    
                    tbody.innerHTML = data.files.map(f => `
                        <tr class="file-row">
                            <td><strong>${escapeHtml(f.name)}</strong></td>
                            <td>${f.size_human}</td>
                            <td>${f.modified_human}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-primary" onclick="previewFile('${escapeHtml(f.name)}')">Ver</button>
                                <button class="btn btn-sm btn-outline-success" onclick="downloadFile('${escapeHtml(f.name)}')">Descargar</button>
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
            
            fetch(`/api/preview?filename=${encodeURIComponent(filename)}&rows=50`)
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
            window.location.href = `/api/download?filename=${encodeURIComponent(filename)}`;
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

        loadFiles();
        setRefreshInterval();
    </script>
</body>
</html>"""

if __name__ == '__main__':
    PORT = 8888
    server = HTTPServer(('0.0.0.0', PORT), ResultsHandler)
    print(f"Servidor de resultados iniciado en http://0.0.0.0:{PORT}")
    print(f"Sirviendo archivos de: {RESULTS_DIR}")
    server.serve_forever()
PYEOF

chmod +x ~/results_viewer_server.py
```

---

## PASO 2: Iniciar el servidor de resultados

```bash
nohup ~/results_viewer_server.py > ~/results_viewer.log 2>&1 &
```

---

## PASO 3: Iniciar cloudflared para el nuevo servidor

```bash
cloudflared tunnel --url http://localhost:8888 &
```

---

## PASO 4: Obtener la URL

Cloudflared generará una URL. Cópiala y agrégale `/` al final (o simplemente abre la URL raíz).

---

## Ventajas de esta solución

✅ **No requiere permisos de Docker**
✅ **No modifica el contenedor**
✅ **Funciona inmediatamente**
✅ **Puedes detenerlo e iniciarlo cuando quieras**
✅ **Los archivos se leen directamente del host**

---

## Comandos para detener

```bash
# Detener el servidor de resultados
pkill -f results_viewer_server.py

# Detener cloudflared
pkill cloudflared
```

---

## Comandos para reiniciar

```bash
# Iniciar servidor de resultados
nohup ~/results_viewer_server.py > ~/results_viewer.log 2>&1 &

# Iniciar cloudflared
cloudflared tunnel --url http://localhost:8888 &
```
