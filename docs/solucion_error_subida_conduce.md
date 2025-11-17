# Solución: Error al Subir Conduce a Firebase Storage

## Problema

Al intentar guardar un alquiler con un conduce adjunto, aparece el error:
```
No se pudo subir el conduce. El alquiler se guardará sin conduce adjunto.
```

## Diagnóstico

### Paso 1: Revisar el Archivo de Logs

Abrir el archivo `equipos.log` y buscar la línea:
```
=== Iniciando subida de conduce ===
```

Justo después de esta línea, verás:
- Nombre del archivo
- Tamaño del archivo
- Datos del alquiler
- Ruta de storage construida

**El error específico aparecerá con el prefijo `ERROR`**. Ejemplos comunes:

#### Error A: Problema de Conexión
```
ERROR: Error al subir archivo a Storage: [Errno 11001] getaddrinfo failed
```
**Solución**: Verificar conexión a Internet, firewall, o proxy.

#### Error B: Permisos Insuficientes
```
ERROR: Error al subir archivo a Storage: 403 Insufficient permissions
```
**Solución**: Ver sección "Permisos de Service Account" abajo.

#### Error C: Bucket No Existe
```
ERROR: Error al subir archivo a Storage: 404 The bucket does not exist
```
**Solución**: Verificar `storage_bucket` en `config_equipos.json`.

#### Error D: Credenciales Incorrectas
```
ERROR: Error al subir archivo a Storage: 401 Unauthorized
```
**Solución**: Verificar archivo de credenciales en `config_equipos.json`.

### Paso 2: Verificar Configuración

#### config_equipos.json

Debe contener:
```json
{
  "firebase": {
    "credentials_path": "firebase_credentials.json",
    "project_id": "equipos-zoec",
    "storage_bucket": "equipos-zoec.appspot.com"
  }
}
```

**Verificar**:
- ✅ `credentials_path` apunta a un archivo que existe
- ✅ `project_id` coincide con el proyecto en Firebase Console
- ✅ `storage_bucket` es el bucket correcto (termina en `.appspot.com`)

#### Archivo de Credenciales

El archivo `firebase_credentials.json` debe ser un Service Account JSON descargado de:
1. Firebase Console
2. Project Settings → Service Accounts
3. Generate New Private Key

**Verificar que el archivo contiene**:
```json
{
  "type": "service_account",
  "project_id": "equipos-zoec",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "firebase-adminsdk-xxxxx@equipos-zoec.iam.gserviceaccount.com",
  ...
}
```

### Paso 3: Permisos de Service Account

El Service Account debe tener permisos suficientes para:
1. Subir archivos a Storage
2. Hacer archivos públicos (opcional)
3. Generar URLs firmadas

#### Verificar Permisos en Firebase Console

1. Ir a [Firebase Console](https://console.firebase.google.com/)
2. Seleccionar proyecto `equipos-zoec`
3. Settings → Service Accounts
4. Click en "Manage service account permissions"
5. Buscar el email del service account (ej: `firebase-adminsdk-xxxxx@equipos-zoec.iam.gserviceaccount.com`)

#### Permisos Requeridos

El Service Account debe tener al menos uno de estos roles:

**Opción 1: Rol Completo (Recomendado)**
- **Firebase Admin SDK Administrator Service Agent**

**Opción 2: Roles Específicos**
- **Storage Object Admin** (para crear/modificar objetos)
- **Storage Object Creator** (mínimo para subir)

#### Cómo Agregar Permisos

Si faltan permisos:

1. En Google Cloud Console (no Firebase Console)
2. IAM & Admin → IAM
3. Buscar el service account
4. Click en editar (ícono de lápiz)
5. Add Another Role → Seleccionar "Storage Object Admin"
6. Save

### Paso 4: Reglas de Firebase Storage

Aunque las reglas no afectan la subida (se hace con service account), pueden afectar si se intenta hacer público el archivo.

#### Verificar Reglas en Firebase Console

1. Firebase Console → Storage → Rules
2. Las reglas deben permitir lectura pública:

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /{allPaths=**} {
      allow read: if true;  // Lectura pública
      allow write: if request.auth != null;  // Solo autenticados
    }
  }
}
```

**Nota**: Con service account, la escritura funciona incluso con estas reglas.

### Paso 5: Verificar Bucket de Storage

1. Firebase Console → Storage
2. Verificar que el bucket existe y está activo
3. El nombre debe coincidir con `storage_bucket` en config

#### Crear Bucket si No Existe

Si Storage no está inicializado:
1. Firebase Console → Storage
2. Click "Get Started"
3. Aceptar reglas por defecto
4. Esperar a que se cree el bucket
5. Verificar que el nombre es `equipos-zoec.appspot.com`

## Soluciones Paso a Paso

### Solución 1: Verificar y Corregir Configuración

1. Abrir `config_equipos.json`
2. Verificar todos los campos
3. Confirmar que archivo de credenciales existe
4. Reiniciar aplicación

### Solución 2: Regenerar Credenciales

Si las credenciales son antiguas o tienen permisos insuficientes:

1. Firebase Console → Project Settings → Service Accounts
2. Generate New Private Key
3. Descargar archivo JSON
4. Reemplazar `firebase_credentials.json`
5. Reiniciar aplicación

### Solución 3: Verificar Permisos de Service Account

1. Google Cloud Console → IAM & Admin → IAM
2. Buscar service account de Firebase
3. Verificar tiene rol "Storage Object Admin"
4. Si no, agregar el rol
5. Esperar 1-2 minutos para propagación
6. Reiniciar aplicación

### Solución 4: Probar Subida Manual

Para verificar que Storage funciona:

```python
from firebase_admin import storage
import firebase_admin
from firebase_admin import credentials

# Inicializar
cred = credentials.Certificate("firebase_credentials.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'equipos-zoec.appspot.com'
})

# Probar subida
bucket = storage.bucket()
blob = bucket.blob('test/prueba.txt')
blob.upload_from_string('Hola mundo')
print(f"URL: {blob.public_url}")
```

Si esto falla, el problema es de configuración de Firebase, no de la aplicación.

### Solución 5: Modo Fallback (Temporal)

Si el problema persiste y necesitas trabajar urgentemente:

1. Comentar temporalmente la subida de conduces
2. Guardar los archivos localmente
3. Subirlos manualmente a Firebase Storage después

## Prevención de Errores Futuros

### Logs Mejorados

La aplicación ahora tiene logs detallados que muestran:
- ✅ Archivo a subir
- ✅ Tamaño del archivo
- ✅ Ruta de storage
- ✅ Error específico si falla

### Validaciones

Antes de subir, la app valida:
- ✅ Archivo existe
- ✅ Archivo no es demasiado grande (>10MB advertencia)
- ✅ Storage Manager está inicializado

### Sistema de Fallback

Si `make_public()` falla:
1. Intenta generar URL firmada (válida 7 días)
2. Como último recurso, usa URL pública sin verificar

## Referencia Rápida de Errores

| Código Error | Causa | Solución |
|-------------|-------|----------|
| 401 | Credenciales incorrectas | Regenerar credenciales |
| 403 | Permisos insuficientes | Agregar rol Storage Object Admin |
| 404 | Bucket no existe | Crear bucket o corregir nombre |
| Network error | Sin Internet/Firewall | Verificar conexión |
| FileNotFoundError | Archivo no existe | Verificar ruta del archivo |

## Soporte

Si después de seguir todos los pasos el problema persiste:

1. **Copiar todo el bloque de error del log** desde `=== Iniciando subida ===` hasta el `ERROR`
2. **Captura de pantalla** de la configuración en Firebase Console → Storage
3. **Verificar** en Firebase Console → Storage → Files que el bucket existe
4. **Revisar** en equipos.log si hay errores de inicialización de Storage al inicio

### Información Útil para Debugging

Al reportar el problema, incluir:
- Versión de Python
- Sistema operativo
- Contenido de `config_equipos.json` (ocultar datos sensibles)
- Últimas 50 líneas de `equipos.log` desde el error
- Captura de pantalla del error en la app
