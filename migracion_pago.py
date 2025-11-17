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

# --- LÓGICA DE MIGRACIÓN (SEGÚN TUS INSTRUCCIONES) ---
PROYECTO_ID = 8
CATEGORIA_ID = 11
TIPO_TRANSACCION = 'Gasto'

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
    """Añade campos 'ano' y 'mes' a un diccionario de datos si tiene 'fecha'."""
    try:
        fecha_obj = datetime.strptime(str(datos_limpios['fecha']), "%Y-%m-%d")
        datos_limpios['ano'] = fecha_obj.year
        datos_limpios['mes'] = fecha_obj.month
    except Exception:
        pass
    return datos_limpios

def migrar_pagos_operadores(proyecto_id, categoria_id, tipo):
    """
    Migra solo los Pagos a Operadores a la colección 'pagos_operadores'.
    """
    logging.info(f"--- Iniciando migración de [Pagos a Operadores] para Proyecto ID: {proyecto_id}, Categoría ID: {categoria_id} ---")
    coleccion_pagos_op = "pagos_operadores"
    try:
        query = "SELECT * FROM transacciones WHERE proyecto_id = ? AND categoria_id = ? AND tipo = ?"
        params = (proyecto_id, categoria_id, tipo)
        
        df_pagos_op = pd.read_sql(query, conn_sql, params=params)
        
        if df_pagos_op.empty:
            logging.warning(f"No se encontraron 'Pagos a Operadores' que coincidan con los criterios. Nada que migrar.")
            return

        batch_pagos = db_firestore.batch()
        count_pagos = 0
        total_pagos = 0
        
        for index, row in df_pagos_op.iterrows():
            datos = row.to_dict()
            datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
            datos_limpios = agregar_fecha_ano_mes(datos_limpios)
            
            # Usar el ID de la transacción como ID del documento
            doc_id = str(datos_limpios['id'])
            doc_ref = db_firestore.collection(coleccion_pagos_op).document(doc_id)
            
            batch_pagos.set(doc_ref, datos_limpios)
            count_pagos += 1
            total_pagos += 1
            
            if count_pagos >= BATCH_SIZE:
                batch_pagos, count_pagos = cometer_lote(batch_pagos, count_pagos, coleccion_pagos_op)
        
        cometer_lote(batch_pagos, count_pagos, coleccion_pagos_op)
        logging.info(f"--- Migración de [pagos_operadores] completada. Total: {total_pagos} docs. ---")

    except Exception as e:
        logging.error(f"Error durante la migración de pagos a operadores: {e}", exc_info=True)

def main():
    logging.info(f"========= INICIANDO SCRIPT DE MIGRACIÓN (SOLO PAGOS A OPERADORES) =========")
    
    migrar_pagos_operadores(PROYECTO_ID, CATEGORIA_ID, TIPO_TRANSACCION)
    
    conn_sql.close()
    logging.info("Conexión a SQLite cerrada.")
    logging.info("========= MIGRACIÓN DE PAGOS FINALIZADA =========")

if __name__ == "__main__":
    main()