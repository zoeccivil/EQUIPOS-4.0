# Guía de Migración desde PROGAIN a EQUIPOS 4.0

## Introducción

Esta guía explica cómo migrar los datos de equipos desde la base de datos compartida de PROGAIN hacia el nuevo sistema EQUIPOS 4.0 basado en Firebase.

## Antes de Comenzar

### Requisitos Previos

1. **Backup de Seguridad**: Antes de iniciar cualquier proceso de migración, crear un backup completo de la base de datos de PROGAIN.
   
2. **Acceso a la Base de Datos de PROGAIN**: Tener acceso al archivo `progain_database.db` o el nombre que tenga tu base de datos compartida.

3. **Firebase Configurado**: Tener un proyecto de Firebase creado y las credenciales descargadas.

4. **EQUIPOS 4.0 Instalado**: Haber instalado todas las dependencias de EQUIPOS 4.0.

### Preparación

1. **Crear Proyecto en Firebase**:
   - Ir a [Firebase Console](https://console.firebase.google.com/)
   - Crear un nuevo proyecto (ej: "equipos-zoec")
   - Habilitar Cloud Firestore
   - Ir a Configuración del Proyecto → Cuentas de servicio
   - Generar nueva clave privada (descarga archivo JSON)
   - Guardar el archivo como `firebase_credentials.json` en la raíz de EQUIPOS-4.0

2. **Configurar EQUIPOS 4.0**:
   ```bash
   cd EQUIPOS-4.0
   cp config_equipos.example.json config_equipos.json
   ```
   
3. **Editar `config_equipos.json`**:
   ```json
   {
     "firebase": {
       "credentials_path": "firebase_credentials.json",
       "project_id": "equipos-zoec"  // Tu project ID de Firebase
     },
     "backup": {
       "ruta_backup_sqlite": "./backups/equipos_backup.db",
       "frecuencia": "diario",
       "hora_ejecucion": "02:00"
     }
   }
   ```

## Proceso de Migración

### Paso 1: Identificar el Proyecto de EQUIPOS en PROGAIN

Por defecto, el script busca el proyecto con ID=8, que corresponde a "EQUIPOS PESADOS ZOEC". Si tu proyecto tiene un ID diferente, necesitarás modificarlo en el script.

Para verificar el ID:
```sql
SELECT id, nombre FROM proyectos WHERE nombre LIKE '%EQUIPO%';
```

### Paso 2: Ejecutar el Script de Migración

```bash
cd EQUIPOS-4.0
python scripts/migrar_equipos_desde_progain.py
```

El script te solicitará:

1. **Ruta a la base de datos de PROGAIN**:
   ```
   Ingrese la ruta completa a la base de datos de PROGAIN: 
   D:/Proyectos/PROGAIN/progain_database.db
   ```

2. **Confirmación**:
   ```
   ¿Desea continuar? (sí/no): sí
   ```

### Paso 3: Proceso de Migración

El script ejecuta los siguientes pasos automáticamente:

1. **Migración de Equipos** (tabla `equipos`)
   - Lee todos los equipos del proyecto
   - Crea documentos en Firestore colección `equipos`
   - Genera mapeo de IDs (SQLite → Firebase)

2. **Migración de Entidades** (tabla `equipos_entidades`)
   - Clientes
   - Operadores
   - Crea documentos en colección `entidades`
   - Genera mapeo de IDs

3. **Migración de Transacciones** (tabla `transacciones`)
   - Solo transacciones de tipo 'Ingreso' con equipo_id
   - Usa los IDs mapeados de equipos y entidades
   - Crea documentos en colección `transacciones`

4. **Migración de Mantenimientos** (tabla `mantenimientos`)
   - Todos los mantenimientos de los equipos migrados
   - Crea documentos en colección `mantenimientos`

5. **Migración de Pagos a Operadores**
   - Transacciones de tipo 'Gasto' con operador_id
   - Crea documentos en colección `pagos_operadores`

### Paso 4: Verificar la Migración

El script genera un archivo de log con nombre:
```
migracion_equipos_YYYYMMDD_HHMMSS.log
```

Revisar este archivo para verificar:

- **Estadísticas de migración**:
  ```
  ✓ Equipos migrados:              45
  ✓ Entidades migradas:            67
  ✓ Transacciones migradas:        1250
  ✓ Mantenimientos migrados:       89
  ✓ Pagos a operadores migrados:   234
  ```

- **Errores** (si los hay):
  ```
  Errores encontrados: 3
  Lista de errores:
    1. No se encontró equipo Firebase para transacción...
    2. ...
  ```

### Paso 5: Backup Inicial

Al finalizar la migración exitosamente, el script automáticamente crea un backup inicial en SQLite:

```
✓ Backup inicial creado en: ./backups/equipos_backup.db
```

Este backup contiene todos los datos migrados y servirá como respaldo de seguridad.

## Lógica de Migración

### Identificación de Datos de EQUIPOS

El script identifica qué datos pertenecen a EQUIPOS usando estos criterios:

1. **Equipos**: Todos los registros de la tabla `equipos` donde `proyecto_id = 8`

2. **Entidades**: Todos los registros de `equipos_entidades` donde `proyecto_id = 8`

3. **Transacciones**: 
   - Tipo = 'Ingreso'
   - equipo_id IS NOT NULL
   - proyecto_id = 8

4. **Mantenimientos**: Todos los que estén asociados a un equipo migrado

5. **Pagos a Operadores**:
   - Tipo = 'Gasto'
   - operador_id IS NOT NULL
   - proyecto_id = 8

### Mapeo de IDs

Dado que Firebase genera IDs automáticamente y son diferentes a los IDs de SQLite, el script mantiene un mapeo:

```python
{
  'equipos': {
    1: 'XYZ123abc',  # SQLite ID → Firebase ID
    2: 'ABC789def',
    ...
  },
  'entidades': {
    5: 'DEF456ghi',
    6: 'GHI012jkl',
    ...
  }
}
```

Este mapeo se usa para actualizar las referencias (foreign keys) en las transacciones, mantenimientos y pagos.

## Validación Post-Migración

### Verificar en Firebase Console

1. Ir a Firebase Console → Firestore Database
2. Verificar que existan las colecciones:
   - `equipos`
   - `entidades`
   - `transacciones`
   - `mantenimientos`
   - `pagos_operadores`

3. Revisar algunos documentos de cada colección

### Verificar Conteos

Comparar los conteos entre PROGAIN y Firebase:

**En PROGAIN (SQLite)**:
```sql
SELECT COUNT(*) FROM equipos WHERE proyecto_id = 8;
SELECT COUNT(*) FROM equipos_entidades WHERE proyecto_id = 8;
SELECT COUNT(*) FROM transacciones WHERE proyecto_id = 8 AND tipo = 'Ingreso' AND equipo_id IS NOT NULL;
```

**En Firebase** (usando Firebase Console o el código):
```python
from firebase_manager import FirebaseManager

fm = FirebaseManager('firebase_credentials.json', 'equipos-zoec')
print(f"Equipos: {len(fm.obtener_equipos(activo=None))}")
print(f"Entidades: {len(fm.obtener_entidades(activo=None))}")
print(f"Transacciones: {len(fm.obtener_transacciones())}")
```

Los números deben coincidir.

## Resolución de Problemas

### Error: "No se encontró el archivo de credenciales"

**Problema**: El archivo `firebase_credentials.json` no existe o la ruta es incorrecta.

**Solución**:
1. Verificar que el archivo existe en la ruta especificada
2. Descargar nuevamente desde Firebase Console si es necesario
3. Actualizar la ruta en `config_equipos.json`

### Error: "No se encontró equipo Firebase para transacción X"

**Problema**: Una transacción hace referencia a un equipo que no fue migrado.

**Causas posibles**:
1. El equipo está en otro proyecto (proyecto_id ≠ 8)
2. El equipo fue eliminado antes de la migración
3. Inconsistencia en los datos originales

**Solución**:
1. Revisar el log para identificar qué equipos faltan
2. Ejecutar query en PROGAIN para verificar:
   ```sql
   SELECT * FROM equipos WHERE id = X;
   ```
3. Si el equipo debe migrarse, ajustar el script o los datos

### Advertencia: "No se encontró cliente/operador Firebase"

**Problema**: Similar al anterior, pero con entidades.

**Solución**: Verificar que todas las entidades relevantes estén en el proyecto correcto.

### La migración es muy lenta

**Posible causa**: Red lenta o muchos datos.

**Soluciones**:
1. Ejecutar desde una conexión de internet rápida
2. El script ya optimiza con inserciones en batch donde es posible
3. Considerar migrar por partes si hay muchos datos

## Migración en Pasos (Opcional)

Si prefieres migrar por partes, puedes modificar el script para ejecutar solo ciertas fases:

```python
# En migrar_equipos_desde_progain.py

# Solo equipos y entidades:
migrador._migrar_equipos(conn, proyecto_id)
migrador._migrar_entidades(conn, proyecto_id)

# Luego en otra ejecución:
# migrador._migrar_transacciones(conn, proyecto_id)
# etc.
```

## Post-Migración

### Limpieza de PROGAIN

**Importante**: Solo realizar DESPUÉS de verificar que la migración a Firebase fue exitosa.

La limpieza de datos de EQUIPOS en PROGAIN se debe hacer manualmente o con un script separado (aún no implementado).

### Configurar Backups Automáticos

Verificar que la configuración de backups esté correcta en `config_equipos.json`:

```json
{
  "backup": {
    "ruta_backup_sqlite": "D:/Backups/Equipos/equipos_backup.db",
    "frecuencia": "diario",
    "hora_ejecucion": "02:00"
  }
}
```

Los backups se ejecutarán automáticamente cuando la aplicación esté en ejecución a la hora programada.

## Consejos y Mejores Prácticas

1. **Hacer la migración en horario de baja actividad**: Preferiblemente cuando nadie esté usando PROGAIN.

2. **Mantener backup de PROGAIN**: No eliminar nada de PROGAIN hasta estar 100% seguro.

3. **Probar en ambiente de prueba primero**: Si es posible, crear un proyecto de Firebase de prueba y migrar ahí primero.

4. **Revisar el log completo**: Siempre revisar el archivo de log generado para detectar advertencias o errores.

5. **Validar datos críticos manualmente**: Verificar algunos registros importantes manualmente en Firebase Console.

6. **Documentar decisiones**: Si se hicieron ajustes o cambios al script, documentarlos.

## Soporte

Para problemas durante la migración:
1. Revisar el archivo de log generado
2. Verificar configuración de Firebase
3. Comprobar conectividad a internet
4. Revisar este documento
5. Contactar al equipo de desarrollo si persiste el problema

---

**Nota**: Este proceso de migración es **unidireccional** (PROGAIN → Firebase). No se implementa sincronización bidireccional. Después de la migración, EQUIPOS 4.0 funcionará completamente independiente de PROGAIN.
