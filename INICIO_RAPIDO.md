# Guía de Inicio Rápido - EQUIPOS 4.0

## Para Desarrolladores

### 1. Clonar el Repositorio

```bash
git clone https://github.com/zoeccivil/EQUIPOS-4.0.git
cd EQUIPOS-4.0
```

### 2. Configurar Entorno

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Firebase

#### a) Crear Proyecto en Firebase

1. Ir a [Firebase Console](https://console.firebase.google.com/)
2. Crear nuevo proyecto → "equipos-zoec" (o el nombre que prefieras)
3. Habilitar **Cloud Firestore**:
   - En el menú lateral, ir a "Firestore Database"
   - Clic en "Crear base de datos"
   - Seleccionar modo de producción
   - Elegir ubicación más cercana

#### b) Descargar Credenciales

1. Configuración del proyecto (⚙️) → Cuentas de servicio
2. Generar nueva clave privada
3. Descargar archivo JSON
4. Guardarlo como `firebase_credentials.json` en la raíz del proyecto

#### c) Configurar Aplicación

```bash
# Copiar plantilla de configuración
cp config_equipos.example.json config_equipos.json

# Editar config_equipos.json y actualizar:
# - "project_id": con tu ID de proyecto Firebase
# - "credentials_path": si cambiaste la ruta del archivo
```

### 4. Probar Instalación

```python
# Ejecutar en Python
python -c "from config_manager import cargar_configuracion; print(cargar_configuracion())"
```

Si no hay errores, la configuración está correcta.

### 5. (Opcional) Migrar Datos desde PROGAIN

Si ya tienes datos en PROGAIN y quieres migrarlos:

```bash
python scripts/migrar_equipos_desde_progain.py
```

El script te pedirá:
1. Ruta a la BD de PROGAIN
2. Confirmación para proceder

---

## Para Testing

### Probar Conexión a Firebase

```python
from firebase_manager import FirebaseManager
from config_manager import cargar_configuracion

config = cargar_configuracion()
fm = FirebaseManager(
    credentials_path=config['firebase']['credentials_path'],
    project_id=config['firebase']['project_id']
)

# Listar equipos (debería estar vacío al inicio)
equipos = fm.obtener_equipos()
print(f"Equipos encontrados: {len(equipos)}")
```

### Agregar un Equipo de Prueba

```python
from firebase_manager import FirebaseManager
from config_manager import cargar_configuracion

config = cargar_configuracion()
fm = FirebaseManager(
    credentials_path=config['firebase']['credentials_path'],
    project_id=config['firebase']['project_id']
)

# Agregar equipo
datos_equipo = {
    'nombre': 'EXCAVADORA PRUEBA',
    'marca': 'KOMATSU',
    'modelo': 'PC200',
    'categoria': 'EXCAVADORA',
    'placa': 'TEST-001',
    'ficha': 'EQ-TEST-001',
    'activo': True
}

equipo_id = fm.agregar_equipo(datos_equipo)
print(f"Equipo creado con ID: {equipo_id}")

# Verificar
equipos = fm.obtener_equipos()
print(f"Total de equipos: {len(equipos)}")
for eq in equipos:
    print(f"  - {eq['nombre']}")
```

### Crear un Backup de Prueba

```python
from backup_manager import BackupManager
from firebase_manager import FirebaseManager
from config_manager import cargar_configuracion

config = cargar_configuracion()

fm = FirebaseManager(
    credentials_path=config['firebase']['credentials_path'],
    project_id=config['firebase']['project_id']
)

bm = BackupManager(
    ruta_backup=config['backup']['ruta_backup_sqlite'],
    firebase_manager=fm
)

print("Creando backup...")
if bm.crear_backup():
    print("✓ Backup creado exitosamente")
    
    # Ver información del backup
    info = bm.obtener_info_backup()
    if info:
        print(f"\nInformación del backup:")
        print(f"  Fecha: {info['fecha_backup']}")
        print(f"  Equipos: {info['registros_equipos']}")
        print(f"  Tamaño: {info['tamanio_archivo'] / 1024:.2f} KB")
else:
    print("✗ Error al crear backup")
```

---

## Estructura Básica

### Agregar un Cliente

```python
datos_cliente = {
    'nombre': 'CLIENTE PRUEBA S.A.',
    'tipo': 'Cliente',
    'telefono': '809-555-1234',
    'cedula': '001-1234567-8',
    'activo': True
}

cliente_id = fm.agregar_entidad(datos_cliente)
```

### Registrar un Alquiler

```python
datos_alquiler = {
    'equipo_id': 'ID_DEL_EQUIPO',
    'cliente_id': 'ID_DEL_CLIENTE',
    'fecha': '2025-11-16',
    'monto': 15000.00,
    'descripcion': 'Alquiler diario',
    'horas': 8.0,
    'precio_por_hora': 1875.00,
    'ubicacion': 'Santo Domingo',
    'pagado': False
}

alquiler_id = fm.registrar_alquiler(datos_alquiler)
```

### Consultar Transacciones

```python
# Todas las transacciones
transacciones = fm.obtener_transacciones()

# Con filtros
filtros = {
    'tipo': 'Ingreso',
    'fecha_inicio': '2025-11-01',
    'fecha_fin': '2025-11-30',
    'pagado': False
}
transacciones = fm.obtener_transacciones(filtros)
```

---

## Comandos Útiles

### Ver logs de migración
```bash
ls -l migracion_equipos_*.log
```

### Ver configuración actual
```bash
cat config_equipos.json
```

### Verificar backup
```bash
# Windows:
dir backups\

# macOS/Linux:
ls -lh backups/
```

### Consultar backup con SQLite
```bash
sqlite3 backups/equipos_backup.db
> SELECT COUNT(*) FROM equipos;
> .quit
```

---

## Problemas Comunes

### Error: "No se encuentra el archivo de credenciales"

**Solución:**
1. Verificar que `firebase_credentials.json` existe
2. Verificar la ruta en `config_equipos.json`
3. Descargar nuevamente desde Firebase Console si es necesario

### Error: "Permission denied" en Firebase

**Solución:**
1. Ir a Firebase Console → Firestore → Reglas
2. Temporalmente (solo para desarrollo), usar:
   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /{document=**} {
         allow read, write: if true;
       }
     }
   }
   ```
3. **IMPORTANTE:** En producción, configurar reglas de seguridad adecuadas

### Backup no se crea

**Solución:**
1. Verificar que la carpeta de destino existe
2. Verificar permisos de escritura
3. Verificar conexión a Firebase
4. Revisar logs para ver el error específico

---

## Próximos Pasos

1. ✅ **Verificar instalación** con los scripts de prueba
2. ✅ **Agregar datos de prueba** para familiarizarte con la API
3. ✅ **Revisar documentación** en la carpeta `docs/`
4. ⏳ **Esperar interfaz gráfica** (en desarrollo)

---

## Recursos

- **Documentación de Firebase:** https://firebase.google.com/docs/firestore
- **Documentación de PyQt6:** https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **Repositorio:** https://github.com/zoeccivil/EQUIPOS-4.0

---

## Soporte

Para problemas o preguntas:
1. Revisar documentación en `docs/`
2. Revisar `RESUMEN_PROYECTO.md`
3. Crear un issue en GitHub
4. Contactar al equipo de desarrollo

---

**¡Listo para comenzar! 🚀**
