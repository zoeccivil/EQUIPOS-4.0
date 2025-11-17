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
PROYECTO_ID_FILTRO = 8 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- INICIALIZACIÓN ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
        firebase_admin.initialize_app(cred)
    db_firestore = firestore.client()
    logging.info(f"Conexión a Firestore exitosa.")
    conn_sql = sqlite3.connect(DB_PATH)
    logging.info(f"Conexión a SQLite exitosa ({DB_PATH})")
except Exception as e:
    logging.error(f"Error al inicializar las conexiones: {e}")
    exit()

def cometer_lote(batch, doc_count, coleccion):
    if doc_count > 0:
        logging.info(f"Enviando lote de {doc_count} documentos a [{coleccion}]...")
        batch.commit()
    return db_firestore.batch(), 0

def agregar_fecha_ano_mes(datos_limpios):
    try:
        fecha_obj = datetime.strptime(str(datos_limpios['fecha']), "%Y-%m-%d")
        datos_limpios['ano'] = fecha_obj.year
        datos_limpios['mes'] = fecha_obj.month
    except Exception:
        pass
    return datos_limpios

def migrar_alquileres_con_join(proyecto_id):
    """
    ¡NUEVO (V7)!
    Migra Alquileres haciendo el JOIN completo para obtener TODOS los campos,
    incluyendo equipo_id.
    """
    logging.info(f"--- Iniciando migración de [alquileres] (CON JOIN) para Proyecto ID: {proyecto_id} ---")
    coleccion_alquileres = "alquileres"
    try:
        # Esta es la consulta "maestra" que tu app antigua usaba
        query_alquileres = """
            SELECT 
                t.id, t.fecha, t.descripcion, t.monto, t.pagado, t.comentario, 
                t.proyecto_id, t.tipo, t.equipo_id,
                m.cliente_id, m.operador_id, m.horas, m.precio_por_hora, 
                m.conduce, m.ubicacion, m.conduce_adjunto_path,
                m.transaccion_id
            FROM transacciones t 
            JOIN equipos_alquiler_meta m ON t.id = m.transaccion_id 
            WHERE t.proyecto_id = ? AND t.tipo = 'Ingreso'
        """
        df_alquileres = pd.read_sql(query_alquileres, conn_sql, params=(proyecto_id,))

        if df_alquileres.empty:
            logging.warning(f"No se encontraron Alquileres para el Proyecto {proyecto_id} usando el JOIN.")
            return

        batch_alquileres = db_firestore.batch()
        count_alquileres = 0
        total_alquileres = 0
        ids_transacciones_alquiler = set()

        for index, row in df_alquileres.iterrows():
            datos = row.to_dict()
            datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
            
            datos_limpios['pagado'] = bool(datos_limpios.get('pagado', 0))
            datos_limpios = agregar_fecha_ano_mes(datos_limpios)
            
            # El ID de documento será el 'transaccion_id' (UUID)
            doc_id = str(datos_limpios['transaccion_id'])
            ids_transacciones_alquiler.add(doc_id)
            
            doc_ref = db_firestore.collection(coleccion_alquileres).document(doc_id)
            batch_alquileres.set(doc_ref, datos_limpios)
            count_alquileres += 1
            total_alquileres += 1
            
            if count_alquileres >= BATCH_SIZE:
                batch_alquileres, count_alquileres = cometer_lote(batch_alquileres, count_alquileres, coleccion_alquileres)
        
        cometer_lote(batch_alquileres, count_alquileres, coleccion_alquileres)
        logging.info(f"--- Migración de [alquileres] (con JOIN) completada. Total: {total_alquileres} docs. ---")

        # Migrar Abonos (no cambia)
        logging.info("--- Iniciando migración de Abonos (pagos) a subcolecciones ---")
        if not ids_transacciones_alquiler:
            logging.warning("No se migraron alquileres, por lo tanto no se migran abonos.")
            return
        df_abonos_sql = pd.read_sql("SELECT * FROM pagos", conn_sql)
        df_abonos_filtrados = df_abonos_sql[df_abonos_sql['transaccion_id'].isin(ids_transacciones_alquiler)]
        if not df_abonos_filtrados.empty:
            batch_abonos = db_firestore.batch()
            count_abonos = 0
            total_abonos = 0
            for index, row in df_abonos_filtrados.iterrows():
                datos = row.to_dict()
                datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
                trans_id = str(datos_limpios['transaccion_id'])
                pago_id = str(datos_limpios['id'])
                doc_ref = db_firestore.collection(coleccion_alquileres).document(trans_id).collection("pagos").document(pago_id)
                batch_abonos.set(doc_ref, datos_limpios)
                count_abonos += 1
                total_abonos += 1
                if count_abonos >= BATCH_SIZE:
                    batch_abonos, count_abonos = cometer_lote(batch_abonos, count_abonos, "pagos (subcolección)")
            cometer_lote(batch_abonos, count_abonos, "pagos (subcolección)")
            logging.info(f"--- Migración de Abonos (pagos) completada. Total: {total_abonos} docs. ---")
        else:
            logging.info("No se encontraron Abonos (pagos) para los alquileres migrados.")
    except Exception as e:
        logging.error(f"Error durante la migración de alquileres: {e}", exc_info=True)


def main():
    logging.info(f"========= INICIANDO SCRIPT DE MIGRACIÓN V7 (JOIN Corregido) =========")
    logging.info(f"========= FILTRANDO TODO POR PROYECTO ID: {PROYECTO_ID_FILTRO} =========")
    
    # Este script ASUME que las otras colecciones (equipos, entidades, gastos, etc.)
    # ya fueron migradas correctamente por el script V6.
    # Este script SOLO migra la colección 'alquileres' (y sus abonos) correctamente.
    
    migrar_alquileres_con_join(PROYECTO_ID_FILTRO)
    
    conn_sql.close()
    logging.info("Conexión a SQLite cerrada.")
    logging.info("========= MIGRACIÓN V7 (SOLO ALQUILERES) FINALIZADA =========")

if __name__ == "__main__":
    main()