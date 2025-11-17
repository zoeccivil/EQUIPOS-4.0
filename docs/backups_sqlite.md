# Sistema de Backups SQLite en EQUIPOS 4.0

## Introducción

EQUIPOS 4.0 utiliza Firebase (Firestore) como fuente principal de datos, pero mantiene un sistema robusto de backups automáticos en SQLite. Este documento explica cómo funciona este sistema y cómo utilizarlo.

## Arquitectura del Sistema de Backups

### Propósito

Los backups SQLite cumplen varios propósitos:

1. **Respaldo de Seguridad**: Copia local de todos los datos en caso de problemas con Firebase
2. **Trabajo Offline**: Permite consultar datos cuando no hay conexión a internet
3. **Historial**: Mantiene snapshots de los datos en diferentes momentos
4. **Auditoría**: Facilita revisiones y comparaciones de datos históricos

### Componente Principal: BackupManager

El módulo `backup_manager.py` gestiona todo el sistema de backups.

```python
from backup_manager import BackupManager
from firebase_manager import FirebaseManager

# Inicializar
firebase_mgr = FirebaseManager('credentials.json', 'proyecto-id')
backup_mgr = BackupManager('./backups/equipos_backup.db', firebase_mgr)

# Crear backup
backup_mgr.crear_backup()
```

## Estructura de la Base de Datos de Backup

La base de datos SQLite replica la estructura de Firestore:

### Tablas

#### equipos
```sql
CREATE TABLE equipos (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    marca TEXT,
    modelo TEXT,
    categoria TEXT,
    placa TEXT,
    ficha TEXT,
    activo INTEGER DEFAULT 1,
    fecha_creacion TEXT,
    fecha_modificacion TEXT
)
```

#### transacciones
```sql
CREATE TABLE transacciones (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL CHECK(tipo IN ('Ingreso', 'Gasto')),
    equipo_id TEXT,
    cliente_id TEXT,
    operador_id TEXT,
    fecha TEXT NOT NULL,
    monto REAL NOT NULL,
    descripcion TEXT,
    comentario TEXT,
    horas REAL,
    precio_por_hora REAL,
    conduce TEXT,
    ubicacion TEXT,
    pagado INTEGER DEFAULT 0,
    categoria TEXT,
    subcategoria TEXT,
    fecha_creacion TEXT,
    fecha_modificacion TEXT
)
```

#### entidades
```sql
CREATE TABLE entidades (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK(tipo IN ('Cliente', 'Operador')),
    telefono TEXT,
    cedula TEXT,
    activo INTEGER DEFAULT 1,
    fecha_creacion TEXT,
    fecha_modificacion TEXT
)
```

#### mantenimientos
```sql
CREATE TABLE mantenimientos (
    id TEXT PRIMARY KEY,
    equipo_id TEXT NOT NULL,
    fecha TEXT,
    descripcion TEXT,
    tipo TEXT,
    costo REAL,
    odometro_horas REAL,
    odometro_km REAL,
    notas TEXT,
    proximo_tipo TEXT,
    proximo_valor REAL,
    proximo_fecha TEXT,
    fecha_creacion TEXT,
    fecha_modificacion TEXT
)
```

#### pagos_operadores
```sql
CREATE TABLE pagos_operadores (
    id TEXT PRIMARY KEY,
    operador_id TEXT NOT NULL,
    equipo_id TEXT,
    fecha TEXT NOT NULL,
    monto REAL NOT NULL,
    horas REAL,
    descripcion TEXT,
    comentario TEXT,
    fecha_creacion TEXT,
    fecha_modificacion TEXT
)
```

#### backup_metadata
```sql
CREATE TABLE backup_metadata (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    fecha_backup TEXT NOT NULL,
    version TEXT,
    registros_equipos INTEGER,
    registros_transacciones INTEGER,
    registros_entidades INTEGER,
    registros_mantenimientos INTEGER,
    registros_pagos_operadores INTEGER
)
```

### Índices

Para mejorar el rendimiento de las consultas:

```sql
CREATE INDEX idx_transacciones_fecha ON transacciones(fecha);
CREATE INDEX idx_transacciones_equipo ON transacciones(equipo_id);
CREATE INDEX idx_mantenimientos_equipo ON mantenimientos(equipo_id);
CREATE INDEX idx_pagos_operador ON pagos_operadores(operador_id);
```

## Configuración de Backups

La configuración se encuentra en `config_equipos.json`:

```json
{
  "backup": {
    "ruta_backup_sqlite": "D:/Backups/Equipos/equipos_backup.db",
    "frecuencia": "diario",
    "hora_ejecucion": "02:00",
    "ultimo_backup": null
  }
}
```

### Parámetros de Configuración

- **ruta_backup_sqlite**: Ruta completa donde se guardará el archivo de backup
  - Puede ser ruta relativa: `./backups/equipos_backup.db`
  - O ruta absoluta: `D:/Backups/Equipos/equipos_backup.db`
  
- **frecuencia**: Con qué frecuencia crear backups
  - Actualmente soportado: `"diario"`
  - Futuro: `"semanal"`, `"mensual"`
  
- **hora_ejecucion**: Hora del día para ejecutar backup automático
  - Formato: `"HH:MM"` (24 horas)
  - Ejemplo: `"02:00"` = 2:00 AM
  
- **ultimo_backup**: Timestamp del último backup realizado
  - Se actualiza automáticamente
  - Formato ISO 8601: `"2025-11-16T02:00:00"`

## Proceso de Backup Automático

### Cómo Funciona

1. **Al iniciar la aplicación**: El sistema verifica la configuración de backups

2. **Verificación Periódica**: Cada cierto tiempo (ej: cada hora), verifica si es momento de crear backup usando:
   ```python
   debe_crear = backup_manager.debe_crear_backup(
       frecuencia="diario",
       hora_ejecucion="02:00",
       ultimo_backup="2025-11-15T02:00:00"
   )
   ```

3. **Criterios para Crear Backup**:
   - Si nunca se ha creado un backup → crear inmediatamente
   - Si la frecuencia es "diario":
     - Ha pasado al menos 1 día desde el último backup
     - La hora actual está dentro de 1 hora de la hora programada
   
4. **Proceso de Backup**:
   ```
   ┌─────────────────────────┐
   │ Leer datos de Firebase  │
   └───────────┬─────────────┘
               │
               ▼
   ┌─────────────────────────┐
   │ Limpiar tablas SQLite   │
   └───────────┬─────────────┘
               │
               ▼
   ┌─────────────────────────┐
   │ Insertar datos actuales │
   └───────────┬─────────────┘
               │
               ▼
   ┌─────────────────────────┐
   │ Guardar metadata        │
   └───────────┬─────────────┘
               │
               ▼
   ┌─────────────────────────┐
   │ Actualizar config       │
   └─────────────────────────┘
   ```

5. **Actualización de Configuración**: Actualiza `ultimo_backup` en el JSON

### Implementación en la Aplicación

En `main_qt.py` (o donde corresponda):

```python
from PyQt6.QtCore import QTimer
from config_manager import cargar_configuracion, guardar_configuracion
from backup_manager import BackupManager
from datetime import datetime

class AplicacionPrincipal:
    def __init__(self):
        self.config = cargar_configuracion()
        self.firebase_manager = FirebaseManager(...)
        self.backup_manager = BackupManager(
            ruta_backup=self.config['backup']['ruta_backup_sqlite'],
            firebase_manager=self.firebase_manager
        )
        
        # Timer para verificar backups cada hora
        self.timer_backup = QTimer()
        self.timer_backup.timeout.connect(self.verificar_backup_automatico)
        self.timer_backup.start(3600000)  # 1 hora en milisegundos
        
        # Verificar al inicio
        self.verificar_backup_automatico()
    
    def verificar_backup_automatico(self):
        """Verifica si es momento de crear un backup."""
        debe_crear = self.backup_manager.debe_crear_backup(
            frecuencia=self.config['backup']['frecuencia'],
            hora_ejecucion=self.config['backup']['hora_ejecucion'],
            ultimo_backup=self.config['backup'].get('ultimo_backup')
        )
        
        if debe_crear:
            self.crear_backup_automatico()
    
    def crear_backup_automatico(self):
        """Crea un backup automático."""
        if self.backup_manager.crear_backup():
            # Actualizar configuración
            self.config['backup']['ultimo_backup'] = datetime.now().isoformat()
            guardar_configuracion(self.config)
            print("✓ Backup automático creado exitosamente")
```

## Backup Manual

### Desde la Interfaz Gráfica

La aplicación incluye una opción en el menú para crear backups manualmente:

```
Menú → Herramientas → Crear Backup Ahora
```

Al seleccionar esta opción:
1. Se muestra un diálogo de progreso
2. Se ejecuta el backup
3. Se muestra mensaje de éxito o error

### Desde Línea de Comandos

```bash
python -c "from backup_manager import BackupManager; from firebase_manager import FirebaseManager; from config_manager import cargar_configuracion; config = cargar_configuracion(); fm = FirebaseManager(config['firebase']['credentials_path'], config['firebase']['project_id']); bm = BackupManager(config['backup']['ruta_backup_sqlite'], fm); bm.crear_backup()"
```

O crear un script simple `crear_backup.py`:

```python
from backup_manager import BackupManager
from firebase_manager import FirebaseManager
from config_manager import cargar_configuracion

config = cargar_configuracion()

firebase_mgr = FirebaseManager(
    credentials_path=config['firebase']['credentials_path'],
    project_id=config['firebase']['project_id']
)

backup_mgr = BackupManager(
    ruta_backup=config['backup']['ruta_backup_sqlite'],
    firebase_manager=firebase_mgr
)

print("Creando backup...")
if backup_mgr.crear_backup():
    print("✓ Backup creado exitosamente")
    info = backup_mgr.obtener_info_backup()
    if info:
        print(f"Fecha: {info['fecha_backup']}")
        print(f"Registros totales: {sum([
            info['registros_equipos'],
            info['registros_transacciones'],
            info['registros_entidades'],
            info['registros_mantenimientos'],
            info['registros_pagos_operadores']
        ])}")
else:
    print("✗ Error al crear backup")
```

## Información del Backup

### Obtener Información

```python
info = backup_manager.obtener_info_backup()

if info:
    print(f"Última fecha de backup: {info['fecha_backup']}")
    print(f"Versión: {info['version']}")
    print(f"Equipos: {info['registros_equipos']}")
    print(f"Transacciones: {info['registros_transacciones']}")
    print(f"Entidades: {info['registros_entidades']}")
    print(f"Mantenimientos: {info['registros_mantenimientos']}")
    print(f"Pagos a operadores: {info['registros_pagos_operadores']}")
    print(f"Tamaño del archivo: {info['tamanio_archivo'] / 1024 / 1024:.2f} MB")
```

### Consultar Datos del Backup

El archivo SQLite de backup se puede consultar directamente:

```python
import sqlite3

conn = sqlite3.connect('backups/equipos_backup.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Ejemplo: Listar equipos
cur.execute("SELECT * FROM equipos WHERE activo = 1")
equipos = cur.fetchall()

for equipo in equipos:
    print(f"{equipo['nombre']} - {equipo['marca']} {equipo['modelo']}")

conn.close()
```

O usando herramientas gráficas como:
- [DB Browser for SQLite](https://sqlitebrowser.org/)
- DBeaver
- SQLite Studio

## Estrategias de Backup

### Backup Incremental vs Completo

Actualmente, el sistema realiza **backups completos**:
- Ventaja: Simplicidad, consistencia garantizada
- Desventaja: Puede ser lento con muchos datos

### Backups Múltiples (Rotación)

Para mantener múltiples versiones de backups:

1. **Configurar rotación en el script**:
   ```python
   from datetime import datetime
   import shutil
   
   # Antes de crear nuevo backup
   if os.path.exists(ruta_backup):
       fecha_str = datetime.now().strftime('%Y%m%d_%H%M%S')
       ruta_antigua = f"backup_{fecha_str}.db"
       shutil.copy2(ruta_backup, ruta_antigua)
   
   # Luego crear el nuevo backup
   backup_manager.crear_backup()
   ```

2. **Limpiar backups antiguos** (mantener solo los últimos 7 días):
   ```python
   import os
   from datetime import datetime, timedelta
   
   directorio_backups = './backups/'
   dias_mantener = 7
   fecha_limite = datetime.now() - timedelta(days=dias_mantener)
   
   for archivo in os.listdir(directorio_backups):
       if archivo.startswith('backup_') and archivo.endswith('.db'):
           ruta_archivo = os.path.join(directorio_backups, archivo)
           fecha_archivo = datetime.fromtimestamp(os.path.getmtime(ruta_archivo))
           
           if fecha_archivo < fecha_limite:
               os.remove(ruta_archivo)
               print(f"Eliminado: {archivo}")
   ```

## Restauración desde Backup

**Importante**: La restauración NO está automatizada. Los backups son principalmente para consulta y respaldo.

### Proceso Manual de Restauración

Si necesitas restaurar datos desde un backup:

1. **Verificar el backup**:
   ```bash
   sqlite3 backups/equipos_backup.db "SELECT COUNT(*) FROM equipos;"
   ```

2. **Restaurar a Firebase** (script personalizado):
   ```python
   # Este es un ejemplo básico - ajustar según necesidades
   import sqlite3
   from firebase_manager import FirebaseManager
   
   # Conectar a backup
   conn = sqlite3.connect('backups/equipos_backup.db')
   conn.row_factory = sqlite3.Row
   cur = conn.cursor()
   
   # Conectar a Firebase
   firebase_mgr = FirebaseManager('credentials.json', 'proyecto-id')
   
   # Restaurar equipos (ejemplo)
   cur.execute("SELECT * FROM equipos")
   equipos = cur.fetchall()
   
   for equipo in equipos:
       datos = {
           'nombre': equipo['nombre'],
           'marca': equipo['marca'],
           'modelo': equipo['modelo'],
           # ... otros campos
       }
       firebase_mgr.agregar_equipo(datos)
   
   conn.close()
   ```

## Monitoreo y Alertas

### Verificar Estado del Backup

```python
def verificar_estado_backup(config):
    """Verifica si los backups están al día."""
    from datetime import datetime, timedelta
    
    ultimo_backup = config['backup'].get('ultimo_backup')
    
    if not ultimo_backup:
        return "⚠ Nunca se ha creado un backup"
    
    ultimo_dt = datetime.fromisoformat(ultimo_backup)
    dias_desde_backup = (datetime.now() - ultimo_dt).days
    
    if dias_desde_backup > 2:
        return f"⚠ Último backup hace {dias_desde_backup} días"
    elif dias_desde_backup > 1:
        return f"⚡ Último backup hace {dias_desde_backup} día"
    else:
        return "✓ Backup al día"
```

### Logs de Backup

Todos los backups generan logs:

```python
import logging

logger = logging.getLogger('backup_manager')
logger.info("Backup completado exitosamente")
logger.info(f"Total de registros: {total}")
```

Configurar logging en `main_qt.py`:

```python
logging.basicConfig(
    filename='equipos.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
```

## Mejores Prácticas

1. **Ubicación del Backup**:
   - Usar una carpeta específica para backups
   - Preferiblemente en un disco diferente al del sistema
   - Considerar backups en la nube (OneDrive, Dropbox, etc.)

2. **Frecuencia**:
   - Para uso intensivo: backups diarios
   - Para uso ligero: pueden ser cada 2-3 días

3. **Verificación**:
   - Revisar periódicamente que los backups se crean correctamente
   - Verificar el tamaño del archivo (debe crecer con el tiempo)

4. **Seguridad**:
   - Los backups contienen todos los datos del negocio
   - Proteger la carpeta de backups
   - Considerar cifrado si se almacenan en la nube

5. **Mantenimiento**:
   - Implementar rotación de backups antiguos
   - Mantener al menos los últimos 7-30 días
   - Realizar backups completos mensuales para archivo

## Resolución de Problemas

### El backup no se crea automáticamente

**Verificar**:
1. La aplicación está en ejecución a la hora programada
2. La configuración en `config_equipos.json` es correcta
3. Hay conexión a Firebase
4. Hay espacio en disco

**Solución**:
- Revisar logs de la aplicación
- Crear backup manual para verificar que funciona
- Ajustar la hora de ejecución

### Error de permisos al crear backup

**Problema**: No se puede escribir en la carpeta de backup.

**Solución**:
1. Verificar permisos de la carpeta
2. Ejecutar la aplicación con permisos adecuados
3. Cambiar la ruta del backup a una carpeta con permisos de escritura

### Backup muy grande

**Problema**: El archivo de backup ocupa demasiado espacio.

**Opciones**:
1. Comprimir backups antiguos
2. Implementar backup incremental (requiere desarrollo)
3. Limpiar datos históricos muy antiguos en Firebase

### Backup incompleto

**Problema**: El backup tiene menos registros de lo esperado.

**Verificar**:
1. Conexión a Firebase durante el backup
2. Logs para ver si hubo errores
3. Comparar conteos entre Firebase y SQLite

## Conclusión

El sistema de backups de EQUIPOS 4.0 proporciona:
- ✅ Respaldo automático de seguridad
- ✅ Acceso offline a datos
- ✅ Historial de datos
- ✅ Simplicidad de uso

Mantener los backups configurados y funcionando correctamente es esencial para la seguridad de los datos del negocio.
