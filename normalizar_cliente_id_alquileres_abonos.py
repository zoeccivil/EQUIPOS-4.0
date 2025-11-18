import firebase_admin
from firebase_admin import credentials, firestore
import logging
from google.api_core import exceptions as google_exceptions

# === CONFIGURACIÓN ===
SERVICE_ACCOUNT_KEY = "firebase_credentials.json"  # ajusta la ruta si es distinta

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def init_firestore():
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def normalizar_cliente_id_en_coleccion(db, coleccion: str):
    """
    Recorre todos los documentos de la colección dada y normaliza el campo
    'cliente_id' a string.
    """
    logging.info(f"Iniciando normalización de cliente_id en colección [{coleccion}]...")

    col_ref = db.collection(coleccion)
    docs = list(col_ref.stream())
    logging.info(f"Total documentos en {coleccion}: {len(docs)}")

    batch = db.batch()
    batch_count = 0
    total_actualizados = 0

    for doc in docs:
        data = doc.to_dict()
        if "cliente_id" not in data:
            continue

        cliente_id = data["cliente_id"]

        # Si ya es string, lo dejamos
        if isinstance(cliente_id, str):
            continue

        try:
            # Intentamos convertir a int primero, luego a string limpia
            cliente_id_int = int(cliente_id)
            cliente_id_str = str(cliente_id_int)
        except (ValueError, TypeError):
            # Si no se puede convertir, lo dejamos como está
            logging.warning(
                f"{coleccion}/{doc.id}: cliente_id ({cliente_id}) no es numérico, se deja sin cambios."
            )
            continue

        # Actualizar solo si cambia
        batch.update(doc.reference, {"cliente_id": cliente_id_str})
        batch_count += 1
        total_actualizados += 1

        if batch_count >= 400:
            logging.info(f"Enviando batch de {batch_count} updates en [{coleccion}]...")
            batch.commit()
            batch = db.batch()
            batch_count = 0

    if batch_count > 0:
        logging.info(f"Enviando batch final de {batch_count} updates en [{coleccion}]...")
        batch.commit()

    logging.info(
        f"Normalización completada en [{coleccion}]. Documentos actualizados: {total_actualizados}"
    )


def main():
    db = init_firestore()

    try:
        normalizar_cliente_id_en_coleccion(db, "alquileres")
        normalizar_cliente_id_en_coleccion(db, "abonos")
        logging.info("Normalización de cliente_id en alquileres y abonos finalizada.")
    except google_exceptions.ResourceExhausted as e:
        logging.error(f"Cuota de Firestore excedida: {e}")
    except Exception as e:
        logging.error(f"Error general en la normalización: {e}", exc_info=True)


if __name__ == "__main__":
    main()