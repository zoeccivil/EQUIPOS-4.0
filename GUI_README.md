# Interfaz Gráfica EQUIPOS 4.0 - Guía de Usuario

## Inicio Rápido

### Requisitos Previos

1. Configurar Firebase (ver `INICIO_RAPIDO.md`)
2. Tener el archivo `firebase_credentials.json`
3. Tener el archivo `config_equipos.json` configurado

### Ejecutar la Aplicación

```bash
python main_qt.py
```

La aplicación se abrirá mostrando la ventana principal con 4 tabs.

## Características de la Interfaz

### Sistema de Temas (4 temas modernos)

La aplicación incluye 4 temas que pueden cambiarse desde el menú **Configuración → Tema**:

#### 1. Claro ☀️
Tema por defecto, limpio y profesional
- Fondo claro
- Alta legibilidad
- Ideal para trabajo diurno

#### 2. Oscuro 🌙
Tema oscuro moderno
- Reduce fatiga visual
- Ideal para trabajo nocturno
- Aspecto profesional

#### 3. Azul Corporativo 💼
Tema azul profesional
- Apariencia corporativa
- Botones y menús en azul
- Profesional y confiable

#### 4. Morado Moderno 🎨
Tema morado vibrante
- Apariencia moderna
- Distintivo y atractivo
- Ideal para destacar

**Nota**: El tema seleccionado se guarda automáticamente y persiste entre sesiones.

## Estructura de Tabs

### Tab 1: Dashboard 📊
Vista general del negocio con:
- KPIs principales (ingresos, gastos, utilidad)
- Equipos activos
- Top equipos por ingresos
- Top operadores por horas trabajadas
- Gráficas y estadísticas

### Tab 2: Registro de Alquileres 📝
Gestión de alquileres de equipos:
- Tabla de todos los alquileres
- Filtros por cliente, operador, equipo, fechas
- Botón "Nuevo Alquiler"
- Editar alquiler existente
- Ver detalles completos
- Estado de pago

### Tab 3: Gastos de Equipos 💰
Control de gastos:
- Registro de gastos por equipo
- Categorías y subcategorías
- Filtros avanzados
- Exportación a Excel/PDF

### Tab 4: Pagos a Operadores 👷
Gestión de pagos:
- Registro de pagos a operadores
- Historial por operador
- Cálculo automático de horas
- Reportes de pagos

## Menús Principales

### Menú Archivo
- **Crear Backup Manual**: Crea un backup inmediato de todos los datos
- **Información del Último Backup**: Muestra detalles del último backup realizado
- **Salir**: Cierra la aplicación

### Menú Gestión
- **Equipos**: Administrar equipos (alta, baja, edición)
- **Clientes**: Administrar clientes
- **Operadores**: Administrar operadores
- **Mantenimientos**: Programar y ver mantenimientos

### Menú Reportes
- **Reporte de Alquileres**: Genera reporte de alquileres por período
- **Reporte de Gastos**: Genera reporte de gastos
- **Reporte de Mantenimientos**: Historial de mantenimientos
- **Estado de Cuenta**: Estado de cuenta por cliente

### Menú Configuración
- **Tema**: Cambiar el tema visual (4 opciones)
- **Configurar Backups**: Configurar frecuencia y ruta de backups
- **Ver Configuración**: Ver la configuración actual en JSON

### Menú Ayuda
- **Acerca de**: Información sobre la aplicación
- **Documentación**: Acceso a la documentación técnica

## Funcionalidades Principales

### Gestión de Equipos

1. **Ver Equipos**: Desde Gestión → Equipos
2. **Agregar Equipo**: Click en "Nuevo Equipo"
3. **Editar Equipo**: Seleccionar y click en "Editar"
4. **Desactivar Equipo**: Marcar como inactivo

### Registro de Alquileres

1. **Nuevo Alquiler**: 
   - Seleccionar equipo
   - Seleccionar cliente
   - Seleccionar operador (opcional)
   - Ingresar fecha, horas, precio
   - Guardar

2. **Buscar Alquileres**:
   - Usar filtros en el tab
   - Por cliente, operador, equipo, fechas
   - Click en "Buscar"

### Gestión de Gastos

1. **Registrar Gasto**:
   - Seleccionar equipo
   - Seleccionar categoría
   - Ingresar monto y descripción
   - Guardar

2. **Ver Gastos**:
   - Usar filtros para búsqueda
   - Exportar a Excel

### Backups

#### Backup Manual
1. Archivo → Crear Backup Manual
2. Confirmar
3. El backup se crea en la ruta configurada

#### Backup Automático
- Se ejecuta automáticamente según configuración
- Por defecto: diario a las 2:00 AM
- Verificación cada hora mientras la app está abierta

#### Ver Información de Backup
- Archivo → Información del Último Backup
- Muestra: fecha, versión, cantidad de registros, tamaño

## Conexión con Firebase

### Datos en Tiempo Real

La aplicación sincroniza automáticamente con Firebase:
- **Equipos**: Sincronización al cargar
- **Clientes/Operadores**: Sincronización al cargar
- **Transacciones**: Actualización en tiempo real

### Sin Conexión a Internet

- Los backups locales SQLite permiten consulta offline
- No se pueden crear/editar registros sin conexión
- Al recuperar conexión, la app se sincroniza automáticamente

## Personalización

### Cambiar Tema

1. Configuración → Tema
2. Seleccionar tema deseado
3. El cambio es inmediato
4. Se guarda en `config_equipos.json`

### Configurar Backups

Editar `config_equipos.json`:

```json
{
  "backup": {
    "ruta_backup_sqlite": "D:/Backups/equipos_backup.db",
    "frecuencia": "diario",
    "hora_ejecucion": "02:00"
  }
}
```

- **ruta_backup_sqlite**: Dónde se guarda el backup
- **frecuencia**: "diario", "semanal", "mensual"
- **hora_ejecucion**: Hora en formato HH:MM (24h)

## Atajos de Teclado

(A implementar en versiones futuras)

- `Ctrl+N`: Nuevo registro
- `Ctrl+F`: Buscar
- `Ctrl+S`: Guardar
- `Ctrl+Q`: Salir

## Solución de Problemas

### La aplicación no inicia

1. Verificar que existe `firebase_credentials.json`
2. Verificar que existe `config_equipos.json`
3. Revisar el archivo `equipos.log` para errores

### Error de conexión a Firebase

1. Verificar conexión a Internet
2. Verificar credenciales de Firebase
3. Verificar que el proyecto Firebase está activo

### Los datos no se cargan

1. Verificar conexión a Firebase
2. Revisar logs en `equipos.log`
3. Intentar crear backup manual para verificar conectividad

### El tema no cambia

1. Reiniciar la aplicación
2. Verificar que se guardó en `config_equipos.json`
3. Algunos elementos requieren reinicio

## Rendimiento

### Optimizaciones

- Carga de datos inicial asíncrona
- Caché de datos frecuentes
- Backups incrementales (futuro)

### Recomendaciones

- Mantener menos de 10,000 transacciones activas
- Realizar backups regularmente
- Limpiar datos antiguos periódicamente

## Seguridad

### Datos

- Datos principales en Firebase (encriptado en tránsito)
- Backups locales en SQLite
- No se guardan credenciales en la aplicación

### Recomendaciones

1. Proteger el archivo `firebase_credentials.json`
2. No compartir el archivo de configuración
3. Realizar backups en ubicación segura
4. Usar contraseñas fuertes en Firebase Console

## Soporte

Para problemas o sugerencias:
- Revisar documentación en `docs/`
- Consultar `INICIO_RAPIDO.md`
- Revisar logs en `equipos.log`
- Contactar al equipo de desarrollo

---

**EQUIPOS 4.0** - Sistema de Gestión de Alquiler de Equipos Pesados
© 2025 ZOEC Civil
