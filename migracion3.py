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

# ¡NUEVO! Filtro por proyecto
PROYECTO_ID_FILTRO = 8 

# Configuración de logging
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
    """Función ayudante para enviar el lote y reiniciarlo."""
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
        pass # Ignorar si la fecha es inválida o no existe
    return datos_limpios

def migrar_coleccion_simple(coleccion_fs, tabla_sql, proyecto_id=None, global_table=False):
    """Migra tablas simples, con filtro de proyecto opcional."""
    logging.info(f"--- Iniciando migración de [{tabla_sql}] a [{coleccion_fs}] ---")
    try:
        query = f"SELECT * FROM {tabla_sql}"
        params = ()
        # Comprobar si la tabla tiene la columna 'proyecto_id'
        df_cols = pd.read_sql(f"PRAGMA table_info('{tabla_sql}')", conn_sql)
        tiene_proyecto_id = 'proyecto_id' in df_cols['name'].values

        if proyecto_id and not global_table and tiene_proyecto_id:
            query += f" WHERE proyecto_id = ?"
            params = (proyecto_id,)
        elif global_table:
            pass # No aplicar filtro de proyecto
        elif not tiene_proyecto_id and not global_table:
            logging.warning(f"Omitiendo [{tabla_sql}], no tiene 'proyecto_id' y no es global.")
            return
        elif not global_table:
            logging.warning(f"Omitiendo [{tabla_sql}], no es global y no tiene filtro de proyecto.")
            return

        df = pd.read_sql(query, conn_sql, params=params)
        
        if df.empty:
            logging.warning(f"No se encontraron datos en [{tabla_sql}]. Omitiendo.")
            return

        batch = db_firestore.batch()
        doc_count = 0
        total_migrados = 0
        for index, row in df.iterrows():
            datos = row.to_dict()
            datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
            
            # Usar el 'id' de SQL como ID de documento de Firestore
            doc_id = str(datos_limpios['id'])
            doc_ref = db_firestore.collection(coleccion_fs).document(doc_id)
            batch.set(doc_ref, datos_limpios)
            doc_count += 1
            total_migrados += 1
            
            if doc_count >= BATCH_SIZE:
                batch, doc_count = cometer_lote(batch, doc_count, coleccion_fs)
        
        cometer_lote(batch, doc_count, coleccion_fs)
        logging.info(f"--- Migración de [{coleccion_fs}] completada. Total: {total_migrados} docs. ---")
    except Exception as e:
        logging.error(f"Error durante la migración de [{coleccion_fs}]: {e}")


def migrar_mantenimientos_filtrado(proyecto_id):
    """Migra mantenimientos solo para los equipos del proyecto especificado."""
    logging.info(f"--- Iniciando migración de [mantenimientos] (filtrado por equipos del Proyecto {proyecto_id}) ---")
    try:
        df_equipos_migrados = pd.read_sql("SELECT id FROM equipos WHERE proyecto_id = ?", conn_sql, params=(proyecto_id,))
        ids_equipos_migrados = list(df_equipos_migrados['id'])
        
        if not ids_equipos_migrados:
            logging.warning("No se encontraron equipos, omitiendo mantenimientos.")
            return

        placeholders = ','.join('?' for _ in ids_equipos_migrados)
        df_mantenimientos = pd.read_sql(f"SELECT * FROM mantenimientos WHERE equipo_id IN ({placeholders})", conn_sql, params=tuple(ids_equipos_migrados))
        
        if df_mantenimientos.empty:
            logging.warning("No se encontraron mantenimientos para los equipos de este proyecto.")
            return

        batch_mant = db_firestore.batch()
        count_mant = 0
        total_mant = 0
        for index, row in df_mantenimientos.iterrows():
            datos = row.to_dict()
            datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
            doc_id = str(datos_limpios['id'])
            doc_ref = db_firestore.collection("mantenimientos").document(doc_id)
            batch_mant.set(doc_ref, datos_limpios)
            count_mant += 1
            total_mant += 1
            if count_mant >= BATCH_SIZE:
                batch_mant, count_mant = cometer_lote(batch_mant, count_mant, "mantenimientos")
        cometer_lote(batch_mant, count_mant, "mantenimientos")
        logging.info(f"--- Migración de [mantenimientos] completada. Total: {total_mant} docs. ---")
    except Exception as e:
        logging.error(f"Error migrando mantenimientos: {e}")

def migrar_alquileres_y_abonos(proyecto_id):
    """
    Migra Alquileres desde 'equipos_alquiler_meta' (pre-procesada).
    Migra Abonos a subcolección.
    """
    logging.info(f"--- Iniciando migración de [alquileres] (desde equipos_alquiler_meta) para Proyecto ID: {proyecto_id} ---")
    coleccion_alquileres = "alquileres"
    try:
        query_alquileres = "SELECT * FROM equipos_alquiler_meta WHERE proyecto_id = ?"
        df_alquileres = pd.read_sql(query_alquileres, conn_sql, params=(proyecto_id,))

        if df_alquileres.empty:
            logging.warning(f"No se encontraron Alquileres en [equipos_alquiler_meta] para el Proyecto {proyecto_id}.")
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
            ids_transacciones_alquiler.add(doc_id) # Guardar ID para migrar abonos
            
            doc_ref = db_firestore.collection(coleccion_alquileres).document(doc_id)
            batch_alquileres.set(doc_ref, datos_limpios)
            count_alquileres += 1
            total_alquileres += 1
            
            if count_alquileres >= BATCH_SIZE:
                batch_alquileres, count_alquileres = cometer_lote(batch_alquileres, count_alquileres, coleccion_alquileres)
        
        cometer_lote(batch_alquileres, count_alquileres, coleccion_alquileres)
        logging.info(f"--- Migración de [alquileres] completada. Total: {total_alquileres} docs. ---")

        # 5. MIGRAR LOS ABONOS (PAGOS) como subcolección
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


def migrar_gastos_y_pagos_operador(proyecto_id):
    """
    Migra Gastos a 'gastos'.
    Migra Pagos de Operador a 'pagos_operadores'.
    """
    logging.info(f"--- Iniciando migración de Gastos y Pagos a Operador para Proyecto ID: {proyecto_id} ---")
    try:
        # 1. OBTENER ID DE CATEGORÍA DE PAGO A OPERADOR
        cat_id_pago_operador = None
        try:
            cat_id_pago_operador = pd.read_sql(
                "SELECT id FROM categorias WHERE nombre = 'PAGO HRS OPERADOR'", 
                conn_sql
            ).iloc[0]['id']
            logging.info(f"ID de categoría 'PAGO HRS OPERADOR' encontrado: {cat_id_pago_operador}")
        except Exception:
            logging.warning("No se encontró la categoría 'PAGO HRS OPERADOR' en SQL.")

        # 2. MIGRAR 'pagos_operadores'
        if cat_id_pago_operador:
            coleccion_pagos_op = "pagos_operadores"
            query_pagos_op = "SELECT * FROM transacciones WHERE tipo = 'Gasto' AND categoria_id = ? AND proyecto_id = ?"
            df_pagos_op = pd.read_sql(query_pagos_op, conn_sql, params=(cat_id_pago_operador, proyecto_id))
            
            if not df_pagos_op.empty:
                batch_pagos = db_firestore.batch()
                count_pagos = 0
                total_pagos = 0
                for index, row in df_pagos_op.iterrows():
                    datos = row.to_dict()
                    datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
                    datos_limpios = agregar_fecha_ano_mes(datos_limpios)
                    doc_id = str(datos_limpios['id'])
                    doc_ref = db_firestore.collection(coleccion_pagos_op).document(doc_id)
                    batch_pagos.set(doc_ref, datos_limpios)
                    count_pagos += 1
                    total_pagos += 1
                    if count_pagos >= BATCH_SIZE:
                        batch_pagos, count_pagos = cometer_lote(batch_pagos, count_pagos, coleccion_pagos_op)
                cometer_lote(batch_pagos, count_pagos, coleccion_pagos_op)
                logging.info(f"Migración de [{coleccion_pagos_op}] completada. Total: {total_pagos} docs.")
            else:
                logging.info(f"No se encontraron 'Pagos a Operadores' para el Proyecto {proyecto_id}.")
        
        # 3. MIGRAR GASTOS (a 'gastos')
        logging.info("Migrando Gastos...")
        coleccion_gastos = "gastos"
        query_gastos = "SELECT * FROM transacciones WHERE tipo = 'Gasto' AND proyecto_id = ?"
        params_gastos = [proyecto_id]
        if cat_id_pago_operador:
            query_gastos += " AND (categoria_id != ? OR categoria_id IS NULL)"
            params_gastos.append(cat_id_pago_operador)
        
        df_gastos = pd.read_sql(query_gastos, conn_sql, params=tuple(params_gastos))

        if df_gastos.empty:
            logging.warning(f"No se encontraron Gastos (excluyendo pagos a op) para el Proyecto {proyecto_id}.")
            return
            
        batch_gastos = db_firestore.batch()
        count_gastos = 0
        total_gastos = 0
        for index, row in df_gastos.iterrows():
            datos = row.to_dict()
            datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
            datos_limpios = agregar_fecha_ano_mes(datos_limpios)
            doc_id = str(datos_limpios['id'])
            doc_ref = db_firestore.collection(coleccion_gastos).document(doc_id)
            batch_gastos.set(doc_ref, datos_limpios)
            count_gastos += 1
            total_gastos += 1
            if count_gastos >= BATCH_SIZE:
                batch_gastos, count_gastos = cometer_lote(batch_gastos, count_gastos, coleccion_gastos)
        
        cometer_lote(batch_gastos, count_gastos, coleccion_gastos)
        logging.info(f"--- Migración de [{coleccion_gastos}] completada. Total: {total_gastos} docs. ---")

    except Exception as e:
        logging.error(f"Error durante la migración de gastos: {e}", exc_info=True)


def main():
    logging.info(f"========= INICIANDO SCRIPT DE MIGRACIÓN V5 (MODELO SEPARADO) =========")
    logging.info(f"========= FILTRANDO TODO POR PROYECTO ID: {PROYECTO_ID_FILTRO} =========")
    
    # Migra colecciones filtrando por proyecto_id
    migrar_coleccion_simple(coleccion_fs="equipos", tabla_sql="equipos", proyecto_id=PROYECTO_ID_FILTRO)
    migrar_coleccion_simple(coleccion_fs="entidades", tabla_sql="equipos_entidades", proyecto_id=PROYECTO_ID_FILTRO)
    
    # Migra colecciones sin filtro de proyecto (son globales)
    migrar_coleccion_simple(coleccion_fs="categorias", tabla_sql="categorias", global_table=True)
    migrar_coleccion_simple(coleccion_fs="cuentas", tabla_sql="cuentas", global_table=True)
    migrar_coleccion_simple(coleccion_fs="subcategorias", tabla_sql="subcategorias", global_table=True) # Asume que existe
    
    # Migra mantenimientos filtrados por los equipos del proyecto
    migrar_mantenimientos_filtrado(PROYECTO_ID_FILTRO)
    
    # Migra Gastos y Pagos a Operador
    migrar_gastos_y_pagos_operador(PROYECTO_ID_FILTRO)
    
    # Migra Alquileres y Abonos
    migrar_alquileres_y_abonos(PROYECTO_ID_FILTRO)
    
    conn_sql.close()
    logging.info("Conexión a SQLite cerrada.")
    logging.info("========= MIGRACIÓN V5 FINALIZADA =========")

if __name__ == "__main__":
    main()