# Configuración de Firebase Storage para Conduces

## Problema Común: "No se pudo subir el conduce"

Si experimentas errores al subir conduces, probablemente necesites configurar los permisos de Firebase Storage.

## Solución: Configurar Reglas de Seguridad

### Paso 1: Acceder a Firebase Console

1. Ir a [Firebase Console](https://console.firebase.google.com/)
2. Seleccionar tu proyecto (`equipos-zoec`)
3. En el menú lateral, clic en **Storage**
4. Ir a la pestaña **Rules** (Reglas)

### Paso 2: Configurar Reglas de Seguridad

Reemplaza las reglas existentes con estas:

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // Regla para conduces: lectura pública, escritura autenticada
    match /conduces/{year}/{month}/{fileName} {
      allow read: if true;  // Cualquiera puede leer (ver conduces)
      allow write: if request.auth != null;  // Solo usuarios autenticados pueden escribir
    }
    
    // Regla para backups (opcional)
    match /backups/{allPaths=**} {
      allow read, write: if request.auth != null;
    }
    
    // Regla por defecto para otros archivos
    match /{allPaths=**} {
      allow read: if request.auth != null;
      allow write: if request.auth != null;
    }
  }
}
```

### Paso 3: Publicar las Reglas

1. Hacer clic en **Publish** (Publicar)
2. Esperar confirmación de que las reglas se aplicaron

## Opciones de Configuración

### Opción 1: Acceso Público (Recomendado para conduces)

```javascript
match /conduces/{year}/{month}/{fileName} {
  allow read: if true;  // ✅ Lectura pública
  allow write: if request.auth != null;  // Escritura solo autenticada
}
```

**Ventajas**:
- URLs públicas permanentes
- No expiran
- Fácil compartir enlaces

**Desventajas**:
- Cualquiera con la URL puede ver el conduce

### Opción 2: Acceso Solo Autenticado (Más Seguro)

```javascript
match /conduces/{year}/{month}/{fileName} {
  allow read: if request.auth != null;  // ✅ Solo usuarios autenticados
  allow write: if request.auth != null;
}
```

**Ventajas**:
- Más seguro
- Control total de acceso

**Desventajas**:
- Requiere URLs firmadas (expiran en 7 días por defecto)
- La app ya maneja esto automáticamente con fallback

## Verificar Configuración

### Desde la Aplicación

1. Intentar subir un conduce
2. Revisar `equipos.log`
3. Buscar uno de estos mensajes:

**Éxito con acceso público**:
```
INFO: Archivo hecho público: https://storage.googleapis.com/...
```

**Éxito con URL firmada**:
```
WARNING: No se pudo hacer público el archivo: ...
INFO: Generando URL firmada temporal...
INFO: URL firmada generada (válida 7 días)
```

**Error**:
```
ERROR: Error al guardar conduce: ...
```

### Desde Firebase Console

1. Ir a Storage
2. Navegar a `conduces/2025/11/` (o la fecha actual)
3. Intentar acceder a un archivo
4. Si muestra el archivo → Configuración correcta
5. Si muestra error de permisos → Revisar reglas

## Solución de Problemas

### Error: "Permission denied"

**Causa**: Las reglas de Storage no permiten la operación

**Solución**:
1. Verificar reglas en Firebase Console
2. Asegurar que incluyen la ruta `conduces/{year}/{month}/{fileName}`
3. Publicar las reglas actualizadas

### Error: "Failed to make blob public"

**Causa**: El bucket no permite hacer archivos públicos

**Solución**:
- No hacer nada, la app usa URLs firmadas automáticamente
- O configurar permisos públicos (Opción 1 arriba)

### Error: "File too large"

**Causa**: El archivo excede el límite de Firebase Storage (5GB por defecto)

**Solución**:
1. Reducir tamaño de imagen antes de adjuntar
2. Usar formato JPEG con calidad menor
3. El mini editor ya comprime automáticamente

## Estructura de Archivos en Storage

```
equipos-zoec.appspot.com/
└── conduces/
    ├── 2025/
    │   ├── 01/
    │   │   ├── 00316.jpeg
    │   │   └── 00317.jpeg
    │   ├── 02/
    │   │   └── 00320.jpeg
    │   └── 11/
    │       ├── 00575.jpeg
    │       └── 00576.jpeg
    └── 2024/
        └── 12/
            └── 00500.jpeg
```

## URLs Generadas

### URL Pública (no expira)
```
https://storage.googleapis.com/equipos-zoec.appspot.com/conduces/2025/11/00575.jpeg
```

### URL Firmada (expira en 7 días)
```
https://storage.googleapis.com/equipos-zoec.appspot.com/conduces/2025/11/00575.jpeg?GoogleAccessId=...&Expires=...&Signature=...
```

## Recomendaciones

1. **Para producción**: Usar Opción 1 (acceso público de lectura)
2. **Para desarrollo/testing**: Usar Opción 2 (solo autenticados)
3. **Siempre**: Mantener escritura solo para autenticados
4. **Backup**: Exportar reglas antes de modificar

## Comandos Firebase CLI (Opcional)

Si prefieres configurar desde línea de comandos:

```bash
# Ver reglas actuales
firebase storage:rules:get

# Desplegar nuevas reglas
firebase deploy --only storage
```

## Soporte

Si después de configurar las reglas el problema persiste:

1. Revisar `equipos.log` para el error específico
2. Verificar conexión a Internet
3. Confirmar que el bucket name es correcto: `equipos-zoec.appspot.com`
4. Verificar que las credenciales de Firebase tienen permisos suficientes
5. Intentar con una imagen más pequeña (<1MB) para descartar problemas de tamaño
