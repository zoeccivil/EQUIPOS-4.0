import sys
import csv
import logging
from pathlib import Path
from datetime import datetime, UTC

import firebase_admin
from firebase_admin import credentials, firestore

from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

# --- CONFIG GLOBAL ---
SERVICE_ACCOUNT_KEY = "firebase_credentials.json"
DEFAULT_COLLECTION = "pagos_operadores"  # colección destino


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("migracion.pagos_operadores.csv.gui")


def init_db(cred_path: str | None = None):
    """
    Inicializa Firebase Admin y devuelve el cliente de Firestore.
    """
    cred_file = str(Path(cred_path or SERVICE_ACCOUNT_KEY).expanduser().resolve())
    if not Path(cred_file).exists():
        raise FileNotFoundError(f"No existe el archivo de credenciales: {cred_file}")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(cred_file))
    return firestore.client()


def parse_float(val):
    """
    Convierte un valor a float, devolviendo None si está vacío o no es numérico.
    """
    if val is None:
        return None
    s = str(val).strip()
    if s == "":
        return None
    try:
        return float(s.replace(",", ""))
    except Exception:
        return None


def seleccionar_csv(app: QApplication) -> Path | None:
    """
    Abre un QFileDialog para seleccionar el archivo CSV.
    """
    dialog = QFileDialog()
    dialog.setWindowTitle("Seleccionar CSV de Pagos a Operadores")
    dialog.setNameFilter("CSV Files (*.csv);;All Files (*.*)")
    dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

    if dialog.exec():
        files = dialog.selectedFiles()
        if files:
            return Path(files[0]).resolve()
    return None


def confirmar_commit(app: QApplication, csv_path: Path, filas: int) -> bool:
    """
    Pregunta al usuario si desea aplicar cambios (commit).
    """
    msg = QMessageBox()
    msg.setWindowTitle("Confirmar Migración")
    msg.setIcon(QMessageBox.Icon.Question)
    msg.setText(
        f"Se encontraron {filas} filas en el CSV:\n\n{csv_path}\n\n"
        "¿Deseas aplicar la migración a Firestore ahora?"
    )
    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    resp = msg.exec()
    return resp == QMessageBox.StandardButton.Yes


def main():
    # Crear QApplication para usar QFileDialog y QMessageBox
    app = QApplication(sys.argv)

    try:
        # 1) Seleccionar CSV
        csv_path = seleccionar_csv(app)
        if not csv_path:
            QMessageBox.information(None, "Migración cancelada", "No se seleccionó ningún archivo CSV.")
            return

        if not csv_path.exists():
            QMessageBox.critical(None, "Error", f"No existe el archivo CSV:\n{csv_path}")
            return

        # 2) Leer CSV
        rows = []
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        if not rows:
            QMessageBox.warning(None, "CSV vacío", f"El archivo CSV no contiene filas:\n{csv_path}")
            return

        logger.info(f"Filas leídas del CSV: {len(rows)}")

        # 3) Confirmar commit
        if not confirmar_commit(app, csv_path, len(rows)):
            QMessageBox.information(None, "Migración cancelada", "No se aplicaron cambios en Firestore.")
            return

        # 4) Inicializar Firestore
        try:
            db = init_db(SERVICE_ACCOUNT_KEY)
        except Exception as e:
            logger.error(f"Error inicializando Firebase: {e}", exc_info=True)
            QMessageBox.critical(None, "Error Firebase", f"No se pudo inicializar Firebase:\n{e}")
            return

        # 5) Ejecutar migración con commit
        batch = db.batch()
        batch_count = 0
        total_procesadas = 0

        for i, row in enumerate(rows, start=1):
            pago_id = (row.get("id") or "").strip()
            if not pago_id:
                logger.warning(f"[{i}] Fila sin id, se omite.")
                continue

            fecha = (row.get("fecha") or "").strip()  # formato YYYY-MM-DD desde SQLite
            proyecto_id = str(row.get("proyecto_id") or "").strip()

            doc_data = {
                "fecha": fecha,
                "proyecto_id": proyecto_id,
                "cuenta_nombre": (row.get("cuenta") or "").strip(),
                "operador_nombre": (row.get("operador") or "").strip(),
                "equipo_nombre": (row.get("equipo") or "").strip(),
                "horas": parse_float(row.get("horas")),
                "monto": parse_float(row.get("monto")) or 0.0,
                "descripcion": (row.get("descripcion") or "").strip(),
                "comentario": (row.get("comentario") or "").strip(),
                # Metadatos de migración
                "migracion_origen": "sqlite_csv_gui",
                "migracion_csv": csv_path.name,
                "migracion_fecha": datetime.now(UTC).isoformat(),
            }

            logger.debug(f"[{i}] {pago_id} -> {doc_data}")
            total_procesadas += 1

            ref = db.collection(DEFAULT_COLLECTION).document(pago_id)
            batch.set(ref, doc_data, merge=True)
            batch_count += 1
            if batch_count >= 400:
                batch.commit()
                logger.info(f"Batch commit de {batch_count} documentos")
                batch = db.batch()
                batch_count = 0

        if batch_count:
            batch.commit()
            logger.info(f"Batch final de {batch_count} documentos")

        logger.info(
            f"Migración completada. Filas procesadas={total_procesadas} | CSV={csv_path}"
        )
        QMessageBox.information(
            None,
            "Migración completada",
            f"Se migraron {total_procesadas} pagos desde:\n{csv_path}"
        )

    except Exception as e:
        logger.error(f"Error general en la migración: {e}", exc_info=True)
        QMessageBox.critical(None, "Error", f"Error en la migración:\n{e}")
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()