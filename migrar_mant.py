import sys
import csv
import logging
from pathlib import Path
from datetime import datetime, UTC

import firebase_admin
from firebase_admin import credentials, firestore

from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

# --- CONFIG ---
SERVICE_ACCOUNT_KEY = "firebase_credentials.json"
DEFAULT_COLLECTION = "mantenimientos"  # cambia si tu colección se llama distinto

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("migracion.mantenimientos.csv.gui")


def init_db(cred_path: str | None = None):
    cred_file = str(Path(cred_path or SERVICE_ACCOUNT_KEY).expanduser().resolve())
    if not Path(cred_file).exists():
        raise FileNotFoundError(f"No existe el archivo de credenciales: {cred_file}")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(cred_file))
    return firestore.client()


def parse_float(val):
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
    dlg = QFileDialog()
    dlg.setWindowTitle("Seleccionar CSV de Mantenimientos de Equipos")
    dlg.setNameFilter("CSV Files (*.csv);;All Files (*.*)")
    dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
    if dlg.exec():
        files = dlg.selectedFiles()
        if files:
            return Path(files[0]).resolve()
    return None


def confirmar_commit(app: QApplication, csv_path: Path, filas: int) -> bool:
    msg = QMessageBox()
    msg.setWindowTitle("Confirmar Migración de Mantenimientos")
    msg.setIcon(QMessageBox.Icon.Question)
    msg.setText(
        f"Se encontraron {filas} filas en el CSV:\n\n{csv_path}\n\n"
        "¿Deseas aplicar la migración a Firestore ahora?"
    )
    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    resp = msg.exec()
    return resp == QMessageBox.StandardButton.Yes


def main():
    app = QApplication(sys.argv)

    try:
        csv_path = seleccionar_csv(app)
        if not csv_path:
            QMessageBox.information(None, "Migración cancelada", "No se seleccionó ningún archivo CSV.")
            return
        if not csv_path.exists():
            QMessageBox.critical(None, "Error", f"No existe el archivo CSV:\n{csv_path}")
            return

        # Leer CSV
        rows = []
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        if not rows:
            QMessageBox.warning(None, "CSV vacío", f"El archivo CSV no contiene filas:\n{csv_path}")
            return

        logger.info(f"Filas leídas del CSV: {len(rows)}")

        if not confirmar_commit(app, csv_path, len(rows)):
            QMessageBox.information(None, "Migración cancelada", "No se aplicaron cambios en Firestore.")
            return

        # Inicializar Firestore
        try:
            db = init_db(SERVICE_ACCOUNT_KEY)
        except Exception as e:
            logger.error(f"Error inicializando Firebase: {e}", exc_info=True)
            QMessageBox.critical(None, "Error Firebase", f"No se pudo inicializar Firebase:\n{e}")
            return

        # Migrar
        batch = db.batch()
        batch_count = 0
        total = 0

        for i, row in enumerate(rows, start=1):
            mid = (row.get("id") or "").strip()
            if not mid:
                logger.warning(f"[{i}] Fila sin id, se omite.")
                continue

            fecha = (row.get("fecha") or "").strip()
            proyecto_id = str(row.get("proyecto_id") or "").strip()
            equipo_id = str(row.get("equipo_id") or "").strip()
            equipo_nombre = (row.get("equipo_nombre") or "").strip()

            data = {
                "fecha": fecha,
                "proyecto_id": proyecto_id,
                "equipo_id": equipo_id,
                "equipo_nombre": equipo_nombre,
                "descripcion": (row.get("descripcion") or "").strip(),
                "costo": parse_float(row.get("costo")) or 0.0,
                "horas_totales_equipo": parse_float(row.get("horas_totales_equipo")),
                "km_totales_equipo": parse_float(row.get("km_totales_equipo")),
                # compatibilidad con el modelo de DialogoMantenimiento:
                "tipo": None,
                "valor": parse_float(row.get("costo")) or 0.0,
                "odometro_horas": parse_float(row.get("horas_totales_equipo")),
                "odometro_km": parse_float(row.get("km_totales_equipo")),
                "lectura_es_horas": True,
                # metadatos de migración
                "migracion_origen": "sqlite_mantenimientos_csv_gui",
                "migracion_csv": csv_path.name,
                "migracion_fecha": datetime.now(UTC).isoformat(),
            }

            ref = db.collection(DEFAULT_COLLECTION).document(mid)
            batch.set(ref, data, merge=True)
            batch_count += 1
            total += 1

            if batch_count >= 400:
                batch.commit()
                logger.info(f"Batch commit de {batch_count} documentos")
                batch = db.batch()
                batch_count = 0

        if batch_count:
            batch.commit()
            logger.info(f"Batch final de {batch_count} documentos")

        logger.info(
            f"Migración de mantenimientos completada. Filas procesadas={total} | CSV={csv_path}"
        )
        QMessageBox.information(
            None,
            "Migración completada",
            f"Se migraron {total} mantenimientos desde:\n{csv_path}"
        )

    except Exception as e:
        logger.error(f"Error general en la migración de mantenimientos: {e}", exc_info=True)
        QMessageBox.critical(None, "Error", f"Error en la migración de mantenimientos:\n{e}")
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()