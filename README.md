# EQUIPOS 4.0 - Sistema de Gestión de Equipos Pesados

## Descripción

EQUIPOS 4.0 es una aplicación completa para la gestión de alquiler de equipos pesados, desarrollada con PyQt6 y Firebase como base de datos principal. Esta versión representa una refactorización completa del sistema anterior, separándolo completamente de PROGAIN y utilizando arquitectura en la nube.

## Características Principales

- **Firebase (Firestore) como Base de Datos Principal**: Todos los datos se almacenan en la nube
- **Sistema de Backup Automático**: Backups diarios en SQLite local
- **Gestión Completa de Equipos**: Alta, baja, edición y seguimiento de equipos
- **Control de Alquileres**: Registro de alquileres con clientes y operadores
- **Gastos de Equipos**: Control de gastos asociados a cada equipo
- **Mantenimientos**: Programación y seguimiento de mantenimientos
- **Pagos a Operadores**: Gestión de pagos por horas trabajadas
- **Dashboard Interactivo**: Visualización de KPIs y métricas importantes
- **Reportes**: Generación de reportes detallados en Excel y PDF

## Requisitos

- Python 3.8 o superior
- PyQt6
- Firebase Admin SDK
- Cuenta de Firebase (Firestore)

## Instalación

1. **Clonar el repositorio**:
```bash
git clone https://github.com/zoeccivil/EQUIPOS-4.0.git
cd EQUIPOS-4.0
```

2. **Crear entorno virtual**:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

4. **Configurar Firebase**:
   - Crear un proyecto en [Firebase Console](https://console.firebase.google.com/)
   - Habilitar Firestore Database
   - Descargar las credenciales del servicio (archivo JSON)
   - Guardar el archivo como `firebase_credentials.json` en el directorio raíz

5. **Configurar la aplicación**:
   - Copiar `config_equipos.example.json` a `config_equipos.json`
   - Editar `config_equipos.json` con tus configuraciones

## Uso

### Iniciar la aplicación

```bash
python main_qt.py
```

### Migrar datos desde PROGAIN (primera vez)

Si vienes de la versión anterior de EQUIPOS que compartía base de datos con PROGAIN:

```bash
python scripts/migrar_equipos_desde_progain.py
```

Este script:
- Lee los datos de la base de datos compartida de PROGAIN
- Migra todos los equipos, alquileres, mantenimientos y pagos a Firebase
- Crea un backup inicial en SQLite
- Genera un log detallado del proceso

### Crear Backup Manual

Desde la interfaz:
- Menú → Herramientas → Crear Backup Ahora

O desde la línea de comandos:
```bash
python -c "from backup_manager import BackupManager; BackupManager().crear_backup()"
```

## Estructura del Proyecto

```
EQUIPOS-4.0/
├── main_qt.py                  # Punto de entrada de la aplicación
├── firebase_manager.py         # Capa de datos Firebase
├── backup_manager.py           # Sistema de backups SQLite
├── config_manager.py           # Gestor de configuración
├── app_gui_qt.py              # Ventana principal
├── config_equipos.json        # Configuración (no incluido en git)
├── firebase_credentials.json  # Credenciales Firebase (no incluido en git)
├── tabs/                      # Módulos de interfaz
│   ├── dashboard_tab.py
│   ├── registro_alquileres_tab.py
│   ├── gastos_equipos_tab.py
│   ├── pagos_operadores_tab.py
│   └── reportes_tab.py
├── scripts/                   # Scripts de utilidad
│   └── migrar_equipos_desde_progain.py
├── docs/                      # Documentación
│   ├── arquitectura_equipos_firebase.md
│   ├── migracion_desde_progain.md
│   └── backups_sqlite.md
└── requirements.txt           # Dependencias

```

## Configuración

El archivo `config_equipos.json` contiene:

```json
{
  "firebase": {
    "credentials_path": "firebase_credentials.json",
    "project_id": "equipos-zoec"
  },
  "backup": {
    "ruta_backup_sqlite": "D:/Backups/Equipos/equipos_backup.db",
    "frecuencia": "diario",
    "hora_ejecucion": "02:00",
    "ultimo_backup": null
  },
  "app": {
    "tema": "claro",
    "idioma": "es"
  }
}
```

## Arquitectura

### Firestore Collections

- **equipos**: Información de equipos pesados
  - id, nombre, marca, modelo, categoria, activo, etc.
  
- **transacciones**: Alquileres, ingresos y gastos
  - id, tipo, fecha, monto, equipo_id, cliente_id, etc.
  
- **entidades**: Clientes y operadores
  - id, nombre, tipo (Cliente/Operador), telefono, cedula
  
- **mantenimientos**: Historial de mantenimientos
  - id, equipo_id, fecha, descripcion, costo, etc.
  
- **pagos_operadores**: Pagos a operadores
  - id, operador_id, fecha, monto, horas, equipo_id

### Backup SQLite

El sistema crea automáticamente backups diarios que replican la estructura de Firestore en una base de datos SQLite local. Esto proporciona:
- Respaldo de seguridad
- Capacidad de trabajo offline (solo lectura)
- Historial de datos

## Seguridad

- Las credenciales de Firebase nunca se incluyen en el repositorio
- El archivo de configuración con rutas locales no se sincroniza
- Los backups se pueden cifrar (configuración opcional)

## Contribuir

Este es un proyecto privado de ZOEC. Para contribuir:
1. Crear un fork del repositorio
2. Crear una rama para tu característica (`git checkout -b feature/AmazingFeature`)
3. Commit de tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## Soporte

Para problemas o preguntas:
- Crear un issue en GitHub
- Contactar al equipo de desarrollo de ZOEC

## Licencia

Propietario - ZOEC Civil. Todos los derechos reservados.

## Autores

- **ZOEC Civil** - Desarrollo y mantenimiento

## Historial de Versiones

- **4.0.0** (2025-11) - Refactorización completa con Firebase
  - Separación de PROGAIN
  - Migración a Firebase/Firestore
  - Sistema de backups automáticos
  - Nueva arquitectura en la nube

---

**Nota**: Esta es la versión 4.0 que reemplaza completamente la arquitectura anterior basada en SQLite compartido con PROGAIN.
