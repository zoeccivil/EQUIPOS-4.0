import sys
import os
import logging
import traceback
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from logic import DatabaseManager
from config_manager import cargar_configuracion, guardar_configuracion
from app_gui_qt import AppGUI

# Configurar logging global (archivo ya usado por el proyecto)
LOG_FILE = "progain.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def excepthook(exc_type, exc_value, exc_tb):
    """
    Manejador global de excepciones: registra la traza completa en el log
    y muestra un QMessageBox si es posible. Finalmente sale con código 1.
    """
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.exception("Excepción no controlada:\n%s", msg)

    # Intentar mostrar un dialogo si la app GUI está disponible.
    try:
        app = QApplication.instance()
        created_temp_app = False
        if app is None:
            # Crear una QApplication temporal para poder mostrar el QMessageBox
            app = QApplication([])  # no manipulamos sys.argv aquí
            created_temp_app = True

        QMessageBox.critical(None, "Error inesperado",
                             "Se produjo un error inesperado y la aplicación debe cerrarse.\n\n"
                             f"{exc_value}")

        if created_temp_app:
            # Forzar cierre de la app temporal que creamos
            app.quit()
    except Exception as show_err:
        # Si no se puede mostrar el QMessageBox, al menos imprimir en consola
        logger.exception("No se pudo mostrar QMessageBox en excepthook: %s", show_err)
        try:
            print("Error inesperado:", exc_value, file=sys.stderr)
        except Exception:
            pass

    # Llamar al excepthook original por si hay otras integraciones
    try:
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    except Exception:
        pass

    # Asegurar salida
    sys.exit(1)


def solicitar_bd_por_dialogo():
    """
    Muestra un QFileDialog para seleccionar una base de datos SQLite.
    Retorna la ruta seleccionada o None si el usuario cancela.
    """
    file_path, _ = QFileDialog.getOpenFileName(
        None,
        "Seleccionar base de datos",
        "",
        "Archivos SQLite (*.db);;Todos los archivos (*)"
    )
    return file_path or None


def main():
    # Registrar el manejador global de excepciones
    sys.excepthook = excepthook

    # Crear la aplicación Qt
    app = QApplication(sys.argv)

    # Cargar configuración (archivo gestionado por config_manager)
    try:
        config = cargar_configuracion()
    except Exception as e:
        logger.exception("No se pudo cargar la configuración: %s", e)
        config = {}

    if not config:
        # Crear configuración por defecto y guardarla
        config = {"database_path": "progain_database.db"}
        try:
            guardar_configuracion(config)
        except Exception as e:
            logger.exception("No se pudo guardar la configuración por defecto: %s", e)

    db_path = config.get("database_path", "progain_database.db")

    # Si la base de datos no existe, solicitarla con diálogo (mantener al usuario informado)
    while not os.path.isfile(db_path):
        QMessageBox.warning(None, "Base de datos no encontrada",
                            f"No se encontró la base de datos:\n{db_path}\n\nPor favor, selecciona una base de datos SQLite.")
        selected = solicitar_bd_por_dialogo()
        if not selected:
            QMessageBox.critical(None, "Sin base de datos", "No se seleccionó una base de datos. La aplicación se cerrará.")
            logger.error("No se seleccionó una base de datos al iniciar. Saliendo.")
            sys.exit(1)
        db_path = selected
        config["database_path"] = db_path
        try:
            guardar_configuracion(config)
        except Exception as e:
            logger.exception("No se pudo guardar la configuración actualizada: %s", e)

    # Inicializar el gestor de base de datos
    try:
        db_manager = DatabaseManager(db_path)
    except Exception as e:
        logger.exception("No se pudo inicializar DatabaseManager con %s: %s", db_path, e)
        QMessageBox.critical(None, "Error BD", f"No se pudo abrir la base de datos:\n{db_path}\n\n{e}")
        sys.exit(1)

    # Asegurar las tablas necesarias (migraciones mínimas)
    try:
        db_manager.crear_tablas_nucleo()
        db_manager.sembrar_datos_iniciales()
        db_manager.crear_tabla_equipos()
        db_manager.asegurar_tabla_alquiler_meta()
        db_manager.asegurar_tabla_pagos()
        db_manager.asegurar_tabla_mantenimientos()
        db_manager.asegurar_tablas_mantenimiento()
        db_manager.crear_indices()
        db_manager.asegurar_tabla_equipos_entidades()  # <-- AÑADE ESTA LÍNEA
    except Exception as e:
        logger.exception("Error creando/asegurando tablas: %s", e)
        QMessageBox.critical(None, "Error BD", f"No se pudo preparar la base de datos:\n{e}")
        sys.exit(1)

    # Iniciar la ventana principal
    try:
        window = AppGUI(db_manager, config)
        window.show()
    except Exception as e:
        logger.exception("Error creando ventana principal AppGUI: %s", e)
        QMessageBox.critical(None, "Error al iniciar", f"No se pudo iniciar la interfaz gráfica:\n{e}")
        sys.exit(1)

    # Ejecutar el loop de Qt y capturar excepciones inesperadas que puedan surgir aquí
    try:
        exit_code = app.exec()
        logger.info("Aplicación finalizada con exit_code=%s", exit_code)
        sys.exit(exit_code)
    except Exception as e:
        # Esto captura excepciones lanzadas fuera del control normal de Qt
        logger.exception("Error durante app.exec(): %s", e)
        # Reraise para que el excepthook las maneje (y muestre/registre)
        raise


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        # permitir salida normal con código
        raise
    except Exception as e:
        # Si ocurre algo aquí, el excepthook lo registrará; aserguramos que se imprima también.
        logger.exception("Fallo en main (capturado en __main__): %s", e)
        try:
            # Intentar mostrar un mensaje de error simple al usuario
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "Error crítico", f"Fallo crítico: {e}")
        except Exception:
            pass
        sys.exit(1)