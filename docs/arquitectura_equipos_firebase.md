# Arquitectura de EQUIPOS 4.0 con Firebase

## Introducción

EQUIPOS 4.0 representa una refactorización completa del sistema de gestión de equipos pesados, separándolo completamente de PROGAIN y migrando a una arquitectura basada en la nube con Firebase (Firestore) como base de datos principal.

## Decisiones Arquitectónicas

### 1. Firebase Firestore como Base de Datos Principal

**Razón de elección: Firestore sobre Realtime Database**

Se eligió **Cloud Firestore** en lugar de Realtime Database por las siguientes razones:

1. **Consultas Complejas**: Firestore soporta consultas compuestas y filtrado avanzado, esencial para las búsquedas por cliente, operador, equipo, fecha, etc.

2. **Modelo de Datos Estructurado**: Firestore utiliza colecciones y documentos, lo que se adapta mejor al modelo relacional existente en PROGAIN.

3. **Escalabilidad**: Mejor escalabilidad horizontal para grandes volúmenes de transacciones.

4. **Queries Offline**: Mejor soporte para consultas offline y sincronización.

5. **Indexación Automática**: Firestore crea índices automáticamente para mejorar el rendimiento.

### 2. SQLite para Backups (No como Fuente Principal)

- **Propósito**: Backups diarios automáticos y respaldo de seguridad
- **NO** se usa como fuente principal de datos
- Permite trabajo offline en modo solo lectura
- Proporciona historial de datos

## Estructura de Datos en Firestore

### Colección: `equipos`

```json
{
  "id": "auto-generado",
  "nombre": "EXCAVADORA KOMATSU",
  "marca": "KOMATSU",
  "modelo": "PC200",
  "categoria": "EXCAVADORA",
  "placa": "ABC-123",
  "ficha": "EQ-001",
  "activo": true,
  "fecha_creacion": "2025-11-16T12:00:00Z",
  "fecha_modificacion": "2025-11-16T12:00:00Z"
}
```

**Campos:**
- `id` (string): ID único auto-generado por Firestore
- `nombre` (string): Nombre descriptivo del equipo
- `marca` (string): Marca del equipo
- `modelo` (string): Modelo del equipo
- `categoria` (string): Categoría (EXCAVADORA, RODILLO, etc.)
- `placa` (string): Número de placa del vehículo
- `ficha` (string): Número de ficha interna
- `activo` (boolean): Indica si el equipo está activo
- `fecha_creacion` (timestamp): Fecha de creación del registro
- `fecha_modificacion` (timestamp): Última modificación

### Colección: `transacciones`

```json
{
  "id": "auto-generado",
  "tipo": "Ingreso",
  "equipo_id": "ref_a_equipos",
  "cliente_id": "ref_a_entidades",
  "operador_id": "ref_a_entidades",
  "fecha": "2025-11-16",
  "monto": 15000.00,
  "descripcion": "Alquiler diario",
  "comentario": "Trabajo en proyecto X",
  "horas": 8.5,
  "precio_por_hora": 1764.71,
  "conduce": "COND-123",
  "ubicacion": "Santo Domingo Este",
  "pagado": false,
  "categoria": "",
  "subcategoria": "",
  "fecha_creacion": "2025-11-16T12:00:00Z",
  "fecha_modificacion": "2025-11-16T12:00:00Z"
}
```

**Campos:**
- `id` (string): ID único auto-generado
- `tipo` (string): "Ingreso" o "Gasto"
- `equipo_id` (string): Referencia al equipo
- `cliente_id` (string): Referencia al cliente (para ingresos)
- `operador_id` (string): Referencia al operador
- `fecha` (string ISO 8601): Fecha de la transacción
- `monto` (number): Monto total
- `descripcion` (string): Descripción de la transacción
- `comentario` (string): Comentarios adicionales
- `horas` (number): Horas trabajadas (opcional)
- `precio_por_hora` (number): Precio por hora (opcional)
- `conduce` (string): Número de conduce
- `ubicacion` (string): Ubicación del trabajo
- `pagado` (boolean): Estado de pago
- `categoria` (string): Categoría de gasto (solo para gastos)
- `subcategoria` (string): Subcategoría de gasto (solo para gastos)

### Colección: `entidades`

```json
{
  "id": "auto-generado",
  "nombre": "JUAN PÉREZ",
  "tipo": "Cliente",
  "telefono": "809-555-1234",
  "cedula": "001-1234567-8",
  "activo": true,
  "fecha_creacion": "2025-11-16T12:00:00Z",
  "fecha_modificacion": "2025-11-16T12:00:00Z"
}
```

**Campos:**
- `id` (string): ID único auto-generado
- `nombre` (string): Nombre completo
- `tipo` (string): "Cliente" u "Operador"
- `telefono` (string): Número de teléfono
- `cedula` (string): Número de cédula
- `activo` (boolean): Indica si está activo

### Colección: `mantenimientos`

```json
{
  "id": "auto-generado",
  "equipo_id": "ref_a_equipos",
  "fecha": "2025-11-16",
  "descripcion": "Cambio de aceite",
  "tipo": "Preventivo",
  "costo": 5000.00,
  "odometro_horas": 1250.5,
  "odometro_km": null,
  "notas": "Se cambió filtro también",
  "proximo_tipo": "HORAS",
  "proximo_valor": 250,
  "proximo_fecha": "2025-12-16",
  "fecha_creacion": "2025-11-16T12:00:00Z",
  "fecha_modificacion": "2025-11-16T12:00:00Z"
}
```

**Campos:**
- `id` (string): ID único auto-generado
- `equipo_id` (string): Referencia al equipo
- `fecha` (string): Fecha del mantenimiento
- `descripcion` (string): Descripción del trabajo realizado
- `tipo` (string): Tipo de mantenimiento (Preventivo, Correctivo, etc.)
- `costo` (number): Costo del mantenimiento
- `odometro_horas` (number): Horómetro al momento del servicio
- `odometro_km` (number): Odómetro en kilómetros (si aplica)
- `notas` (string): Notas adicionales
- `proximo_tipo` (string): Tipo de intervalo para próximo servicio ("HORAS" o "KM")
- `proximo_valor` (number): Valor del intervalo (ej: 250 horas)
- `proximo_fecha` (string): Fecha estimada del próximo servicio

### Colección: `pagos_operadores`

```json
{
  "id": "auto-generado",
  "operador_id": "ref_a_entidades",
  "equipo_id": "ref_a_equipos",
  "fecha": "2025-11-16",
  "monto": 3000.00,
  "horas": 8.0,
  "descripcion": "Pago semanal",
  "comentario": "Semana 46",
  "fecha_creacion": "2025-11-16T12:00:00Z",
  "fecha_modificacion": "2025-11-16T12:00:00Z"
}
```

**Campos:**
- `id` (string): ID único auto-generado
- `operador_id` (string): Referencia al operador
- `equipo_id` (string): Referencia al equipo (opcional)
- `fecha` (string): Fecha del pago
- `monto` (number): Monto pagado
- `horas` (number): Horas trabajadas
- `descripcion` (string): Descripción del pago
- `comentario` (string): Comentarios adicionales

## Capa de Datos

### FirebaseManager (`firebase_manager.py`)

La clase `FirebaseManager` encapsula todas las operaciones con Firestore:

**Métodos principales:**

**Equipos:**
- `obtener_equipos(activo=True)` - Lista equipos
- `obtener_equipo_por_id(equipo_id)` - Obtiene un equipo específico
- `agregar_equipo(datos)` - Crea un nuevo equipo
- `editar_equipo(equipo_id, datos)` - Actualiza un equipo
- `eliminar_equipo(equipo_id, eliminar_fisicamente=False)` - Elimina/desactiva un equipo

**Transacciones:**
- `obtener_transacciones(filtros=None)` - Lista transacciones con filtros
- `obtener_transaccion_por_id(transaccion_id)` - Obtiene una transacción
- `registrar_alquiler(datos)` - Registra un alquiler (ingreso)
- `registrar_gasto_equipo(datos)` - Registra un gasto
- `editar_transaccion(transaccion_id, datos)` - Actualiza transacción
- `eliminar_transaccion(transaccion_id)` - Elimina transacción

**Entidades:**
- `obtener_entidades(tipo=None, activo=True)` - Lista entidades
- `obtener_entidad_por_id(entidad_id)` - Obtiene una entidad
- `agregar_entidad(datos)` - Crea una entidad
- `editar_entidad(entidad_id, datos)` - Actualiza entidad
- `eliminar_entidad(entidad_id, eliminar_fisicamente=False)` - Elimina/desactiva

**Mantenimientos:**
- `obtener_mantenimientos(equipo_id=None)` - Lista mantenimientos
- `obtener_mantenimiento_por_id(mantenimiento_id)` - Obtiene mantenimiento
- `registrar_mantenimiento(datos)` - Crea mantenimiento
- `editar_mantenimiento(mantenimiento_id, datos)` - Actualiza mantenimiento
- `eliminar_mantenimiento(mantenimiento_id)` - Elimina mantenimiento

**Pagos a Operadores:**
- `obtener_pagos_operadores(filtros=None)` - Lista pagos
- `registrar_pago_operador(datos)` - Crea pago
- `editar_pago_operador(pago_id, datos)` - Actualiza pago
- `eliminar_pago_operador(pago_id)` - Elimina pago

**Utilidades:**
- `obtener_estadisticas_dashboard(fecha_inicio, fecha_fin)` - Estadísticas para dashboard

## Sistema de Backups

### BackupManager (`backup_manager.py`)

Gestiona backups automáticos desde Firestore a SQLite.

**Funcionalidades:**
- Crea backups completos de todas las colecciones
- Mantiene estructura de BD compatible con consultas
- Guarda metadata del backup (fecha, versión, conteo de registros)
- Verifica necesidad de backup según programación
- Proporciona información del último backup

**Métodos principales:**
- `crear_backup()` - Crea backup completo
- `obtener_info_backup()` - Info del último backup
- `debe_crear_backup(frecuencia, hora, ultimo)` - Verifica si toca backup

## Flujo de Datos

```
┌─────────────────┐
│  Interfaz Qt    │
│   (PyQt6)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ FirebaseManager │ ◄── Capa de abstracción
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Firestore     │ ◄── Fuente principal de datos
│   (Firebase)    │
└────────┬────────┘
         │
         │ (backup diario)
         ▼
┌─────────────────┐
│ BackupManager   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SQLite Local   │ ◄── Backup y respaldo
└─────────────────┘
```

## Ventajas de esta Arquitectura

1. **Independencia Total de PROGAIN**: No hay dependencias compartidas
2. **Datos en la Nube**: Acceso desde múltiples dispositivos
3. **Backups Automáticos**: Seguridad de datos garantizada
4. **Escalabilidad**: Firebase escala automáticamente
5. **Sincronización**: Datos siempre actualizados en tiempo real
6. **Trabajo Offline**: Los backups SQLite permiten consultas offline

## Consideraciones de Seguridad

1. **Credenciales Firebase**: Nunca se incluyen en el repositorio
2. **Reglas de Seguridad**: Configurar en Firebase Console
3. **Autenticación**: Implementar según necesidades (futuro)
4. **Backups Locales**: Se pueden cifrar si es necesario

## Migración desde PROGAIN

Ver documento: `migracion_desde_progain.md`

## Sistema de Backups

Ver documento: `backups_sqlite.md`
