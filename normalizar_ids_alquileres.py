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


def _normalizar_campo_entero_a_string(data: dict, campo: str) -> tuple[bool, str]:
    """
    Si data[campo] existe y es numérico, lo convierte a string y devuelve (True, nuevo_valor).
    Si no hay que cambiar nada, devuelve (False, valor_actual_ignorando).
    """
    if campo not in data:
        return False, ""

    valor = data[campo]

    # Si ya es string, no cambiamos nada
    if isinstance(valor, str):
        return False, valor

    try:
        valor_int = int(valor)
        valor_str = str(valor_int)
        return True, valor_str
    except (ValueError, TypeError):
        logging.warning(f"{campo}={valor!r} no es numérico, se deja sin cambios.")
        return False, ""


def normalizar_ids_en_alquileres(db):
    """
    Normaliza los campos equipo_id y operador_id en la colección 'alquileres'
    para que todos sean strings.
    """
    logging.info("Iniciando normalización de equipo_id y operador_id en colección [alquileres]...")

    col_ref = db.collection("alquileres")
    docs = list(col_ref.stream())
    logging.info(f"Total documentos en alquileres: {len(docs)}")

    batch = db.batch()
    batch_count = 0
    total_actualizados = 0

    for doc in docs:
        data = doc.to_dict()
        cambios = {}

        # equipo_id
        cambiar_equipo, equipo_id_str = _normalizar_campo_entero_a_string(data, "equipo_id")
        if cambiar_equipo:
            cambios["equipo_id"] = equipo_id_str

        # operador_id (opcional pero recomendable)
        cambiar_operador, operador_id_str = _normalizar_campo_entero_a_string(data, "operador_id")
        if cambiar_operador:
            cambios["operador_id"] = operador_id_str

        if not cambios:
            continue

        batch.update(doc.reference, cambios)
        batch_count += 1
        total_actualizados += 1

        if batch_count >= 400:
            logging.info(f"Enviando batch de {batch_count} updates en [alquileres]...")
            batch.commit()
            batch = db.batch()
            batch_count = 0

    if batch_count > 0:
        logging.info(f"Enviando batch final de {batch_count} updates en [alquileres]...")
        batch.commit()

    logging.info(
        f"Normalización completada en [alquileres]. Documentos actualizados: {total_actualizados}"
    )


def main():
    db = init_firestore()

    try:
        normalizar_ids_en_alquileres(db)
        logging.info("Normalización de equipo_id/operador_id en alquileres finalizada.")
    except google_exceptions.ResourceExhausted as e:
        logging.error(f"Cuota de Firestore excedida: {e}")
    except Exception as e:
        logging.error(f"Error general en la normalización: {e}", exc_info=True)


if __name__ == "__main__":
    main()