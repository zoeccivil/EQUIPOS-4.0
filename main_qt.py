"""
Punto de entrada principal para EQUIPOS 4.0
Adaptado para trabajar con Firebase en lugar de SQLite
"""

import sys
import os
import logging
import traceback
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt6.QtCore import QTimer

from firebase_manager import FirebaseManager
from backup_manager import BackupManager
from storage_manager import StorageManager
from config_manager import cargar_configuracion, guardar_configuracion
from app_gui_qt import AppGUI
from theme_manager import ThemeManager

# Configurar logging global
LOG_FILE = "equipos.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def excepthook(exc_type, exc_value, exc_tb):
    """
    Manejador global de excepciones: registra la traza completa en el log
    y muestra un QMessageBox si es posible.
    """
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.exception("Excepción no controlada:\n%s", msg)

    # Intentar mostrar un diálogo si la app GUI está disponible
    try:
        app = QApplication.instance()
        created_temp_app = False
        if app is None:
            app = QApplication([])
            created_temp_app = True

        QMessageBox.critical(None, "Error inesperado",
                             "Se produjo un error inesperado y la aplicación debe cerrarse.\n\n"
                             f"{exc_value}")

        if created_temp_app:
            app.quit()
    except Exception as show_err:
        logger.exception("No se pudo mostrar QMessageBox en excepthook: %s", show_err)
        try:
            print("Error inesperado:", exc_value, file=sys.stderr)
        except Exception:
            pass

    # Llamar al excepthook original
    try:
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    except Exception:
        pass

    sys.exit(1)


def main():
    """Función principal de la aplicación"""
    # Registrar el manejador global de excepciones
    sys.excepthook = excepthook

    # Crear la aplicación Qt
    app = QApplication(sys.argv)

    # Cargar configuración
    try:
        config = cargar_configuracion()
    except Exception as e:
        logger.exception("No se pudo cargar la configuración: %s", e)
        QMessageBox.critical(None, "Error de Configuración",
                             f"No se pudo cargar la configuración:\n{e}\n\n"
                             "Asegúrese de que existe el archivo config_equipos.json")
        sys.exit(1)

    # Verificar que existe el archivo de credenciales de Firebase
    firebase_creds = config.get('firebase', {}).get('credentials_path', 'firebase_credentials.json')
    if not os.path.exists(firebase_creds):
        QMessageBox.critical(None, "Credenciales de Firebase no encontradas",
                             f"No se encontró el archivo de credenciales de Firebase:\n{firebase_creds}\n\n"
                             "Por favor:\n"
                             "1. Descargue las credenciales desde Firebase Console\n"
                             "2. Guárdelas como 'firebase_credentials.json' en el directorio raíz\n"
                             "3. Reinicie la aplicación")
        logger.error("No se encontraron credenciales de Firebase")
        sys.exit(1)

    # Aplicar tema
    theme_name = config.get('app', {}).get('tema', 'Claro')
    try:
        ThemeManager.apply_theme(app, theme_name)
        logger.info(f"Tema aplicado: {theme_name}")
    except Exception as e:
        logger.warning(f"No se pudo aplicar el tema {theme_name}: {e}")
        ThemeManager.apply_theme(app, "Claro")  # Fallback al tema claro

    # Inicializar Firebase Manager
    try:
        firebase_manager = FirebaseManager(
            credentials_path=config['firebase']['credentials_path'],
            project_id=config['firebase']['project_id']
        )
        logger.info("Firebase Manager inicializado correctamente")
    except Exception as e:
        logger.exception("No se pudo inicializar Firebase Manager: %s", e)
        QMessageBox.critical(None, "Error de Firebase",
                             f"No se pudo conectar con Firebase:\n{e}\n\n"
                             "Verifique:\n"
                             "1. Las credenciales son correctas\n"
                             "2. Tiene conexión a Internet\n"
                             "3. El proyecto de Firebase está activo")
        sys.exit(1)

    # Inicializar Backup Manager
    try:
        backup_manager = BackupManager(
            ruta_backup=config['backup']['ruta_backup_sqlite'],
            firebase_manager=firebase_manager
        )
        logger.info("Backup Manager inicializado correctamente")
    except Exception as e:
        logger.warning(f"No se pudo inicializar Backup Manager: {e}")
        backup_manager = None

    # Inicializar Storage Manager (opcional - si está configurado)
    storage_manager = None
    storage_bucket = config.get('firebase', {}).get('storage_bucket')
    if storage_bucket:
        try:
            storage_manager = StorageManager(bucket_name=storage_bucket) # Corregido: StorageManager solo necesita bucket_name
            logger.info(f"Storage Manager inicializado correctamente con bucket: {storage_bucket}")
        except Exception as e:
            logger.warning(f"No se pudo inicializar Storage Manager: {e}")
            logger.warning("La funcionalidad de conduces estará deshabilitada")
    else:
        logger.info("Storage bucket no configurado - funcionalidad de conduces deshabilitada")

    # Iniciar la ventana principal
    try:
        # --- ¡LÍNEA CORREGIDA! ---
        # Se pasa el 'storage_manager' que se inicializó (en lugar de None)
        window = AppGUI(
            firebase_manager=firebase_manager, 
            backup_manager=backup_manager, 
            storage_manager=storage_manager, 
            config=config
        )
        # --- FIN DE LA CORRECCIÓN ---
        window.show()
        logger.info("Ventana principal creada y mostrada")
    except Exception as e:
        logger.exception("Error creando ventana principal AppGUI: %s", e)
        QMessageBox.critical(None, "Error al iniciar",
                             f"No se pudo iniciar la interfaz gráfica:\n{e}")
        sys.exit(1)

    # Configurar verificación de backups automáticos
    if backup_manager:
        def verificar_backup():
            """Verifica si es necesario crear un backup"""
            try:
                debe_backup = backup_manager.debe_crear_backup(
                    frecuencia=config['backup']['frecuencia'],
                    hora_ejecucion=config['backup']['hora_ejecucion'],
                    ultimo_backup=config['backup'].get('ultimo_backup')
                )
                
                if debe_backup:
                    logger.info("Iniciando backup automático...")
                    if backup_manager.crear_backup():
                        # Actualizar configuración con la fecha del último backup
                        from datetime import datetime
                        config['backup']['ultimo_backup'] = datetime.now().isoformat()
                        guardar_configuracion(config)
                        logger.info("Backup automático completado")
                    else:
                        logger.error("Error al crear backup automático")
            except Exception as e:
                logger.error(f"Error en verificación de backup: {e}")
        
        # Verificar al inicio
        QTimer.singleShot(5000, verificar_backup)  # 5 segundos después de iniciar
        
        # Verificar cada hora
        timer_backup = QTimer()
        timer_backup.timeout.connect(verificar_backup)
        timer_backup.start(3600000)  # 1 hora en milisegundos

    # Ejecutar el loop de Qt
    try:
        exit_code = app.exec()
        logger.info(f"Aplicación finalizada con exit_code={exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        logger.exception("Error durante app.exec(): %s", e)
        raise


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        logger.exception("Fallo en main (capturado en __main__): %s", e)
        try:
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "Error crítico", f"Fallo crítico: {e}")
        except Exception:
            pass
        sys.exit(1) 