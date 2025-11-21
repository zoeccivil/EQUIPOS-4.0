"""
Punto de entrada principal para EQUIPOS 4.0
Adaptado para trabajar con Firebase en lugar de SQLite

Comportamiento específico:
- Las credenciales de Firebase se buscarán siempre en la carpeta raíz
  de la aplicación (el directorio donde está este archivo) con el nombre
  exacto 'firebase_equipos_key' (se acepta con o sin extensión '.json').
  Esto facilita el empaquetado con PyInstaller: incluya ese archivo en el
  bundle o colóquelo en la misma carpeta que el ejecutable.
- Inicializa firebase_admin tempranamente (si las credenciales están
  presentes) antes de crear StorageManager para evitar errores del tipo:
    "The default Firebase app does not exist. Make sure to initialize the SDK by calling initialize_app()."
- Usa resource_path(...) para localizar archivos tanto en desarrollo como
  cuando la aplicación está empaquetada con PyInstaller.
"""

import sys
import os
import logging
import traceback
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt6.QtCore import QTimer

# Importaciones internas
from firebase_manager import FirebaseManager
from backup_manager import BackupManager
from storage_manager import StorageManager
from config_manager import cargar_configuracion, guardar_configuracion
from app_gui_qt import AppGUI
from theme_manager import ThemeManager

# Intentar importar helpers de firebase_admin (si están instalados)
try:
    from firebase_admin import credentials as fb_credentials  # type: ignore
    from firebase_admin import initialize_app as fb_initialize_app  # type: ignore
    from firebase_admin import _apps as fb_apps  # type: ignore
except Exception:
    fb_credentials = None
    fb_initialize_app = None
    fb_apps = None

# Helper para localizar recursos (soporta PyInstaller)
def resource_path(rel_path: str) -> str:
    """
    Devuelve la ruta absoluta a rel_path, soportando ejecución desde PyInstaller.
    Si el archivo se pasa como ruta absoluta se devuelve tal cual.
    """
    if os.path.isabs(rel_path):
        return rel_path
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, rel_path)

# Ruta "raíz" donde buscamos las credenciales según tu requisito:
def root_credentials_candidates() -> list:
    """
    Devuelve la lista de rutas candidatas donde buscar el archivo de credenciales
    llamado 'firebase_equipos_key' (con y sin .json) en la carpeta raíz de la app.
    """
    base = os.path.abspath(os.path.dirname(__file__))
    candidates = [
        os.path.join(base, "firebase_equipos_key.json"),
        os.path.join(base, "firebase_equipos_key"),
    ]
    return candidates

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

        QMessageBox.critical(
            None,
            "Error inesperado",
            "Se produjo un error inesperado y la aplicación debe cerrarse.\n\n"
            f"{exc_value}",
        )

        if created_temp_app:
            app.quit()
    except Exception as show_err:
        logger.exception("No se pudo mostrar QMessageBox en excepthook: %s", show_err)
        try:
            print("Error inesperado:", exc_value, file=sys.stderr)
        except Exception:
            pass

    # Llamar al excepthook original si existe
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
        QMessageBox.critical(
            None,
            "Error de Configuración",
            "No se pudo cargar la configuración:\n"
            f"{e}\n\n"
            "Asegúrese de que existe el archivo config_equipos.json",
        )
        sys.exit(1)

    # Aplicar tema
    theme_name = config.get("app", {}).get("tema", "Claro")
    try:
        ThemeManager.apply_theme(app, theme_name)
        logger.info(f"Tema aplicado: {theme_name}")
    except Exception as e:
        logger.warning(f"No se pudo aplicar el tema {theme_name}: {e}")
        try:
            ThemeManager.apply_theme(app, "Claro")  # Fallback al tema claro
        except Exception:
            logger.exception("Fallo aplicando tema de fallback 'Claro'")

    # ---------- Localizar credenciales en la carpeta raíz ----------
    # Requisito: siempre buscar en la carpeta raíz por 'firebase_equipos_key' (json o sin)
    cred_candidates = root_credentials_candidates()
    selected_cred = None
    for c in cred_candidates:
        if os.path.exists(c):
            selected_cred = c
            break

    # Si no encontramos las credenciales en la raíz, también comprobamos si config tiene otra ruta
    if not selected_cred:
        cfg_path = config.get("firebase", {}).get("credentials_path")
        if cfg_path:
            cfg_abs = resource_path(cfg_path)
            if os.path.exists(cfg_abs):
                selected_cred = cfg_abs

    # Si aún no hay credenciales, mostrar error instructivo y salir
    if not selected_cred:
        # Mostrar la primera ruta candidata en el mensaje para orientar al usuario
        ejemplo_expect = cred_candidates[0]
        QMessageBox.critical(
            None,
            "Credenciales de Firebase no encontradas",
            "No se encontró el archivo de credenciales de Firebase en la carpeta raíz.\n\n"
            f"Se buscó, por ejemplo, en:\n  {ejemplo_expect}\n\n"
            "Por favor:\n"
            "1. Descargue las credenciales desde Firebase Console (Service Account).\n"
            "2. Guárdelas en la carpeta raíz de la aplicación con el nombre:\n"
            "   firebase_equipos_key.json\n"
            "   (o 'firebase_equipos_key' sin extensión)\n"
            "3. Reinicie la aplicación.",
        )
        logger.error("Credenciales de Firebase no encontradas. Rutas comprobadas: %s", cred_candidates)
        sys.exit(1)

    # Normalizar ruta seleccionada
    selected_cred = os.path.abspath(selected_cred)
    logger.info("Usando credenciales de Firebase encontradas en: %s", selected_cred)

    # ---------- Inicializar firebase_admin tempranamente (si está disponible) ----------
    storage_manager = None
    storage_bucket = config.get("firebase", {}).get("storage_bucket")

    if fb_initialize_app is not None and fb_credentials is not None and fb_apps is not None:
        try:
            if not fb_apps:
                try:
                    cred = fb_credentials.Certificate(selected_cred)
                    init_kwargs = {}
                    if storage_bucket:
                        init_kwargs["storageBucket"] = storage_bucket
                    if init_kwargs:
                        fb_initialize_app(cred, init_kwargs)
                    else:
                        fb_initialize_app(cred)
                    logger.info("firebase_admin inicializado tempranamente con credenciales.")
                except Exception as e:
                    logger.warning("No se pudo inicializar firebase_admin tempranamente: %s", e)
            else:
                logger.debug("firebase_admin ya estaba inicializado, se omite inicialización temprana.")
        except Exception as e:
            logger.warning("Comprobación/Inicialización temprana de firebase_admin falló: %s", e)
    else:
        logger.debug("firebase_admin no disponible o no se pudieron importar helpers; se intentará inicializar desde FirebaseManager.")

    # ---------- Crear StorageManager (después de intentar inicializar firebase_admin) ----------
    if storage_bucket:
        try:
            # Pasamos bucket_name; StorageManager internamente debería usar firebase_admin si está inicializado
            storage_manager = StorageManager(bucket_name=storage_bucket)
            logger.info("Storage Manager inicializado correctamente con bucket: %s", storage_bucket)
        except Exception as e:
            logger.warning("No se pudo inicializar Storage Manager: %s", e)
            logger.warning("La funcionalidad de archivos en Storage estará deshabilitada")
            storage_manager = None
    else:
        logger.info("Storage bucket no configurado - funcionalidad de archivos deshabilitada")

    # ---------- Inicializar FirebaseManager (inyectando storage_manager) ----------
    try:
        firebase_manager = FirebaseManager(
            credentials_path=selected_cred,
            project_id=config["firebase"]["project_id"],
            storage_manager=storage_manager,
        )
        logger.info("Firebase Manager inicializado correctamente")
    except Exception as e:
        logger.exception("No se pudo inicializar Firebase Manager: %s", e)
        QMessageBox.critical(
            None,
            "Error de Firebase",
            "No se pudo conectar con Firebase:\n"
            f"{e}\n\n"
            "Verifique:\n"
            "1. Las credenciales son correctas\n"
            "2. Tiene conexión a Internet\n"
            "3. El proyecto de Firebase está activo",
        )
        sys.exit(1)

    # Inicializar Backup Manager
    try:
        backup_manager = BackupManager(
            ruta_backup=config["backup"]["ruta_backup_sqlite"],
            firebase_manager=firebase_manager,
        )
        logger.info("Backup Manager inicializado correctamente")
    except Exception as e:
        logger.warning(f"No se pudo inicializar Backup Manager: {e}")
        backup_manager = None

    # Iniciar la ventana principal
    try:
        window = AppGUI(
            firebase_manager=firebase_manager,
            storage_manager=storage_manager,
            backup_manager=backup_manager,
            config=config,
        )
        window.show()
        logger.info("Ventana principal creada y mostrada")
    except Exception as e:
        logger.exception("Error creando ventana principal AppGUI: %s", e)
        QMessageBox.critical(
            None,
            "Error al iniciar",
            f"No se pudo iniciar la interfaz gráfica:\n{e}",
        )
        sys.exit(1)

    # Configurar verificación de backups automáticos
    if backup_manager:
        def verificar_backup():
            """Verifica si es necesario crear un backup"""
            try:
                debe_backup = backup_manager.debe_crear_backup(
                    frecuencia=config["backup"]["frecuencia"],
                    hora_ejecucion=config["backup"]["hora_ejecucion"],
                    ultimo_backup=config["backup"].get("ultimo_backup"),
                )

                if debe_backup:
                    logger.info("Iniciando backup automático...")
                    if backup_manager.crear_backup():
                        # Actualizar configuración con la fecha del último backup
                        from datetime import datetime

                        config["backup"]["ultimo_backup"] = datetime.now().isoformat()
                        guardar_configuracion(config)
                        logger.info("Backup automático completado")
                    else:
                        logger.error("Error al crear backup automático")
            except Exception as e:
                logger.error(f"Error en verificación de backup: {e}")

        # Verificar al inicio y periódicamente
        QTimer.singleShot(5000, verificar_backup)  # 5 segundos después de iniciar

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