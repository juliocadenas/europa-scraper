# Cómo Iniciar el Sistema Europa Scraper Corregido

## 🎯 Resumen Rápido

El sistema ha sido corregido para solucionar el problema donde el servidor respondía correctamente pero el cliente lo interpretaba como error.

## 🚀 Inicio Rápido (Recomendado)

### Opción 1: Inicio Automático Completo
```bash
python iniciar_gui_con_servidor_corregido.py
```
Este script:
1. Verifica si el servidor corregido está corriendo
2. Si no está, lo inicia automáticamente
3. Inicia la GUI conectada al servidor corregido

### Opción 2: Inicio Manual por Pasos

#### Paso 1: Iniciar el Servidor Corregido
```bash
python iniciar_servidor_corregido.py
```

#### Paso 2: Iniciar la GUI (en otra terminal)
```bash
python gui/scraper_gui.py
```

## 🔧 Componentes del Sistema

### Servidor Corregido
- **Archivo**: `server/main_wsl_corregido.py`
- **Puerto**: 8001
- **Endpoint de ping**: `http://localhost:8001/ping`
- **Endpoint de scraping**: `http://localhost:8001/start_scraping`

### GUI del Scraper
- **Archivo**: `gui/scraper_gui.py`
- **Configuración automática**: Se conecta a `http://localhost:8001`

## ✅ Verificación del Sistema

### Probar Conexión Básica
```bash
python probar_servidor_actual.py
```

### Probar Endpoints Manualmente
```bash
# Ping al servidor
curl http://localhost:8001/ping

# Probar scraping
curl -X POST http://localhost:8001/start_scraping \
  -H "Content-Type: application/json" \
  -d '{"job_params": {"from_sic": "600", "to_sic": "604", "search_engine": "DuckDuckGo"}}'
```

## 🐛 Solución de Problemas Comunes

### Problema: "El servidor ya está corriendo"
**Solución**: El script `iniciar_servidor_corregido.py` detecta y limpia automáticamente procesos en el puerto 8001.

### Problema: "La GUI no se conecta"
**Solución**: 
1. Asegúrate que el servidor esté corriendo en el puerto 8001
2. En la GUI, ve a la pestaña "Configuración del Servidor"
3. Verifica que la URL sea `http://localhost:8001`
4. Haz clic en "Conectar"

### Problema: "Error de dependencias"
**Solución**: 
```bash
pip install psutil fastapi uvicorn requests
```

### Problema: "Puerto en uso"
**Solución**: El script automáticamente libera el puerto, pero si falla:
```bash
# En Windows
netstat -ano | findstr :8001
taskkill /F /PID <PID_DEL_PROCESO>

# En Linux/Mac
lsof -i :8001
kill -9 <PID_DEL_PROCESO>
```

## 📁 Estructura de Archivos Importantes

```
├── iniciar_gui_con_servidor_corregido.py    # Inicio automático completo
├── iniciar_servidor_corregido.py          # Script de inicio del servidor
├── probar_servidor_actual.py              # Script de prueba
├── server/
│   └── main_wsl_corregido.py           # Servidor corregido
├── gui/
│   └── scraper_gui.py                  # Interfaz gráfica
└── results/                             # Resultados del scraping
```

## 🔄 Flujo de Trabajo

1. **Inicio**: Ejecuta `python iniciar_gui_con_servidor_corregido.py`
2. **Conexión**: La GUI se conecta automáticamente al servidor
3. **Carga de cursos**: Los cursos se cargan desde la base de datos del servidor
4. **Scraping**: Selecciona rangos y haz clic en "Iniciar Scraping"
5. **Resultados**: Los archivos CSV se guardan en `results/`

## 🎉 ¿Qué se solucionó?

### Problema Original
- El servidor respondía: `"Scraping corregido completado. Se generaron 5 resultados"`
- Pero con código HTTP 200 en lugar de 202
- La GUI esperaba código 202 para considerar la respuesta exitosa
- Resultado: La GUI mostraba "❌ Error" aunque el scraping funcionaba

### Solución Aplicada
- Modificado `server/main_wsl_corregido.py` para devolver código 202
- Actualizada la respuesta para usar `JSONResponse(status_code=202, ...)`
- Ahora la GUI recibe código 202 y muestra "✅ Éxito"

## 📞 Soporte

Si encuentras problemas:
1. Revisa este documento
2. Ejecuta `python probar_servidor_actual.py` para diagnóstico
3. Verifica los logs del servidor en la terminal

---
**Estado del Sistema**: ✅ Funcionando correctamente
**Última Actualización**: 25/11/2025
**Versión**: v3.1-LINUX Corregida