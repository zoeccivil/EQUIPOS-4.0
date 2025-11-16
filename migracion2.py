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
    if not firebase_admin._apps: # Evitar inicializar dos veces
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


def migrar_coleccion_simple(coleccion_fs, tabla_sql, proyecto_id=None):
    """Migra tablas simples, con filtro de proyecto opcional."""
    logging.info(f"--- Iniciando migración de [{tabla_sql}] a [{coleccion_fs}] ---")
    try:
        query = f"SELECT * FROM {tabla_sql}"
        params = ()
        if proyecto_id:
            query += f" WHERE proyecto_id = ?"
            params = (proyecto_id,)
        # Para subcategorías que no tienen proyecto_id
        elif tabla_sql == 'subcategorias' and 'proyecto_id' in pd.read_sql("SELECT name FROM PRAGMA_TABLE_INFO('subcategorias')", conn_sql)['name'].values:
             query += f" WHERE proyecto_id = ?"
             params = (proyecto_id,) # Asumiendo que pueden tenerlo
        elif tabla_sql in ['categorias', 'cuentas', 'subcategorias']:
            pass # No aplicar filtro de proyecto

        df = pd.read_sql(query, conn_sql, params=params)
        
        if df.empty:
            logging.warning(f"No se encontraron datos en [{tabla_sql}] (Proyecto {proyecto_id if proyecto_id else 'Global'}). Omitiendo.")
            return

        batch = db_firestore.batch()
        doc_count = 0
        total_migrados = 0
        for index, row in df.iterrows():
            datos = row.to_dict()
            datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
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


def agregar_fecha_ano_mes(datos_limpios):
    """Añade campos 'ano' y 'mes' a un diccionario de datos si tiene 'fecha'."""
    try:
        fecha_obj = datetime.strptime(datos_limpios['fecha'], "%Y-%m-%d")
        datos_limpios['ano'] = fecha_obj.year
        datos_limpios['mes'] = fecha_obj.month
    except Exception:
        pass # Ignorar si la fecha es inválida o no existe
    return datos_limpios


def migrar_transacciones_y_pagos(proyecto_id):
    """
    Migra Alquileres (JOIN) y Gastos a 'transacciones'.
    Migra Pagos de Operador a 'pagos_operadores'.
    Migra Abonos a subcolecciones.
    Todo filtrado por proyecto_id.
    """
    logging.info(f"--- Iniciando migración de transacciones (unificada) para Proyecto ID: {proyecto_id} ---")
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

        batch_trans = db_firestore.batch()
        count_trans = 0
        total_trans = 0
        ids_transacciones_alquiler = set()

        # 2. MIGRAR 'pagos_operadores' (LOS QUE SÍ VAN SEPARADOS)
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
        
        # 3. MIGRAR GASTOS (a 'transacciones')
        logging.info("Migrando Gastos...")
        query_gastos = "SELECT * FROM transacciones WHERE tipo = 'Gasto' AND proyecto_id = ?"
        params_gastos = [proyecto_id]
        if cat_id_pago_operador:
            query_gastos += " AND (categoria_id != ? OR categoria_id IS NULL)"
            params_gastos.append(cat_id_pago_operador)
        
        df_gastos = pd.read_sql(query_gastos, conn_sql, params=tuple(params_gastos))
        
        for index, row in df_gastos.iterrows():
            datos = row.to_dict()
            datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
            datos_limpios = agregar_fecha_ano_mes(datos_limpios)
            doc_id = str(datos_limpios['id'])
            doc_ref = db_firestore.collection("transacciones").document(doc_id)
            batch_trans.set(doc_ref, datos_limpios)
            count_trans += 1
            total_trans += 1
            if count_trans >= BATCH_SIZE:
                batch_trans, count_trans = cometer_lote(batch_trans, count_trans, "transacciones (Gastos)")
        logging.info(f"Gastos procesados para lote: {len(df_gastos)}")

        # 4. MIGRAR ALQUILERES (JOIN a 'transacciones')
        logging.info("Migrando Alquileres (con JOIN)...")
        # Usamos el JOIN para combinar los datos.
        query_alquileres = """
            SELECT 
                t.id, t.fecha, t.descripcion, t.monto, t.pagado, t.comentario, t.proyecto_id, t.tipo,
                m.cliente_id, m.operador_id, m.horas, m.precio_por_hora, m.conduce, m.ubicacion,
                t.equipo_id
            FROM transacciones t 
            JOIN equipos_alquiler_meta m ON t.id = m.transaccion_id 
            WHERE t.proyecto_id = ? AND t.tipo = 'Ingreso'
        """
        df_alquileres = pd.read_sql(query_alquileres, conn_sql, params=(proyecto_id,))

        for index, row in df_alquileres.iterrows():
            datos = row.to_dict()
            datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
            datos_limpios['pagado'] = bool(datos_limpios.get('pagado', 0))
            datos_limpios = agregar_fecha_ano_mes(datos_limpios)
            doc_id = str(datos_limpios['id'])
            ids_transacciones_alquiler.add(doc_id) # Guardar ID para migrar abonos
            doc_ref = db_firestore.collection("transacciones").document(doc_id)
            batch_trans.set(doc_ref, datos_limpios)
            count_trans += 1
            total_trans += 1
            if count_trans >= BATCH_SIZE:
                batch_trans, count_trans = cometer_lote(batch_trans, count_trans, "transacciones (Alquileres)")
        logging.info(f"Alquileres procesados para lote: {len(df_alquileres)}")

        # Enviar lote final de transacciones
        cometer_lote(batch_trans, count_trans, "transacciones")
        logging.info(f"--- Migración de [transacciones] (Gastos y Alquileres) completada. Total: {total_trans} docs. ---")

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
                doc_ref = db_firestore.collection("transacciones").document(trans_id).collection("pagos").document(pago_id)
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
        logging.error(f"Error durante la migración unificada: {e}", exc_info=True)


def main():
    logging.info(f"========= INICIANDO SCRIPT DE MIGRACIÓN V4 (FILTRADO POR PROYECTO ID: {PROYECTO_ID_FILTRO}) =========")
    
    # Migra colecciones filtrando por proyecto_id
    migrar_coleccion_simple(coleccion_fs="equipos", tabla_sql="equipos", proyecto_id=PROYECTO_ID_FILTRO)
    migrar_coleccion_simple(coleccion_fs="entidades", tabla_sql="equipos_entidades", proyecto_id=PROYECTO_ID_FILTRO)
    
    # Migra colecciones sin filtro de proyecto (son globales)
    migrar_coleccion_simple(coleccion_fs="categorias", tabla_sql="categorias")
    migrar_coleccion_simple(coleccion_fs="cuentas", tabla_sql="cuentas")
    migrar_coleccion_simple(coleccion_fs="subcategorias", tabla_sql="subcategorias") # Asume que existe
    
    # Migra mantenimientos filtrados por los equipos del proyecto
    migrar_mantenimientos_filtrado(PROYECTO_ID_FILTRO)
    
    # Migra 'transacciones', 'pagos_operadores', y 'pagos' (subcolección) filtrado por proyecto
    migrar_transacciones_y_pagos(PROYECTO_ID_FILTRO)
    
    conn_sql.close()
    logging.info("========= MIGRACIÓN V4 FINALIZADA =========")

if __name__ == "__main__":
    main()