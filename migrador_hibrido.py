import sqlite3
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import logging
from datetime import datetime

# --- CONFIGURACIÓN ---
DB_PATH = "progain_database.db"
SERVICE_ACCOUNT_KEY = "firebase_credentials.json"
BATCH_SIZE = 499
PROYECTO_ID_FILTRO = 8  # ajusta este ID al proyecto que quieres migrar

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- INICIALIZACIÓN ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
        firebase_admin.initialize_app(cred)
    db_firestore = firestore.client()
    logging.info("Conexión a Firestore exitosa.")
    conn_sql = sqlite3.connect(DB_PATH)
    conn_sql.row_factory = sqlite3.Row
    logging.info(f"Conexión a SQLite exitosa ({DB_PATH})")
except Exception as e:
    logging.error(f"Error al inicializar las conexiones: {e}", exc_info=True)
    exit(1)


def cometer_lote(batch, doc_count, coleccion):
    if doc_count > 0:
        logging.info(f"Enviando lote de {doc_count} documentos a [{coleccion}]...")
        batch.commit()
    return db_firestore.batch(), 0


def agregar_fecha_ano_mes(fecha_str: str, datos: dict) -> dict:
    """
    Añade campos 'ano' y 'mes' a un diccionario de datos a partir de un string fecha "YYYY-MM-DD".
    """
    try:
        fecha_obj = datetime.strptime(str(fecha_str), "%Y-%m-%d")
        datos["ano"] = fecha_obj.year
        datos["mes"] = fecha_obj.month
    except Exception:
        pass
    return datos


def migrar_alquileres_con_join(proyecto_id):
    """
    YA EXISTENTE EN TU V7:
    Migra Alquileres haciendo el JOIN completo para obtener TODOS los campos,
    incluyendo equipo_id, cliente_id, operador_id, etc.
    """
    logging.info(f"--- Iniciando migración de [alquileres] (CON JOIN) para Proyecto ID: {proyecto_id} ---")
    coleccion_alquileres = "alquileres"
    try:
        query_alquileres = """
            SELECT 
                T.id, T.fecha, T.descripcion, T.monto, T.pagado, T.comentario, 
                T.proyecto_id, T.tipo, T.equipo_id,
                META.cliente_id, META.operador_id, META.horas, META.precio_por_hora, 
                META.conduce, META.ubicacion, META.conduce_adjunto_path,
                META.transaccion_id
            FROM transacciones T 
            JOIN equipos_alquiler_meta META ON T.id = META.transaccion_id 
            WHERE T.proyecto_id = ? AND T.tipo = 'Ingreso'
        """
        df_alquileres = pd.read_sql(query_alquileres, conn_sql, params=(proyecto_id,))

        if df_alquileres.empty:
            logging.warning(f"No se encontraron Alquileres para el Proyecto {proyecto_id} usando el JOIN.")
            return set()

        batch_alquileres = db_firestore.batch()
        count_alquileres = 0
        total_alquileres = 0
        ids_transacciones_alquiler = set()

        for _, row in df_alquileres.iterrows():
            datos = dict(row)
            datos_limpios = {k: v for k, v in datos.items() if v is not None}

            # asegurar tipos
            datos_limpios["pagado"] = bool(datos_limpios.get("pagado", 0))
            fecha_str = str(datos_limpios.get("fecha", ""))
            datos_limpios = agregar_fecha_ano_mes(fecha_str, datos_limpios)

            # El ID de documento será el 'transaccion_id' (UUID)
            doc_id = str(datos_limpios["transaccion_id"])
            ids_transacciones_alquiler.add(doc_id)

            doc_ref = db_firestore.collection(coleccion_alquileres).document(doc_id)
            batch_alquileres.set(doc_ref, datos_limpios)
            count_alquileres += 1
            total_alquileres += 1

            if count_alquileres >= BATCH_SIZE:
                batch_alquileres, count_alquileres = cometer_lote(
                    batch_alquileres, count_alquileres, coleccion_alquileres
                )

        cometer_lote(batch_alquileres, count_alquileres, coleccion_alquileres)
        logging.info(
            f"--- Migración de [alquileres] (con JOIN) completada. Total: {total_alquileres} docs. ---"
        )
        return ids_transacciones_alquiler

    except Exception as e:
        logging.error(f"Error durante la migración de alquileres: {e}", exc_info=True)
        return set()


def migrar_pagos_y_abonos(proyecto_id, ids_transacciones_alquiler):
    """
    Migra pagos de la tabla 'pagos' a:
    - subcolección 'alquileres/{transaccion_id}/pagos/{pago_id}'
    - colección plana 'abonos/{pago_id}' (modelo híbrido)
    """
    logging.info(f"--- Iniciando migración de pagos y abonos para proyecto {proyecto_id} ---")

    if not ids_transacciones_alquiler:
        logging.warning("No hay transacciones de alquiler migradas; no se migran pagos/abonos.")
        return

    # Leer pagos + data de transacciones + cliente_id en una sola consulta
    query = """
        SELECT 
            P.id AS pago_id,
            P.transaccion_id,
            P.cuenta_id,
            P.fecha,
            P.monto,
            P.comentario,
            T.proyecto_id,
            T.descripcion AS transaccion_descripcion,
            META.cliente_id
        FROM pagos P
        JOIN transacciones T ON P.transaccion_id = T.id
        JOIN equipos_alquiler_meta META ON T.id = META.transaccion_id
        WHERE T.proyecto_id = ?
          AND P.transaccion_id IN (
                SELECT id FROM transacciones WHERE proyecto_id = ? AND tipo = 'Ingreso'
          )
    """
    df = pd.read_sql(query, conn_sql, params=(proyecto_id, proyecto_id))

    if df.empty:
        logging.info("No se encontraron pagos para migrar.")
        return

    batch_pagos = db_firestore.batch()
    batch_abonos = db_firestore.batch()
    count_pagos = 0
    count_abonos = 0
    total_pagos = 0
    total_abonos = 0

    for _, row in df.iterrows():
        datos = dict(row)
        datos_limpios = {k: v for k, v in datos.items() if v is not None}

        pago_id = str(datos_limpios["pago_id"])
        trans_id = str(datos_limpios["transaccion_id"])

        # --- Subcolección pagos dentro de alquileres ---
        doc_ref_pago = (
            db_firestore.collection("alquileres")
            .document(trans_id)
            .collection("pagos")
            .document(pago_id)
        )
        batch_pagos.set(doc_ref_pago, datos_limpios)
        count_pagos += 1
        total_pagos += 1

        # --- Documento plano en 'abonos' ---
        abono_doc = {
            "id": pago_id,
            "transaccion_id": trans_id,
            "cliente_id": datos_limpios.get("cliente_id"),
            "proyecto_id": datos_limpios.get("proyecto_id"),
            "cuenta_id": datos_limpios.get("cuenta_id"),
            "fecha": str(datos_limpios.get("fecha")),
            "monto": float(datos_limpios.get("monto") or 0.0),
            "comentario": datos_limpios.get("comentario"),
            "transaccion_descripcion": datos_limpios.get("transaccion_descripcion"),
            "fecha_creacion": datetime.now().isoformat(),
            "fecha_modificacion": datetime.now().isoformat(),
        }
        abono_doc = agregar_fecha_ano_mes(abono_doc["fecha"], abono_doc)

        doc_ref_abono = db_firestore.collection("abonos").document(pago_id)
        batch_abonos.set(doc_ref_abono, abono_doc)
        count_abonos += 1
        total_abonos += 1

        # commit por lotes
        if count_pagos >= BATCH_SIZE:
            batch_pagos, count_pagos = cometer_lote(batch_pagos, count_pagos, "alquileres/*/pagos")
        if count_abonos >= BATCH_SIZE:
            batch_abonos, count_abonos = cometer_lote(batch_abonos, count_abonos, "abonos")

    # commit final
    cometer_lote(batch_pagos, count_pagos, "alquileres/*/pagos")
    cometer_lote(batch_abonos, count_abonos, "abonos")

    logging.info(f"--- Migración de subcolección pagos completada. Total: {total_pagos} docs. ---")
    logging.info(f"--- Migración de colección abonos completada. Total: {total_abonos} docs. ---")


def main():
    logging.info("========= INICIANDO SCRIPT DE MIGRACIÓN HÍBRIDO (ALQUILERES + PAGOS + ABONOS) =========")
    logging.info(f"========= FILTRANDO TODO POR PROYECTO ID: {PROYECTO_ID_FILTRO} =========")

    # 1) Migrar alquileres y obtener los IDs de transacciones de ingresos
    ids_transacciones_alquiler = migrar_alquileres_con_join(PROYECTO_ID_FILTRO)

    # 2) Migrar pagos a subcolecciones y a colección plana abonos
    migrar_pagos_y_abonos(PROYECTO_ID_FILTRO, ids_transacciones_alquiler)

    conn_sql.close()
    logging.info("Conexión a SQLite cerrada.")
    logging.info("========= MIGRACIÓN HÍBRIDA FINALIZADA =========")


if __name__ == "__main__":
    main()