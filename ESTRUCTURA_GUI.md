# Estructura de la Interfaz Gráfica EQUIPOS 4.0

```
┌────────────────────────────────────────────────────────────────────┐
│  EQUIPOS 4.0 - Gestión de Alquiler de Equipos Pesados            │
├────────────────────────────────────────────────────────────────────┤
│  Archivo  Gestión  Reportes  Configuración  Ayuda                 │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────┬──────────────────┬───────────────┬──────────────────┐│
│  │Dashboard│ Registro Alquiler│ Gastos Equipos│ Pagos Operadores ││
│  └─────────┴──────────────────┴───────────────┴──────────────────┘│
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                                                                 │ │
│  │                     CONTENIDO DEL TAB                           │ │
│  │                                                                 │ │
│  │  • Dashboard: KPIs, gráficas, estadísticas                     │ │
│  │  • Registro: Tabla de alquileres, búsqueda, filtros            │ │
│  │  • Gastos: Registro y consulta de gastos por equipo            │ │
│  │  • Pagos: Gestión de pagos a operadores                        │ │
│  │                                                                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

## Menús Principales

### Archivo
- Crear Backup Manual...
- Información del Último Backup
- ────────
- Salir

### Gestión
- Equipos
- Clientes
- Operadores
- ────────
- Mantenimientos

### Reportes
- Reporte de Alquileres
- Reporte de Gastos
- Reporte de Mantenimientos
- ────────
- Estado de Cuenta

### Configuración
- Tema ▶
  - Claro
  - Oscuro
  - Azul Corporativo
  - Morado Moderno
- ────────
- Configurar Backups
- Ver Configuración

### Ayuda
- Acerca de
- Documentación

## Tabs Implementados

### 1. Dashboard
- Resumen de ingresos y gastos
- Equipos activos vs inactivos
- Top equipos por ingresos
- Top operadores por horas
- Gráficas y métricas

### 2. Registro de Alquileres
- Tabla de transacciones
- Filtros por cliente, operador, equipo, fecha
- Agregar nuevo alquiler
- Editar alquiler existente
- Ver detalles completos

### 3. Gastos de Equipos
- Registro de gastos por equipo
- Categorías y subcategorías
- Filtros avanzados
- Exportación de reportes

### 4. Pagos a Operadores
- Registro de pagos
- Historial por operador
- Cálculo de horas trabajadas
- Reportes de pagos

## Integración con Firebase

Todos los datos se sincronizan con Firebase Firestore en tiempo real:

```
Firebase Firestore
    ├── equipos (colección)
    ├── transacciones (colección)
    ├── entidades (colección) 
    ├── mantenimientos (colección)
    └── pagos_operadores (colección)
        ↓
   FirebaseManager
        ↓
   Interfaz Gráfica
```

## Backups Automáticos

- Verificación cada hora
- Backup diario automático a SQLite
- Opción de backup manual desde menú
- Información del último backup disponible
