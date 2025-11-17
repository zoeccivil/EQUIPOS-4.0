import sqlite3
import os
import uuid
import logging
import calendar
from datetime import datetime, date
import uuid # Asegúrate de que esta línea esté al inicio de tu archivo logic.py


# Configura logging para archivo y consola
logging.basicConfig(
    filename='progain.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="progain_database.db"):
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    # --- UTILIDADES GENERALES ---
    def fetchall(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(sql, params)
        rows = [dict(row) for row in cur.fetchall()]
        cur.close()
        return rows

    def fetchone(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None

    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(sql, params)
        self._conn.commit()
        rowid = cur.lastrowid
        cur.close()
        return rowid

    # --- CREACIÓN Y MIGRACIÓN DE TABLAS ---
    def crear_tablas_nucleo(self):
        logger.info("[INFO] Asegurando que las tablas núcleo existan...")
        sqls = [
            """
            CREATE TABLE IF NOT EXISTS proyectos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                descripcion TEXT,
                moneda TEXT DEFAULT 'RD$',
                cuenta_principal TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS cuentas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                tipo_cuenta TEXT,
                UNIQUE(nombre, tipo_cuenta)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS equipos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proyecto_id INTEGER,
                nombre TEXT NOT NULL,
                marca TEXT,
                modelo TEXT,
                categoria TEXT,
                equipo TEXT,
                activo INTEGER DEFAULT 1
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS transacciones (
                id TEXT PRIMARY KEY,
                proyecto_id INTEGER,
                cuenta_id INTEGER,
                categoria_id INTEGER,
                equipo_id INTEGER,
                tipo TEXT NOT NULL CHECK(tipo IN ('Ingreso', 'Gasto')),
                descripcion TEXT,
                comentario TEXT,
                monto REAL NOT NULL,
                fecha DATE NOT NULL,
                pagado INTEGER DEFAULT 0,
                cliente_id INTEGER,
                operador_id INTEGER,
                conduce TEXT,
                ubicacion TEXT,
                horas REAL,
                precio_por_hora REAL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS proyecto_cuentas (
                proyecto_id INTEGER,
                cuenta_id INTEGER,
                is_principal INTEGER DEFAULT 0,
                PRIMARY KEY (proyecto_id, cuenta_id)
            )
            """
        ]
        for sql in sqls:
            self._conn.execute(sql)
        self._conn.commit()

    # --- OBTENCIÓN DE DATOS ---
    def obtener_proyectos(self):
        return self.fetchall("SELECT * FROM proyectos ORDER BY nombre")

    def obtener_proyecto_por_id(self, proyecto_id):
        return self.fetchone("SELECT * FROM proyectos WHERE id = ?", (proyecto_id,))

    def obtener_entidades_por_tipo(self, proyecto_id=None):
        if proyecto_id is not None:
            return self.fetchall(
                "SELECT * FROM equipos WHERE proyecto_id=? AND activo=1",
                (proyecto_id,)
            )
        else:
            return self.fetchall(
                "SELECT * FROM equipos WHERE activo=1"
            )



    def obtener_equipo_por_id(self, equipo_id):
        return self.fetchone(
            "SELECT * FROM equipos WHERE id = ?",
            (equipo_id,)
        )

    # --- GUARDAR Y ELIMINAR EQUIPOS ---
    def guardar_equipo(self, datos, equipo_id=None):
        if equipo_id:
            query = """
                UPDATE equipos SET
                    nombre=?, marca=?, modelo=?, categoria=?, equipo=?, activo=?
                WHERE id=?
            """
            self.execute(query, (
                datos["nombre"], datos["marca"], datos["modelo"],
                datos["categoria"], datos["equipo"], datos["activo"], equipo_id
            ))
        else:
            query = """
                INSERT INTO equipos (proyecto_id, nombre, marca, modelo, categoria, equipo, activo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            self.execute(query, (
                datos["proyecto_id"], datos["nombre"], datos["marca"],
                datos["modelo"], datos["categoria"], datos["equipo"], datos["activo"]
            ))
        return True

    def eliminar_equipo(self, equipo_id):
        try:
            self.execute("DELETE FROM equipos WHERE id = ?", (equipo_id,))
            return True
        except Exception as e:
            logger.error(f"[ERROR] {e}")
            return False

    # --- TRANSACCIONES ---
    def obtener_transaccion_por_id(self, transaccion_id):
        return self.fetchone("SELECT * FROM transacciones WHERE id = ?", (transaccion_id,))

    # --- ABONOS/PAGOS ---
    def asegurar_tabla_pagos(self):
        query = """
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaccion_id TEXT NOT NULL,
            cuenta_id INTEGER NOT NULL,
            fecha DATE NOT NULL,
            monto REAL NOT NULL,
            comentario TEXT
        )
        """
        self.execute(query)

    # --- MANTENIMIENTO ---
    def asegurar_tabla_mantenimientos(self):
        query = """
            CREATE TABLE IF NOT EXISTS mantenimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipo_id INTEGER NOT NULL,
                fecha TEXT,
                descripcion TEXT,
                tipo TEXT,
                valor REAL,
                odometro_horas REAL,
                odometro_km REAL,
                notas TEXT,
                proximo_tipo TEXT,
                proximo_valor REAL,
                proximo_fecha TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """
        self.execute(query)

    def registrar_mantenimiento(self, datos):
        return self.execute(
            """
            INSERT INTO mantenimientos
                (equipo_id, fecha, descripcion, tipo, valor, odometro_horas, odometro_km, notas,
                 proximo_tipo, proximo_valor, proximo_fecha, created_at)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                int(datos["equipo_id"]),
                datos.get("fecha"),
                (datos.get("descripcion") or "").strip(),
                (datos.get("tipo") or "").strip() or None,
                float(str(datos.get("valor")).replace(",", ".")) if datos.get("valor") not in (None, "") else None,
                float(str(datos.get("odometro_horas")).replace(",", ".")) if datos.get("odometro_horas") not in (None, "") else None,
                float(str(datos.get("odometro_km")).replace(",", ".")) if datos.get("odometro_km") not in (None, "") else None,
                (datos.get("notas") or "").strip() or None,
                (datos.get("proximo_tipo") or "").strip() or None,
                float(str(datos.get("proximo_valor")).replace(",", ".")) if datos.get("proximo_valor") not in (None, "") else None,
                datos.get("proximo_fecha")
            )
        )

    def actualizar_mantenimiento(self, datos):
        return self.execute(
            """
            UPDATE mantenimientos
            SET fecha = ?, descripcion = ?, tipo = ?, valor = ?, odometro_horas = ?, odometro_km = ?, notas = ?,
                proximo_tipo = ?, proximo_valor = ?, proximo_fecha = ?
            WHERE id = ?
            """,
            (
                datos.get("fecha"),
                (datos.get("descripcion") or "").strip(),
                (datos.get("tipo") or "").strip() or None,
                float(str(datos.get("valor")).replace(",", ".")) if datos.get("valor") not in (None, "") else None,
                float(str(datos.get("odometro_horas")).replace(",", ".")) if datos.get("odometro_horas") not in (None, "") else None,
                float(str(datos.get("odometro_km")).replace(",", ".")) if datos.get("odometro_km") not in (None, "") else None,
                (datos.get("notas") or "").strip() or None,
                (datos.get("proximo_tipo") or "").strip() or None,
                float(str(datos.get("proximo_valor")).replace(",", ".")) if datos.get("proximo_valor") not in (None, "") else None,
                datos.get("proximo_fecha"),
                int(datos["id"])
            )
        )

    def eliminar_mantenimiento(self, mantenimiento_id):
        self.execute("DELETE FROM mantenimientos WHERE id = ?", (mantenimiento_id,))
        return True

    def obtener_mantenimiento_por_id(self, mantenimiento_id):
        return self.fetchone(
            """
            SELECT id, equipo_id, fecha, descripcion, tipo, valor, odometro_horas, odometro_km,
                   notas, proximo_tipo, proximo_valor, proximo_fecha, created_at
            FROM mantenimientos
            WHERE id = ?
            """,
            (mantenimiento_id,)
        )

    # --- DASHBOARD Y RESÚMENES ---
    def obtener_kpis_dashboard(self, proyecto_id, anio, mes, equipo_id=None):
        try:
            num_dias = calendar.monthrange(anio, mes)[1]
            inicio_mes = f"{anio}-{mes:02d}-01"
            fin_mes = f"{anio}-{mes:02d}-{num_dias}"
        except ValueError:
            return {}

        where_mes = " WHERE T.proyecto_id = ? AND T.fecha BETWEEN ? AND ? "
        params_mes = [proyecto_id, inicio_mes, fin_mes]
        if equipo_id:
            where_mes += " AND T.equipo_id = ? "
            params_mes.append(equipo_id)

        query_ing_gas = f"""
            SELECT
                SUM(CASE WHEN T.tipo = 'Ingreso' THEN T.monto ELSE 0 END) as ingresos,
                SUM(CASE WHEN T.tipo = 'Gasto' THEN T.monto ELSE 0 END) as gastos
            FROM transacciones T
            {where_mes}
        """
        res_ing_gas = self.fetchone(query_ing_gas, tuple(params_mes))

        query_pendiente = "SELECT SUM(monto) as total_pendiente FROM transacciones WHERE proyecto_id = ? AND tipo = 'Ingreso' AND pagado = 0"
        res_pendiente = self.fetchone(query_pendiente, (proyecto_id,))

        query_equipo = f"""
            SELECT EQ.nombre, SUM(T.monto) as total_generado
            FROM transacciones T
            JOIN equipos EQ ON T.equipo_id = EQ.id
            {where_mes} AND T.tipo = 'Ingreso'
            GROUP BY EQ.nombre
            ORDER BY total_generado DESC
            LIMIT 1
        """
        res_equipo = self.fetchone(query_equipo, tuple(params_mes))

        where_meta = " WHERE META.proyecto_id = ? AND T.fecha BETWEEN ? AND ? "
        params_meta = [proyecto_id, inicio_mes, fin_mes]
        if equipo_id:
            where_meta += " AND T.equipo_id = ? "
            params_meta.append(equipo_id)

        query_operador = f"""
            SELECT OPE.nombre, SUM(META.horas) as total_horas
            FROM equipos_alquiler_meta META
            JOIN equipos_entidades OPE ON META.operador_id = OPE.id
            JOIN transacciones T ON META.transaccion_id = T.id
            {where_meta}
            GROUP BY OPE.nombre
            ORDER BY total_horas DESC
            LIMIT 1
        """
        res_operador = self.fetchone(query_operador, tuple(params_meta))

        kpis = {
            'ingresos_mes': res_ing_gas['ingresos'] if res_ing_gas and res_ing_gas['ingresos'] else 0.0,
            'gastos_mes': res_ing_gas['gastos'] if res_ing_gas and res_ing_gas['gastos'] else 0.0,
            'saldo_pendiente': res_pendiente['total_pendiente'] if res_pendiente and res_pendiente['total_pendiente'] else 0.0,
            'top_equipo_nombre': res_equipo['nombre'] if res_equipo else "N/A",
            'top_equipo_monto': res_equipo['total_generado'] if res_equipo else 0.0,
            'top_operador_nombre': res_operador['nombre'] if res_operador else "N/A",
            'top_operador_horas': res_operador['total_horas'] if res_operador else 0.0
        }
        return kpis


    def sembrar_datos_iniciales(self):
        """
        Crea un proyecto por defecto si la tabla está vacía.
        """
        conteo = self.fetchone("SELECT COUNT(*) as c FROM proyectos")
        if conteo and conteo['c'] == 0:
            self.execute("INSERT OR IGNORE INTO proyectos (nombre) VALUES (?)", ("EQUIPOS PESADOS ZOEC",))


    def crear_tabla_equipos(self):
        """Crea la tabla de equipos si no existe (proxy para compatibilidad)."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS equipos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proyecto_id INTEGER,
                nombre TEXT NOT NULL,
                marca TEXT,
                modelo TEXT,
                categoria TEXT,
                equipo TEXT,
                activo INTEGER DEFAULT 1
            )
        """)
        self._conn.commit()

    def asegurar_tabla_alquiler_meta(self):
        """Crea la tabla equipos_alquiler_meta si no existe."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS equipos_alquiler_meta (
                transaccion_id TEXT PRIMARY KEY,
                proyecto_id INTEGER NOT NULL,
                cliente_id INTEGER,
                operador_id INTEGER,
                horas REAL,
                precio_por_hora REAL,
                conduce TEXT,
                ubicacion TEXT,
                conduce_adjunto_path TEXT
            )
        """)
        self._conn.commit()

    def asegurar_tablas_mantenimiento(self):
        """Crea tablas y/o columnas para mantenimiento avanzado (equipos_mantenimiento)."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS equipos_mantenimiento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipo_id INTEGER NOT NULL,
                fecha_mantenimiento DATE NOT NULL,
                costo REAL DEFAULT 0,
                descripcion TEXT NOT NULL,
                fecha_proximo DATE,
                horas_equipo_en_mantenimiento REAL,
                km_equipo_en_mantenimiento REAL
            )
        """)
        self._conn.commit()

    def crear_indices(self):
        indices = [
            "CREATE INDEX IF NOT EXISTS ix_equipos_proyecto_id ON equipos(proyecto_id)",
            "CREATE INDEX IF NOT EXISTS ix_transacciones_equipo_id ON transacciones(equipo_id)",
            "CREATE INDEX IF NOT EXISTS ix_mantenimientos_equipo_id ON mantenimientos(equipo_id)",
        ]
        for sql in indices:
            self._conn.execute(sql)
        self._conn.commit()


    def obtener_entidades_equipo_por_tipo(self, proyecto_id, tipo_entidad):
        """
        Obtiene todas las entidades (Clientes u Operadores) de un proyecto específico.
        Devuelve TODOS los campos incluyendo telefono y cedula.
        """
        query = """
            SELECT id, nombre, tipo, proyecto_id, activo, telefono, cedula
            FROM equipos_entidades 
            WHERE proyecto_id = ? AND tipo = ? 
            ORDER BY nombre
        """
        return self.fetchall(query, (proyecto_id, tipo_entidad))


    def obtener_equipos(self, proyecto_id):
        return self.fetchall(
            "SELECT id, nombre, mantenimiento_trigger_tipo, mantenimiento_trigger_valor, marca, modelo, categoria, subcategoria, activo FROM equipos WHERE proyecto_id = ? AND activo=1 ORDER BY nombre",
            (proyecto_id,)
        )

    def obtener_fecha_primera_transaccion(self, proyecto_id):
        row = self.fetchone(
            "SELECT MIN(fecha) as primera_fecha FROM transacciones WHERE proyecto_id = ?",
            (proyecto_id,)
        )
        if row and row["primera_fecha"]:
            return row["primera_fecha"]
        return None


    def obtener_transacciones_por_proyecto(self, proyecto_id, filtros=None):
        # Esta es tu función principal, está correcta.
        query = """
            SELECT 
                T.id, T.fecha, T.conduce, T.ubicacion, T.horas, T.precio_por_hora,
                T.monto, T.pagado, T.conduce_adjunto_path,
                EQ.nombre AS equipo_nombre,
                CLI.nombre AS cliente_nombre,
                OPE.nombre AS operador_nombre
            FROM transacciones T
            LEFT JOIN equipos EQ ON T.equipo_id = EQ.id
            LEFT JOIN equipos_entidades CLI ON T.cliente_id = CLI.id
            LEFT JOIN equipos_entidades OPE ON T.operador_id = OPE.id
            WHERE T.proyecto_id = :proyecto_id AND T.tipo = 'Ingreso'
        """
        params = {'proyecto_id': proyecto_id}
        if filtros:
            if filtros.get('cliente_id'):
                query += " AND T.cliente_id = :cliente_id"
                params['cliente_id'] = filtros['cliente_id']
            if filtros.get('operador_id'):
                query += " AND T.operador_id = :operador_id"
                params['operador_id'] = filtros['operador_id']
            if filtros.get('equipo_id'):
                query += " AND T.equipo_id = :equipo_id"
                params['equipo_id'] = filtros['equipo_id']
            if filtros.get('fecha_inicio'):
                query += " AND T.fecha >= :fecha_inicio"
                params['fecha_inicio'] = filtros['fecha_inicio']
            if filtros.get('fecha_fin'):
                query += " AND T.fecha <= :fecha_fin"
                params['fecha_fin'] = filtros['fecha_fin']
        query += " ORDER BY T.fecha DESC, T.id DESC"
        return self._ejecutar_consulta(query, params, fetchall=True)

    def obtener_mantenimientos_por_equipo(self, equipo_id, limite=200):
        """
        Devuelve el historial de mantenimientos de un equipo por ID,
        devolviendo los campos que muestra la tabla y la UI.
        """
        return self.fetchall(
            """
            SELECT 
                id,
                equipo_id,
                fecha AS fecha_servicio,
                descripcion,
                tipo,
                valor AS costo,
                odometro_horas AS horas_totales_equipo,
                odometro_km AS km_totales_equipo,
                proximo_tipo,
                proximo_valor,
                proximo_fecha,
                created_at
            FROM mantenimientos
            WHERE equipo_id = ?
            ORDER BY COALESCE(fecha, created_at) DESC, id DESC
            LIMIT ?
            """,
            (equipo_id, limite)
        )

    def obtener_estado_mantenimiento_equipos(self, proyecto_id=None):
        """
        Devuelve el estado de mantenimiento de cada equipo:
        - El intervalo de servicio se lee de la tabla equipos (mantenimiento_trigger_tipo y mantenimiento_trigger_valor).
        - El uso se calcula como la diferencia entre el odómetro actual y el del último mantenimiento.
        - El restante y progreso se calculan en base al intervalo.
        """
        equipos = self.obtener_equipos(proyecto_id) if proyecto_id else self.obtener_equipos()
        resultado = []
        for equipo in equipos:
            equipo_id = equipo['id']
            nombre = equipo.get('nombre', '')

            trigger_tipo = (equipo.get('mantenimiento_trigger_tipo') or '').upper()
            trigger_valor = equipo.get('mantenimiento_trigger_valor')

            # Valor actual del odómetro
            odometro_actual = 0
            if trigger_tipo == "HORAS":
                odometro_actual = float(equipo.get('odometro_horas') or 0)
            elif trigger_tipo == "KM":
                odometro_actual = float(equipo.get('odometro_km') or 0)

            # Valor del odómetro en el último mantenimiento
            row = self.fetchone(
                "SELECT odometro_horas, odometro_km FROM mantenimientos WHERE equipo_id = ? ORDER BY COALESCE(fecha, created_at) DESC LIMIT 1",
                (equipo_id,)
            )
            odometro_base = 0
            if row:
                if trigger_tipo == "HORAS":
                    odometro_base = float(row.get("odometro_horas") or 0)
                elif trigger_tipo == "KM":
                    odometro_base = float(row.get("odometro_km") or 0)

            # Cálculo del uso desde el último mantenimiento
            uso = max(0.0, odometro_actual - odometro_base)

            # Restante y progreso
            if trigger_valor not in (None, '', 'None'):
                try:
                    trigger_valor_f = float(trigger_valor)
                    restante = trigger_valor_f - uso
                    progreso = uso / trigger_valor_f * 100 if trigger_valor_f > 0 else 0
                except Exception:
                    restante = 0
                    progreso = 0
            else:
                restante = 0
                progreso = 0

            if trigger_tipo and trigger_valor not in (None, '', 'None'):
                intervalo_txt = f"{trigger_valor} {trigger_tipo}"
            else:
                intervalo_txt = ""

            resultado.append({
                "id": equipo_id,
                "nombre": nombre,
                "intervalo_txt": intervalo_txt,
                "uso_txt": f"{uso:.1f}",
                "restante_txt": f"{restante:.1f}",
                "progreso_txt": f"{progreso:.1f}%",
                "critico": (trigger_valor not in (None, '', 'None') and uso >= float(trigger_valor)),
                "alerta": (trigger_valor not in (None, '', 'None') and 0.8 * float(trigger_valor) <= uso < float(trigger_valor)),
            })
        return resultado

    def obtener_acumulado_equipo(self, equipo_id, tipo):
        # tipo = "HORAS" o "KM"
        if tipo == "HORAS":
            row = self.fetchone("SELECT SUM(horas) as total FROM transacciones WHERE equipo_id = ?", (equipo_id,))
            return row['total'] if row and row['total'] else 0
        elif tipo == "KM":
            row = self.fetchone("SELECT SUM(kilometros) as total FROM transacciones WHERE equipo_id = ?", (equipo_id,))
            return row['total'] if row and row['total'] else 0
        return 0
    


    def actualizar_intervalo_equipo(self, equipo_id, tipo, valor):
        """
        Actualiza el intervalo de servicio de un equipo (tipo y valor).
        """
        self.execute(
            "UPDATE equipos SET mantenimiento_trigger_tipo = ?, mantenimiento_trigger_valor = ? WHERE id = ?",
            (tipo, valor, equipo_id)
        )


    def obtener_lista_abonos(self, proyecto_id: int, filtros: dict):
        """
        Obtiene una lista completa de los abonos registrados, con nombres de cliente
        y descripciones de transacción para ser mostrados en la GUI.
        """
        query = """
            SELECT
                P.id, P.fecha, P.monto, P.comentario,
                CLI.nombre as cliente_nombre,
                T.descripcion as transaccion_descripcion,
                T.id as transaccion_id
            FROM pagos P
            JOIN equipos_alquiler_meta META ON P.transaccion_id = META.transaccion_id
            JOIN equipos_entidades CLI ON META.cliente_id = CLI.id
            JOIN transacciones T ON P.transaccion_id = T.id
            WHERE T.proyecto_id = :proyecto_id
        """
        params = {'proyecto_id': proyecto_id}
        
        if filtros.get('cliente_id'):
            query += " AND META.cliente_id = :cliente_id"
            params['cliente_id'] = filtros['cliente_id']
        if filtros.get('fecha_inicio'):
            query += " AND P.fecha >= :fecha_inicio"
            params['fecha_inicio'] = filtros['fecha_inicio']
        if filtros.get('fecha_fin'):
            query += " AND P.fecha <= :fecha_fin"
            params['fecha_fin'] = filtros['fecha_fin']

        query += " ORDER BY P.fecha DESC, CLI.nombre ASC"
        return self.fetchall(query, params)

# En tu clase DatabaseManager (logic.py)
# REEMPLAZA la función obtener_fecha_primera_transaccion_cliente si ya la tienes

    def obtener_fecha_primera_transaccion_cliente(self, proyecto_id, cliente_id):
        """
        Obtiene la fecha de la primera transacción para un cliente específico,
        leyendo directamente de la tabla 'transacciones'.
        """
        query = "SELECT MIN(fecha) as primera_fecha FROM transacciones WHERE proyecto_id = ? AND cliente_id = ?"
        resultado = self.fetchone(query, (proyecto_id, cliente_id))
        return resultado['primera_fecha'] if resultado and resultado['primera_fecha'] else None

# En tu clase DatabaseManager (logic.py)
# AÑADE esta nueva función

    def obtener_fecha_primera_transaccion_operador(self, proyecto_id, operador_id):
        """
        Obtiene la fecha de la primera transacción para un operador específico.
        """
        query = "SELECT MIN(fecha) as primera_fecha FROM transacciones WHERE proyecto_id = ? AND operador_id = ?"
        resultado = self.fetchone(query, (proyecto_id, operador_id))
        return resultado['primera_fecha'] if resultado and resultado['primera_fecha'] else None


    def actualizar_abono(self, pago_id: int, nueva_fecha: str, nuevo_monto: float, nuevo_comentario: str):
        """Actualiza un registro de pago y recalcula el estado de la transacción asociada."""
        cur = None
        try:
            cur = self._conn.cursor()

            # 1. Obtener el ID de la transacción original antes de hacer cambios
            cur.execute("SELECT transaccion_id FROM pagos WHERE id = ?", (pago_id,))
            res = cur.fetchone()
            if not res:
                raise ValueError("El pago a actualizar no fue encontrado.")
            transaccion_id = res['transaccion_id']

            # 2. Actualizar el pago
            cur.execute(
                "UPDATE pagos SET fecha = ?, monto = ?, comentario = ? WHERE id = ?",
                (nueva_fecha, nuevo_monto, nuevo_comentario, pago_id)
            )

            # 3. Recalcular el estado de la transacción
            self._actualizar_estado_pago_transaccion(transaccion_id, cur)
            
            self._conn.commit()
            return True
        except Exception as e:
            self._conn.rollback()
            print(f"[ERROR] No se pudo actualizar el abono: {e}")
            return False
        finally:
            if cur: cur.close()
            

    def eliminar_abono(self, pago_ids: list) -> bool:
        """
        Elimina uno o más registros de pago y recalcula el estado de las
        transacciones asociadas. Es una operación atómica.
        """
        if not pago_ids:
            return False
            
        cur = None
        try:
            cur = self._conn.cursor()

            # 1. Crear una cadena de placeholders (?,?,?) para la consulta SQL
            placeholders = ', '.join(['?'] * len(pago_ids))

            # 2. Obtener los IDs de las transacciones originales ANTES de eliminar los pagos
            cur.execute(
                f"SELECT DISTINCT transaccion_id FROM pagos WHERE id IN ({placeholders})",
                pago_ids
            )
            transacciones_afectadas = [row['transaccion_id'] for row in cur.fetchall()]

            # 3. Eliminar los pagos seleccionados
            cur.execute(f"DELETE FROM pagos WHERE id IN ({placeholders})", pago_ids)

            # 4. Recalcular el estado de CADA transacción afectada
            if transacciones_afectadas:
                for trans_id in transacciones_afectadas:
                    self._actualizar_estado_pago_transaccion(trans_id, cur)

            self._conn.commit()
            return True
        except Exception as e:
            self._conn.rollback()
            print(f"[ERROR] No se pudo eliminar el/los abono(s): {e}")
            return False
        finally:
            if cur: cur.close()


    def obtener_transacciones_pendientes_cliente(self, proyecto_id: int, cliente_id: int):
        """
        Obtiene una lista de todas las transacciones de alquiler pendientes de pago
        para un cliente específico, ordenadas por fecha (la más antigua primero).
        """
        query = """
            SELECT T.id, T.fecha, T.descripcion, T.monto
            FROM transacciones T
            WHERE T.proyecto_id = ? AND T.cliente_id = ? AND T.pagado = 0
            ORDER BY T.fecha ASC, T.id ASC
        """
        return self.fetchall(query, (proyecto_id, cliente_id))

    def registrar_abono_general_cliente(self, datos_pago: dict):
        """
        Registra un abono general de un cliente y lo aplica a las facturas
        pendientes más antiguas primero. Es una operación atómica.
        """
        cur = None
        try:
            cur = self._conn.cursor()

            proyecto_id = datos_pago['proyecto_id']
            cliente_id = datos_pago['cliente_id']
            monto_abonar = datos_pago['monto']
            
            cur.execute("""
                SELECT T.id, T.monto FROM transacciones T
                JOIN equipos_alquiler_meta META ON T.id = META.transaccion_id
                WHERE T.proyecto_id = ? AND META.cliente_id = ? AND T.pagado = 0
                ORDER BY T.fecha ASC, T.id ASC
            """, (proyecto_id, cliente_id))
            pendientes = cur.fetchall()
            
            if not pendientes:
                raise ValueError("Este cliente no tiene facturas pendientes de pago.")

            monto_restante_abono = monto_abonar
            for trans in pendientes:
                if monto_restante_abono <= 0:
                    break

                trans_id = trans['id']
                monto_factura = trans['monto']

                cur.execute("SELECT SUM(monto) FROM pagos WHERE transaccion_id = ?", (trans_id,))
                total_previo_pagado = cur.fetchone()[0] or 0
                
                monto_pendiente_factura = monto_factura - total_previo_pagado
                if monto_pendiente_factura <= 0:
                    continue

                monto_a_aplicar = min(monto_restante_abono, monto_pendiente_factura)

                cur.execute(
                    "INSERT INTO pagos (transaccion_id, cuenta_id, fecha, monto, comentario) VALUES (?, ?, ?, ?, ?)",
                    (trans_id, datos_pago['cuenta_id'], datos_pago['fecha'], monto_a_aplicar, datos_pago['comentario'])
                )
                
                self._actualizar_estado_pago_transaccion(trans_id, cur)
                monto_restante_abono -= monto_a_aplicar

            self._conn.commit()
            return True

        except ValueError as ve:
            self._conn.rollback()
            # Devolvemos el mensaje de error específico para mostrarlo en la GUI
            return str(ve)
        except Exception as e:
            self._conn.rollback()
            print(f"[ERROR] No se pudo registrar el abono general: {e}")
            return False
        finally:
            if cur: cur.close()


    def obtener_abono_por_id(self, pago_id: int):
        """Obtiene los detalles de un único abono por su ID."""
        query = "SELECT * FROM pagos WHERE id = ?"
        return self._ejecutar_consulta(query, (pago_id,), fetchone=True)


    def listar_cuentas(self):
        """
        Devuelve una lista de todas las cuentas disponibles.
        """
        return self.fetchall("SELECT id, nombre FROM cuentas ORDER BY nombre")

    def _actualizar_estado_pago_transaccion(self, transaccion_id, cursor=None):
        """
        Actualiza el campo 'pagado' de la transacción si el monto pagado es igual o mayor al monto de la factura.
        Si el cursor se pasa como argumento, lo usa; si no, crea uno temporal.
        """
        close_cur = False
        if cursor is None:
            cursor = self._conn.cursor()
            close_cur = True

        # Obtener el monto total de la transacción
        cursor.execute("SELECT monto FROM transacciones WHERE id = ?", (transaccion_id,))
        row = cursor.fetchone()
        if not row:
            if close_cur:
                cursor.close()
            return
        monto_total = row["monto"]

        # Obtener el monto total pagado
        cursor.execute("SELECT SUM(monto) as pagado FROM pagos WHERE transaccion_id = ?", (transaccion_id,))
        row = cursor.fetchone()
        monto_pagado = row["pagado"] or 0

        # Determinar si la factura está pagada
        pagado = 1 if monto_pagado >= monto_total else 0

        # Actualizar el campo 'pagado' en la transacción
        cursor.execute("UPDATE transacciones SET pagado = ? WHERE id = ?", (pagado, transaccion_id))

        if close_cur:
            self._conn.commit()
            cursor.close()


    def _ejecutar_consulta(self, query, params=None, fetchone=False, fetchall=False, commit=False):
        """
        Método genérico para ejecutar consultas SQL.
        Devuelve los resultados como diccionarios.
        """
        # Permite acceder a los resultados por nombre de columna
        self._conn.row_factory = sqlite3.Row 
        cursor = self._conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        resultado = None
        if fetchone:
            resultado = cursor.fetchone()
        elif fetchall:
            resultado = cursor.fetchall()

        if commit:
            self._conn.commit()

        # Si el resultado es una lista de sqlite3.Row, lo convertimos a una lista de diccionarios
        if isinstance(resultado, list):
            return [dict(row) for row in resultado]
        # Si es un solo sqlite3.Row, lo convertimos a un diccionario
        if isinstance(resultado, sqlite3.Row):
            return dict(resultado)
            
        return resultado


    def eliminar_alquiler(self, alquiler_id):
        """
        Elimina un registro de alquiler (una transacción) de la base de datos.
        """
        try:
            query = "DELETE FROM transacciones WHERE id = :id"
            params = {'id': alquiler_id}
            # Usamos el método ayudante que ya tienes, asegurando que se haga commit
            self._ejecutar_consulta(query, params, commit=True)
            print(f"[INFO] Alquiler con ID {alquiler_id} eliminado exitosamente.")
            return True # Retorna True si la operación fue exitosa
        except Exception as e:
            print(f"[ERROR] No se pudo eliminar el alquiler con ID {alquiler_id}: {e}")
            return False # Retorna False si ocurrió un error


    def obtener_detalles_alquiler(self, transaccion_id):
        """
        Obtiene todos los detalles de un único alquiler (transacción) por su ID.
        """
        try:
            query = "SELECT * FROM transacciones WHERE id = :id"
            params = {'id': transaccion_id}
            
            # Usamos el ayudante para obtener una sola fila (fetchone)
            # El resultado será un diccionario con los datos del alquiler
            resultado = self._ejecutar_consulta(query, params, fetchone=True)
            
            return resultado # Retorna el diccionario o None si no se encuentra
        except Exception as e:
            print(f"[ERROR] No se pudieron obtener los detalles para el alquiler con ID {transaccion_id}: {e}")
            return None

    def obtener_equipos_por_proyecto(self, proyecto_id):
        rows = self.fetchall(
            "SELECT id, nombre FROM equipos WHERE proyecto_id = ?",
            (proyecto_id,)
        )
        # print("Equipos encontrados:", rows)  # <-- ELIMINA O COMENTA ESTA LINEA
        return rows



    def obtener_todos_los_equipos(self):
        # Esta es la función correcta y única para Equipos
        query = "SELECT id, nombre FROM equipos WHERE activo = 1 ORDER BY nombre"
        return self.fetchall(query)

    def crear_nuevo_alquiler(self, datos):
        """
        Inserta un nuevo alquiler en la tabla 'transacciones'.
        """
        try:
            # Generamos un ID único para la nueva transacción
            datos['id'] = str(uuid.uuid4())
            # Nos aseguramos de que el campo 'pagado' tenga un valor inicial
            datos['pagado'] = datos.get('pagado', 0)

            columnas = ', '.join(datos.keys())
            placeholders = ', '.join(f":{key}" for key in datos.keys())
            
            query = f"INSERT INTO transacciones ({columnas}) VALUES ({placeholders})"
            
            self._ejecutar_consulta(query, datos, commit=True)
            print(f"[INFO] Nuevo alquiler creado con ID {datos['id']}.")
            return True
        except Exception as e:
            print(f"[ERROR] No se pudo crear el nuevo alquiler: {e}")
            return False



    def actualizar_alquiler(self, transaccion_id, datos):
        """
        Actualiza un alquiler existente en la tabla 'transacciones'.
        """
        try:
            # Construimos la parte SET de la consulta dinámicamente
            set_clauses = [f"{key} = :{key}" for key in datos.keys()]
            set_string = ", ".join(set_clauses)
            
            query = f"UPDATE transacciones SET {set_string} WHERE id = :transaccion_id"
            
            # Añadimos el ID de la transacción al diccionario de parámetros
            params = datos.copy()
            params['transaccion_id'] = transaccion_id
            
            self._ejecutar_consulta(query, params, commit=True)
            print(f"[INFO] Alquiler con ID {transaccion_id} actualizado exitosamente.")
            return True
        except Exception as e:
            print(f"[ERROR] No se pudo actualizar el alquiler con ID {transaccion_id}: {e}")
            return False


    def obtener_clientes_por_proyecto(self, proyecto_id):
        # Correcta (atajo)
        return self.obtener_entidades_equipo_por_tipo(proyecto_id, "Cliente")
    

    def actualizar_conduce_adjunto(self, transaccion_id, ruta_adjunto):
        """
        Actualiza únicamente la ruta del archivo de conduce para una transacción existente.
        """
        try:
            query = "UPDATE transacciones SET conduce_adjunto_path = ? WHERE id = ?"
            self.execute(query, (ruta_adjunto, transaccion_id))
            return True
        except Exception as e:
            logger.error(f"Error al actualizar conduce adjunto para {transaccion_id}: {e}")
            return False

    # --- NUEVAS FUNCIONES PARA REPORTES DE ESTADO DE CUENTA ---

    def obtener_datos_estado_cuenta_cliente_global(self, cliente_id, fecha_inicio, fecha_fin):
        """
        NUEVA FUNCIÓN: Obtiene facturas y abonos para el estado de cuenta de UN cliente.
        """
        # Obtener Facturas (transacciones de ingreso)
        facturas_query = """
            SELECT T.*, CLI.nombre as cliente_nombre, EQ.nombre as equipo_nombre
            FROM transacciones T
            LEFT JOIN equipos_entidades CLI ON T.cliente_id = CLI.id
            LEFT JOIN equipos EQ ON T.equipo_id = EQ.id
            WHERE T.cliente_id = ? AND T.fecha BETWEEN ? AND ? AND T.tipo = 'Ingreso'
            ORDER BY T.fecha
        """
        facturas = self.fetchall(facturas_query, (cliente_id, fecha_inicio, fecha_fin))

        # Obtener Abonos (pagos)
        abonos_query = """
            SELECT P.*, T.descripcion as transaccion_descripcion
            FROM pagos P
            JOIN transacciones T ON P.transaccion_id = T.id
            WHERE T.cliente_id = ? AND P.fecha BETWEEN ? AND ?
            ORDER BY P.fecha
        """
        abonos = self.fetchall(abonos_query, (cliente_id, fecha_inicio, fecha_fin))
        
        return facturas, abonos


    def obtener_datos_estado_cuenta_general_global(self, proyecto_id, fecha_inicio, fecha_fin):
        """Obtiene facturas y abonos para el estado de cuenta de TODOS los clientes de un proyecto."""
        # Obtener todas las Facturas del proyecto
        facturas_query = """
            SELECT T.*, CLI.nombre as cliente_nombre, EQ.nombre as equipo_nombre
            FROM transacciones T
            LEFT JOIN equipos_entidades CLI ON T.cliente_id = CLI.id
            LEFT JOIN equipos EQ ON T.equipo_id = EQ.id
            WHERE T.proyecto_id = ? AND T.fecha BETWEEN ? AND ? AND T.tipo = 'Ingreso'
            ORDER BY CLI.nombre, T.fecha
        """
        facturas = self.fetchall(facturas_query, (proyecto_id, str(fecha_inicio), str(fecha_fin)))

        # Obtener todos los Abonos del proyecto
        abonos_query = """
            SELECT P.*, CLI.nombre as cliente_nombre
            FROM pagos P
            JOIN transacciones T ON P.transaccion_id = T.id
            JOIN equipos_entidades CLI ON T.cliente_id = CLI.id
            WHERE T.proyecto_id = ? AND P.fecha BETWEEN ? AND ?
            ORDER BY CLI.nombre, P.fecha
        """
        abonos = self.fetchall(abonos_query, (proyecto_id, str(fecha_inicio), str(fecha_fin)))
        
        return facturas, abonos

    def obtener_total_abonos_cliente(self, proyecto_id, cliente_id, fecha_inicio, fecha_fin):
        """
        NUEVA FUNCIÓN: Obtiene el total abonado por un cliente en un rango de fechas.
        """
        query = """
            SELECT SUM(P.monto) as total
            FROM pagos P
            JOIN transacciones T ON P.transaccion_id = T.id
            WHERE T.proyecto_id = ? AND T.cliente_id = ? AND P.fecha BETWEEN ? AND ?
        """
        resultado = self.fetchone(query, (proyecto_id, cliente_id, fecha_inicio, fecha_fin))
        return resultado['total'] if resultado and resultado['total'] else 0.0
    

    def obtener_pagos_a_operadores(self, proyecto_id, filtros):
        q = """
        SELECT t.id, t.fecha, c.nombre as cuenta, o.nombre as operador, eq.nombre as equipo,
            t.horas, t.descripcion, t.monto, t.comentario
        FROM transacciones t
            LEFT JOIN cuentas c ON t.cuenta_id = c.id
            LEFT JOIN equipos_entidades o ON t.operador_id = o.id AND o.tipo = 'Operador'
            LEFT JOIN equipos eq ON t.equipo_id = eq.id
        WHERE t.proyecto_id = ? AND t.tipo = 'Gasto'
        AND t.categoria_id IN (SELECT id FROM categorias WHERE nombre = 'PAGO HRS OPERADOR')
        """
        params = [proyecto_id]
        if filtros.get("cuenta_id"):
            q += " AND t.cuenta_id = ?"
            params.append(filtros["cuenta_id"])
        if filtros.get("operador_id"):
            q += " AND t.operador_id = ?"
            params.append(filtros["operador_id"])
        if filtros.get("equipo_id"):
            q += " AND t.equipo_id = ?"
            params.append(filtros["equipo_id"])
        if filtros.get("fecha_desde"):
            q += " AND date(t.fecha) >= ?"
            params.append(filtros["fecha_desde"])
        if filtros.get("fecha_hasta"):
            q += " AND date(t.fecha) <= ?"
            params.append(filtros["fecha_hasta"])
        if filtros.get("texto"):
            q += " AND (t.descripcion LIKE ? OR t.comentario LIKE ?)"
            params.extend([f"%{filtros['texto']}%", f"%{filtros['texto']}%"])
        q += " ORDER BY date(t.fecha) DESC, t.id DESC"
        return self.fetchall(q, tuple(params))

    def analisis_horas_por_operador(self, proyecto_id):
        """
        Calcula el total de horas y el ingreso total generado por cada operador
        en un proyecto específico.
        """
        query = """
            SELECT
                OPE.nombre as operador_nombre,
                SUM(T.horas) as total_horas,
                SUM(T.monto) as total_ingresos
            FROM transacciones T
            LEFT JOIN equipos_entidades OPE ON T.operador_id = OPE.id
            WHERE
                T.proyecto_id = ?
                AND T.tipo = 'Ingreso'
                AND T.operador_id IS NOT NULL
            GROUP BY OPE.nombre
            ORDER BY total_horas DESC
        """
        return self.fetchall(query, (proyecto_id,))


    # Obtiene cuentas del proyecto
    def obtener_cuentas_por_proyecto(self, proyecto_id):
        q = "SELECT id, nombre FROM cuentas WHERE id IN (SELECT cuenta_id FROM transacciones WHERE proyecto_id = ?) ORDER BY nombre"
        return self.fetchall(q, (proyecto_id,))

    # Obtiene categorías de tipo (Gasto/Ingreso) usadas en el proyecto
    def obtener_categorias_por_proyecto(self, proyecto_id, tipo="Gasto"):
        q = "SELECT DISTINCT c.id, c.nombre FROM transacciones t JOIN categorias c ON t.categoria_id = c.id WHERE t.proyecto_id = ? AND t.tipo = ? ORDER BY c.nombre"
        return self.fetchall(q, (proyecto_id, tipo))

    # Obtiene subcategorías para una categoría
    def obtener_subcategorias_por_categoria(self, categoria_id):
        q = "SELECT id, nombre FROM subcategorias WHERE categoria_id = ? ORDER BY nombre"
        return self.fetchall(q, (categoria_id,))


    # Crea una subcategoría si no existe y retorna su id
    def crear_subcategoria(self, nombre, categoria_id):
        # ¿Existe ya?
        subcat = self.fetchone("SELECT id FROM subcategorias WHERE nombre = ? AND categoria_id = ?", (nombre, categoria_id))
        if subcat:
            return subcat['id']
        cur = self._conn.cursor()
        cur.execute("INSERT INTO subcategorias (nombre, categoria_id) VALUES (?, ?)", (nombre, categoria_id))
        self._conn.commit()
        subcat_id = cur.lastrowid
        cur.close()
        return subcat_id

    # Guarda un gasto de equipo
    def guardar_gasto_equipo(self, datos):
        q = """
        INSERT INTO transacciones
        (id, proyecto_id, cuenta_id, categoria_id, subcategoria_id, equipo_id, tipo, descripcion, comentario, monto, fecha)
        VALUES (:id, :proyecto_id, :cuenta_id, :categoria_id, :subcategoria_id, :equipo_id, :tipo, :descripcion, :comentario, :monto, :fecha)
        """
        try:
            cur = self._conn.cursor()
            cur.execute(q, datos)
            self._conn.commit()
            cur.close()
            return True
        except Exception as e:
            print("Error guardando gasto:", e)
            return False

    # Obtiene los gastos con todos los filtros
    def obtener_gastos_equipo(self, proyecto_id, filtros):
        q = """
        SELECT t.id, t.fecha, c.nombre as cuenta, ca.nombre as categoria, s.nombre as subcategoria,
            eq.nombre as equipo, t.descripcion, t.monto, t.comentario
        FROM transacciones t
            LEFT JOIN cuentas c ON t.cuenta_id = c.id
            LEFT JOIN categorias ca ON t.categoria_id = ca.id
            LEFT JOIN subcategorias s ON t.subcategoria_id = s.id
            LEFT JOIN equipos eq ON t.equipo_id = eq.id
        WHERE t.proyecto_id = ? AND t.tipo = 'Gasto'
        """
        params = [proyecto_id]
        if filtros.get("cuenta_id"):
            q += " AND t.cuenta_id = ?"
            params.append(filtros["cuenta_id"])
        if filtros.get("categoria_id"):
            q += " AND t.categoria_id = ?"
            params.append(filtros["categoria_id"])
        if filtros.get("subcategoria_id"):
            q += " AND t.subcategoria_id = ?"
            params.append(filtros["subcategoria_id"])
        if filtros.get("equipo_id"):
            q += " AND t.equipo_id = ?"
            params.append(filtros["equipo_id"])
        if filtros.get("fecha_desde"):
            q += " AND date(t.fecha) >= ?"
            params.append(filtros["fecha_desde"])
        if filtros.get("fecha_hasta"):
            q += " AND date(t.fecha) <= ?"
            params.append(filtros["fecha_hasta"])
        if filtros.get("texto"):
            q += " AND (t.descripcion LIKE ? OR t.comentario LIKE ?)"
            params.extend([f"%{filtros['texto']}%", f"%{filtros['texto']}%"])
        q += " ORDER BY date(t.fecha) DESC, t.id DESC"
        return self.fetchall(q, tuple(params))

    def eliminar_gasto_equipo(self, gasto_id):
        try:
            cur = self._conn.cursor()
            cur.execute("DELETE FROM transacciones WHERE id = ?", (gasto_id,))
            self._conn.commit()
            cur.close()
            return True
        except Exception as e:
            print("Error eliminando gasto:", e)
            return False

    def editar_gasto_equipo(self, datos):
        q = """
        UPDATE transacciones
        SET cuenta_id=:cuenta_id, categoria_id=:categoria_id, subcategoria_id=:subcategoria_id,
            equipo_id=:equipo_id, descripcion=:descripcion, comentario=:comentario,
            monto=:monto, fecha=:fecha
        WHERE id=:id
        """
        try:
            cur = self._conn.cursor()
            cur.execute(q, datos)
            self._conn.commit()
            cur.close()
            return True
        except Exception as e:
            print("Error editando gasto:", e)
            return False


    def obtener_operadores_por_proyecto(self, proyecto_id):
        return self.fetchall(
            "SELECT id, nombre FROM equipos_entidades WHERE proyecto_id = ? AND tipo = 'Operador' AND activo = 1 ORDER BY nombre",
            (proyecto_id,)
        )
    
    def guardar_pago_operador(self, datos):
        q = """
        INSERT INTO transacciones
        (id, proyecto_id, cuenta_id, categoria_id, subcategoria_id, equipo_id, operador_id, tipo, descripcion, comentario, monto, fecha, horas)
        VALUES (:id, :proyecto_id, :cuenta_id, :categoria_id, :subcategoria_id, :equipo_id, :operador_id, :tipo, :descripcion, :comentario, :monto, :fecha, :horas)
        """
        try:
            cur = self._conn.cursor()
            cur.execute(q, datos)
            self._conn.commit()
            cur.close()
            return True
        except Exception as e:
            print("Error guardando pago operador:", e)
            return False

    def editar_pago_operador(self, datos):
        q = """
        UPDATE transacciones
        SET cuenta_id=:cuenta_id, categoria_id=:categoria_id, subcategoria_id=:subcategoria_id,
            equipo_id=:equipo_id, operador_id=:operador_id, descripcion=:descripcion,
            comentario=:comentario, monto=:monto, fecha=:fecha, horas=:horas
        WHERE id=:id
        """
        try:
            cur = self._conn.cursor()
            cur.execute(q, datos)
            self._conn.commit()
            cur.close()
            return True
        except Exception as e:
            print("Error editando pago operador:", e)
            return False

    def eliminar_pago_operador(self, pago_id):
        try:
            cur = self._conn.cursor()
            cur.execute("DELETE FROM transacciones WHERE id = ?", (pago_id,))
            self._conn.commit()
            cur.close()
            return True
        except Exception as e:
            print("Error eliminando pago operador:", e)
            return False

    def obtener_pagos_a_operadores(self, proyecto_id, filtros):
        q = """
        SELECT t.id, t.fecha, c.nombre as cuenta, o.nombre as operador, eq.nombre as equipo,
            t.horas, t.descripcion, t.monto, t.comentario
        FROM transacciones t
            LEFT JOIN cuentas c ON t.cuenta_id = c.id
            LEFT JOIN equipos_entidades o ON t.operador_id = o.id AND o.tipo = 'Operador'
            LEFT JOIN equipos eq ON t.equipo_id = eq.id
        WHERE t.proyecto_id = ? AND t.tipo = 'Gasto'
        AND t.categoria_id IN (SELECT id FROM categorias WHERE nombre = 'PAGO HRS OPERADOR')
        """
        params = [proyecto_id]
        if filtros.get("cuenta_id"):
            q += " AND t.cuenta_id = ?"
            params.append(filtros["cuenta_id"])
        if filtros.get("operador_id"):
            q += " AND t.operador_id = ?"
            params.append(filtros["operador_id"])
        if filtros.get("equipo_id"):
            q += " AND t.equipo_id = ?"
            params.append(filtros["equipo_id"])
        if filtros.get("fecha_desde"):
            q += " AND date(t.fecha) >= ?"
            params.append(filtros["fecha_desde"])
        if filtros.get("fecha_hasta"):
            q += " AND date(t.fecha) <= ?"
            params.append(filtros["fecha_hasta"])
        if filtros.get("texto"):
            q += " AND (t.descripcion LIKE ? OR t.comentario LIKE ?)"
            params.extend([f"%{filtros['texto']}%", f"%{filtros['texto']}%"])
        q += " ORDER BY date(t.fecha) DESC, t.id DESC"
        return self.fetchall(q, tuple(params))

    def obtener_cliente_equipo(self, proyecto_id, equipo_id):
        """
        Retorna el nombre del cliente más reciente asociado a un equipo en las transacciones.
        """
        row = self.fetchone(
            "SELECT cliente_id FROM transacciones WHERE proyecto_id = ? AND equipo_id = ? AND cliente_id IS NOT NULL ORDER BY fecha DESC LIMIT 1",
            (proyecto_id, equipo_id)
        )
        if row and row['cliente_id']:
            cliente_row = self.fetchone("SELECT nombre FROM equipos_entidades WHERE id = ?", (row['cliente_id'],))
            return cliente_row['nombre'] if cliente_row else ""
        return ""

    def obtener_ubicacion_equipo(self, proyecto_id, equipo_id):
        """
        Retorna la ubicación más reciente de un equipo según la última transacción registrada.
        """
        row = self.fetchone(
            "SELECT ubicacion FROM transacciones WHERE proyecto_id = ? AND equipo_id = ? AND ubicacion IS NOT NULL AND ubicacion != '' ORDER BY fecha DESC LIMIT 1",
            (proyecto_id, equipo_id)
        )
        if row and 'ubicacion' in row and row['ubicacion']:
            return row['ubicacion']
        return ""

    def obtener_o_crear_id(self, tabla, nombre, columna_extra=None, valor_extra=None):
        """
        Busca el id de un registro por nombre (y columna extra opcional) en la tabla dada.
        Si no existe, lo crea y retorna el nuevo id.
        """
        if columna_extra and valor_extra is not None:
            row = self.fetchone(
                f"SELECT id FROM {tabla} WHERE nombre = ? AND {columna_extra} = ?",
                (nombre, valor_extra)
            )
        else:
            row = self.fetchone(
                f"SELECT id FROM {tabla} WHERE nombre = ?",
                (nombre,)
            )
        if row and 'id' in row:
            return row['id']
        # Si no existe, crear
        cur = self._conn.cursor()
        if columna_extra and valor_extra is not None:
            cur.execute(
                f"INSERT INTO {tabla} (nombre, {columna_extra}) VALUES (?, ?)",
                (nombre, valor_extra)
            )
        else:
            cur.execute(
                f"INSERT INTO {tabla} (nombre) VALUES (?)",
                (nombre,)
            )
        self._conn.commit()
        new_id = cur.lastrowid
        cur.close()
        return new_id


    def obtener_anios_transacciones(self, proyecto_id):
        """
        Obtiene una lista de años únicos en los que hay transacciones para un proyecto,
        ordenados de más reciente a más antiguo.
        """
        query = """
            SELECT DISTINCT STRFTIME('%Y', fecha) as anio
            FROM transacciones
            WHERE proyecto_id = ?
            ORDER BY anio DESC
        """
        rows = self.fetchall(query, (proyecto_id,))
        return [row['anio'] for row in rows if row['anio']]


    def asegurar_tabla_equipos_entidades(self):
        """Crea la tabla equipos_entidades si no existe (para Clientes y Operadores)."""
        query = """
            CREATE TABLE IF NOT EXISTS equipos_entidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                tipo TEXT NOT NULL,
                proyecto_id INTEGER,
                activo INTEGER DEFAULT 1,
                UNIQUE(nombre, tipo, proyecto_id)
            )
        """
        self.execute(query)
        logger.info("Tabla equipos_entidades asegurada")

    def guardar_entidad(self, datos, entidad_id=None):
        """
        Guarda o actualiza una entidad (Cliente u Operador) incluyendo telefono y cedula.
        """
        try:
            if entidad_id:
                # Actualizar entidad existente
                query = """
                    UPDATE equipos_entidades 
                    SET nombre=?, tipo=?, proyecto_id=?, activo=?, telefono=?, cedula=?
                    WHERE id=?
                """
                self.execute(query, (
                    datos.get("nombre"),
                    datos.get("tipo"),
                    datos.get("proyecto_id"),
                    datos.get("activo", 1),
                    datos.get("telefono"),
                    datos.get("cedula"),
                    entidad_id
                ))
                logger.info("Entidad actualizada: ID=%s, nombre=%s", entidad_id, datos.get("nombre"))
            else:
                # Crear nueva entidad
                query = """
                    INSERT INTO equipos_entidades (nombre, tipo, proyecto_id, activo, telefono, cedula)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                self.execute(query, (
                    datos.get("nombre"),
                    datos.get("tipo"),
                    datos.get("proyecto_id"),
                    datos.get("activo", 1),
                    datos.get("telefono"),
                    datos.get("cedula")
                ))
                logger.info("Nueva entidad creada: nombre=%s, tipo=%s", datos.get("nombre"), datos.get("tipo"))
            return True
        except Exception as e:
            logger.exception("Error guardando entidad: %s", e)
            return False
        
    def eliminar_entidad(self, entidad_id):
        """
        Elimina (marca como inactiva) una entidad de equipos_entidades.
        Retorna True si tuvo éxito.
        """
        try:
            # En lugar de eliminar físicamente, marcamos como inactiva
            self.execute("UPDATE equipos_entidades SET activo = 0 WHERE id = ?", (entidad_id,))
            logger.info("Entidad marcada como inactiva: ID=%s", entidad_id)
            return True
        except Exception as e:
            logger.exception("Error eliminando entidad ID=%s: %s", entidad_id, e)
            return False

    def obtener_entidad_por_id(self, entidad_id):
        """
        Obtiene una entidad por su ID.
        """
        return self.fetchone("SELECT * FROM equipos_entidades WHERE id = ?", (entidad_id,))

# --- CLASES DE DATOS (MODELOS) ---
class Transaccion:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.fecha = kwargs.get('fecha')
        if isinstance(self.fecha, str):
            self.fecha = datetime.strptime(self.fecha, '%Y-%m-%d').date()
        self.tipo = kwargs.get('tipo')
        self.categoria_nombre = kwargs.get('categoria_nombre')
        self.equipo_nombre = kwargs.get('equipo_nombre')
        self.monto = float(kwargs.get('monto', 0))
        self.cliente_nombre = kwargs.get('cliente_nombre')
        self.operador_nombre = kwargs.get('operador_nombre')
        self.conduce = kwargs.get('conduce')
        self.ubicacion = kwargs.get('ubicacion')
        self.horas = float(kwargs.get('horas', 0) or 0)
        self.precio_por_hora = float(kwargs.get('precio_por_hora', 0) or 0)
        self.pagado = bool(kwargs.get('pagado', 0))




class Proyecto:
    def __init__(self, db_manager: DatabaseManager, proyecto_id: int):
        self.db = db_manager
        self.id = proyecto_id
        self.nombre = ""
        self.moneda = ""
        self.cargar_datos_iniciales()

    def cargar_datos_iniciales(self):
        datos_proyecto = self.db.obtener_proyecto_por_id(self.id)
        if not datos_proyecto:
            return False
        self.nombre = datos_proyecto['nombre']
        self.moneda = datos_proyecto['moneda']
        return True
    
       
