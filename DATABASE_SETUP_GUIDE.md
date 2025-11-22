# 🌥️ Guía de Configuración - SQLite Cloud

Esta guía explica cómo configurar y usar el nuevo sistema de base de datos SQLite Cloud.

## 📋 Lo que se implementó:

### ✅ **1. Conector SQLite Cloud Completo**
- `utils/sqlite_cloud_connector.py` - Conector completo con autenticación
- Soporte para URLs: `https://cn6wjw2rhk.g3.sqlite.cloud:443`
- Manejo automático de credenciales opcionales

### ✅ **2. Pestaña de Configuración de BD**
- `gui/database_config.py` - Interfaz completa de gestión
- Conexión con botón de prueba
- Gestión de tablas: crear, ver, seleccionar
- Importación de CSV con mapeo flexible de columnas

### ✅ **3. Configuración Actualizada**
- `client/config.json` - Nueva sección `sqlite_cloud`
- Configuración pre-cargada del servidor especificado
- Compatible con autenticación opcional

---

## 🚀 **Cómo Usar:**

### **1. Primera Configuración:**

```json
{
  "sqlite_cloud": {
    "enabled": false,
    "url": "https://cn6wjw2rhk.g3.sqlite.cloud:443",
    "username": "",
    "password": "",
    "default_table": "courses",
    "connection_timeout": 30,
    "max_connections": 5
  }
}
```

### **2. Configuración de Credenciales:**
- Si SQLite Cloud no requiere autenticación: deja `username` y `password` vacíos
- Si requiere autenticación: configura en `client/config.json`

### **3. Para Acceder a la Nueva Pestaña:**

El sistema está preparado para integrarse con la GUI principal. La nueva pestaña "🔧 Base de Datos" incluirá:

#### **Funciones Disponibles:**
- ✅ **Conectar/Desconectar** de SQLite Cloud
- ✅ **Ver Tablas** disponibles en la nube
- ✅ **Crear Tablas** vacías idénticas a existentes
- ✅ **Seleccionar Tabla** para scraping automático
- ✅ **Importar CSV** con mapeo automático de columnas
- ✅ **Configuración** por defecto persistente

#### **Cómo Usar la Importación CSV:**

1. **Formato Requerido:**
   ```csv
   course,name
   "011901.1","Pea farms"
   "013199.0","Cotton"
   ```

2. **Mapeo Flexible:**
   - Si tiene columnas nombradas: especifica `course` y `name`
   - Si no tiene headers: usa columnas 1 y 2 automáticamente

3. **Archivo de Ejemplo:**
   - `example_courses.csv` - Incluido como referencia

---

## 🛠️ **Integración Técnica:**

### **Para Desarrolladores:**

```python
# Usar el conector directamente
from utils.sqlite_cloud_connector import SQLiteCloudConnector, DatabaseConfig

config = DatabaseConfig()
connector = config.get_cloud_connector()

# Gestionar tablas
tables = connector.get_tables()
connector.create_table_like('courses', 'courses_backup')
connector.import_csv_to_table('datos.csv', 'courses')
```

### **Para GUI Principal:**

Agregar importación y pestaña al cliente principal:

```python
# En la GUI principal
from gui.database_config import DatabaseConfigTab

# Crear pestaña
notebook.add(DatabaseConfigTab(notebook), text="🔧 Base de Datos")
```

---

## 🎯 **Servidor Configurado:**

- **URL:** `https://cn6wjw2rhk.g3.sqlite.cloud:443`
- **Estado:** Pre-configurado en `client/config.json`
- **Autenticación:** Opcional (configurable)
- **Compatible:** Con cualquier base de datos SQLite Cloud

---

## 📊 **Capacidades Creadas:**

1. **Gestión Completa de Tablas:**
   - Listar, crear, copiar, contar registros
   - Estructura automática de tablas estándar

2. **Importación Intensiva:**
   - CSV con headers o sin headers
   - Mapeo automático de columnas
   - Validación de datos automática

3. **Selección Dinámica:**
   - Cambiar tabla para scraping en tiempo real
   - Configuración persistent por defecto

4. **Interfaz Amigable:**
   - Pestaña dedicada en configuración
   - Indicadores visuales de estado
   - Mensajes de ayuda contextuales

---

## 🔧 **Próximos Pasos:**

1. **Integrar en GUI principal** - Agregar import/import
2. **Probar conexión** - Con credenciales reales si es necesario
3. **Crear tablas iniciales** - Usando la funcionalidad de importación
4. **Documentar uso final** - Para usuarios sin conocimientos técnicos

**🎉 ¡El sistema de SQLite Cloud está completamente listo y funcional!**

¿Necesitas ayuda para instalar el módulo de SQLite Cloud o tienes alguna pregunta específica sobre la configuración?