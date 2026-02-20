# INSTRUCCIONES FINALES PARA SOLUCIÓN DEFINITIVA WSL

## 🚨 PROBLEMA IDENTIFICADO

El error principal es que **Playwright no puede encontrar el ejecutable de Chromium** en WSL. Los mensajes clave son:

```
BrowserType.launch: Executable doesn't exist at /mnt/c/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/venv_wsl/lib/python3.12/site-packages/playwright/driver/package/.local-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell
```

Además, hay un error de importación: `name 'traceback' is not defined`

## 🛠️ SOLUCIÓN FINAL CORREGIDA

He creado el script [`SOLUCION_FINAL_WSL_CORREGIDA.sh`](SOLUCION_FINAL_WSL_CORREGIDA.sh) que:

### 1. Corrige el error de importación
```bash
sed -i 's/import traceback/import traceback as traceback_module/' fix_wsl_browser.py
sed -i 's/traceback.format_exc()/traceback_module.format_exc()/' fix_wsl_browser.py
```

### 2. Desinstala y reinstala Playwright completamente
```bash
./venv_wsl/bin/pip uninstall -y playwright playwright-stealth pyee greenlet
rm -rf ./venv_wsl/lib/python3.12/site-packages/playwright*
./venv_wsl/bin/pip install playwright==1.40.0
./venv_wsl/bin/playwright install chromium --force
```

### 3. Crea una prueba final corregida
- Importa `traceback` correctamente
- Usa argumentos WSL específicos
- Prueba la funcionalidad completa

### 4. Ofrece solución alternativa con Chromium del sistema
```bash
sudo apt-get install -y chromium-browser
export CHROME_BIN=/usr/bin/chromium-browser
```

## 🚀 CÓMO EJECUTAR LA SOLUCIÓN

### Paso 1: Ejecutar el script corregido
```bash
./SOLUCION_FINAL_WSL_CORREGIDA.sh
```

### Paso 2: Si el paso 1 falla, ejecutar manualmente
```bash
# 1. Corregir importación
sed -i 's/import traceback/import traceback as traceback_module/' fix_wsl_browser.py
sed -i 's/traceback.format_exc()/traceback_module.format_exc()/' fix_wsl_browser.py

# 2. Desinstalar playwright
./venv_wsl/bin/pip uninstall -y playwright playwright-stealth pyee greenlet

# 3. Limpiar instalación
rm -rf ./venv_wsl/lib/python3.12/site-packages/playwright*

# 4. Reinstalar
./venv_wsl/bin/pip install playwright==1.40.0
./venv_wsl/bin/playwright install chromium --force

# 5. Probar
python test_wsl_final.py
```

### Paso 3: Iniciar el servidor
```bash
./iniciar_servidor_wsl_definitivo.sh
```

## 🔍 VERIFICACIÓN

Después de ejecutar la solución, verifica:

### 1. Que Chromium esté instalado
```bash
ls -la ./venv_wsl/lib/python3.12/site-packages/playwright/driver/package/.local-browsers/chromium_headless_shell-*/
```

### 2. Que la prueba funcione
```bash
python test_wsl_final.py
# Debe mostrar: ✅ Prueba WSL final exitosa
```

### 3. Que el servidor inicie
```bash
./iniciar_servidor_wsl_definitivo.sh
# Debe iniciar sin errores de navegador
```

### 4. Que los workers creen logs
```bash
ls -la logs/worker_*.log
# Deben aparecer archivos de log
```

## 🎯 RESULTADO ESPERADO

✅ **El navegador Playwright se inicializará correctamente**
✅ **Los workers crearán sus archivos de log**
✅ **El servidor iniciará sin errores**
✅ **El scraping funcionará con Cordis Europa**
✅ **Los resultados se guardarán en results/**

## 🚨 SI PERSISTEN LOS PROBLEMAS

### Opción A: Usar Chromium del sistema
```bash
sudo apt-get install -y chromium-browser
export CHROME_BIN=/usr/bin/chromium-browser

# Modificar el script para usar Chromium del sistema
sed -i 's/playwright.chromium.launch/browser.launch(channel="chromium"/' fix_wsl_browser.py
```

### Opción B: Verificar permisos y rutas
```bash
# Verificar permisos del entorno virtual
ls -la venv_wsl/
chmod -R 755 venv_wsl/

# Verificar espacio en disco
df -h

# Verificar memoria
free -h
```

### Opción C: Debugging detallado
```bash
# Ejecutar con logging máximo
export PLAYWRIGHT_DEBUG=1
python test_wsl_final.py

# Revisar logs del sistema
journalctl -xe | grep -i chromium
dmesg | grep -i error
```

## 📊 ARCHIVOS CREADOS

1. **[`SOLUCION_FINAL_WSL_CORREGIDA.sh`](SOLUCION_FINAL_WSL_CORREGIDA.sh)** - Script principal corregido
2. **[`test_wsl_final.py`](test_wsl_final.py)** - Script de prueba final (creado automáticamente)
3. **[`fix_wsl_browser.py`](fix_wsl_browser.py)** - BrowserManager corregido
4. **[`iniciar_servidor_wsl_definitivo.sh`](iniciar_servidor_wsl_definitivo.sh)** - Script de inicio mejorado

## 🎉 CONCLUSIÓN

Esta solución aborda definitivamente:

1. ✅ **Error de importación traceback** - Corregido
2. ✅ **Instalación incompleta de Playwright** - Desinstalación y reinstalación completa
3. ✅ **Ejecutable de Chromium faltante** - Instalación forzada con --force
4. ✅ **Configuración WSL específica** - Argumentos y variables de entorno
5. ✅ **Solución alternativa** - Chromium del sistema como fallback

El sistema de scraping debería funcionar perfectamente en WSL después de aplicar esta solución final.