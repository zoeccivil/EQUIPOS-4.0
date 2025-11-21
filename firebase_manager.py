"""
Gestor de Firebase (Firestore) para EQUIPOS 4.0
Encapsula todas las operaciones con Firebase/Firestore
"""

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import time
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)


def retry_on_quota_exceeded(max_retries=3, initial_delay=1.0):
    """
    Decorador para reintentar operaciones cuando se excede la cuota de Firebase.
    Usa exponential backoff: espera 1s, luego 2s, luego 4s, etc.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except google_exceptions.ResourceExhausted as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Cuota excedida en {func.__name__}, reintentando en {delay}s "
                            f"(intento {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"Cuota excedida después de {max_retries} intentos en {func.__name__}")
                except Exception as e:
                    # Para otros errores, no reintentar
                    raise e

            # Si llegamos aquí, todos los reintentos fallaron
            raise last_exception
        return wrapper
    return decorator


class FirebaseManager:
    """
    Gestor de conexión y operaciones con Firebase Firestore.
    Proporciona métodos CRUD para todas las entidades de EQUIPOS.
    """

    def __init__(self, credentials_path: str, project_id: str, storage_manager: Any | None = None):
        """
        credentials_path: ruta al JSON de credenciales de servicio
        project_id: ID del proyecto de Firebase
        storage_manager: instancia opcional de StorageManager para subir archivos (gastos, pagos, etc.)
        """
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred, {
                    'projectId': project_id,
                })
                logger.info(f"Firebase inicializado con proyecto: {project_id}")
            else:
                logger.info("Firebase ya estaba inicializado")

            self.db = firestore.client()
            logger.info("Cliente de Firestore creado correctamente")

            # Referencia opcional al StorageManager (inyectado desde fuera)
            self.storage_manager = storage_manager
            if self.storage_manager:
                logger.info("FirebaseManager asociado a StorageManager correctamente")
            else:
                logger.info("FirebaseManager inicializado sin StorageManager (funciones de archivos deshabilitadas)")

        except FileNotFoundError:
            logger.error(f"No se encontró el archivo de credenciales: {credentials_path}")
            raise
        except Exception as e:
            logger.error(f"Error al inicializar Firebase: {e}")
            raise

    def _agregar_fecha_ano_mes(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """Añade campos 'ano' y 'mes' a un diccionario de datos si tiene 'fecha'."""
        if 'fecha' in datos:
            try:
                # Aceptar tanto objeto datetime como string
                if isinstance(datos['fecha'], str):
                    fecha_obj = datetime.strptime(str(datos['fecha']), "%Y-%m-%d")
                else:
                    fecha_obj = datos['fecha']

                datos['ano'] = fecha_obj.year
                datos['mes'] = fecha_obj.month
                # Convertir a string para Firestore (si es objeto)
                datos['fecha'] = fecha_obj.strftime("%Y-%m-%d")
            except Exception:
                pass  # Ignorar si la fecha es inválida
        return datos

    # ==================== MAPAS GLOBALES ====================

    @retry_on_quota_exceeded(max_retries=3, initial_delay=1.0)
    def obtener_mapa_global(self, coleccion_nombre: str) -> Dict[str, str]:
        """
        Obtiene un mapa simple (ID -> nombre) de una colección global.
        """
        try:
            mapa = {}
            docs = self.db.collection(coleccion_nombre).stream()
            for doc in docs:
                datos = doc.to_dict()
                mapa[doc.id] = datos.get('nombre', f"ID: {doc.id}")
            logger.info(f"Obtenido mapa para [{coleccion_nombre}]. Total: {len(mapa)} entradas.")
            return mapa
        except Exception as e:
            logger.error(f"Error al obtener mapa para [{coleccion_nombre}]: {e}", exc_info=True)
            raise e  # Propagar el error

    # ==================== EQUIPOS ====================

    @retry_on_quota_exceeded(max_retries=3, initial_delay=1.0)
    def obtener_equipos(self, activo: bool | None = None) -> list[dict]:
        """
        Lee colección 'equipos'. Si activo es True/False, acepta tanto booleanos como 1/0.
        """
        try:
            col = self.db.collection("equipos")
            if activo is True:
                col = col.where(filter=FieldFilter("activo", "in", [True, 1]))
            elif activo is False:
                col = col.where(filter=FieldFilter("activo", "in", [False, 0]))

            docs = list(col.stream())
            out = []
            for d in docs:
                data = d.to_dict()
                data["id"] = d.id
                out.append(data)
            logger.info(f"Obtenidos {len(out)} equipos (activo={activo})")
            return out
        except Exception as e:
            logger.error(f"Error al obtener equipos: {e}", exc_info=True)
            return []

    def obtener_equipo_por_id(self, equipo_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = self.db.collection('equipos').document(equipo_id).get()
            if doc.exists:
                equipo = doc.to_dict()
                equipo['id'] = doc.id
                return equipo
            return None
        except Exception as e:
            logger.error(f"Error al obtener equipo {equipo_id}: {e}")
            return None

    def agregar_equipo(self, datos: Dict[str, Any]) -> Optional[str]:
        try:
            datos['fecha_creacion'] = datetime.now()
            datos['fecha_modificacion'] = datetime.now()
            if 'activo' not in datos:
                datos['activo'] = True
            doc_ref = self.db.collection('equipos').add(datos)
            equipo_id = doc_ref[1].id
            logger.info(f"Equipo creado con ID: {equipo_id}")
            return equipo_id
        except Exception as e:
            logger.error(f"Error al agregar equipo: {e}")
            return None

    def editar_equipo(self, equipo_id: str, datos: Dict[str, Any]) -> bool:
        try:
            datos['fecha_modificacion'] = datetime.now()
            self.db.collection('equipos').document(equipo_id).update(datos)
            logger.info(f"Equipo {equipo_id} actualizado")
            return True
        except Exception as e:
            logger.error(f"Error al editar equipo {equipo_id}: {e}")
            return False

    def eliminar_equipo(self, equipo_id: str, eliminar_fisicamente: bool = False) -> bool:
        try:
            if eliminar_fisicamente:
                self.db.collection('equipos').document(equipo_id).delete()
                logger.info(f"Equipo {equipo_id} eliminado físicamente")
            else:
                self.db.collection('equipos').document(equipo_id).update({'activo': False})
                logger.info(f"Equipo {equipo_id} marcado como inactivo")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar equipo {equipo_id}: {e}")
            return False

    # ==================== ALQUILERES ====================

    def obtener_alquileres(self, filtros: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Obtiene alquileres con filtros opcionales.
        """
        try:
            query = self.db.collection('alquileres')

            if filtros:
                if 'fecha_inicio' in filtros:
                    query = query.where(filter=FieldFilter('fecha', '>=', filtros['fecha_inicio']))
                if 'fecha_fin' in filtros:
                    query = query.where(filter=FieldFilter('fecha', '<=', filtros['fecha_fin']))
                if 'equipo_id' in filtros:
                    query = query.where(filter=FieldFilter('equipo_id', '==', filtros['equipo_id']))
                if 'cliente_id' in filtros:
                    query = query.where(filter=FieldFilter('cliente_id', '==', filtros['cliente_id']))
                if 'operador_id' in filtros:
                    query = query.where(filter=FieldFilter('operador_id', '==', filtros['operador_id']))
                if 'pagado' in filtros:
                    query = query.where(filter=FieldFilter('pagado', '==', filtros['pagado']))

            query = query.order_by('fecha', direction=firestore.Query.DESCENDING)
            docs = query.stream()

            alquileres = []
            for doc in docs:
                alquiler = doc.to_dict()
                alquiler['id'] = doc.id
                alquileres.append(alquiler)

            logger.info(f"Obtenidos {len(alquileres)} alquileres con filtros: {filtros}")
            return alquileres

        except Exception as e:
            logger.error(f"Error al obtener alquileres: {e}", exc_info=True)
            raise e  # Propagar el error

    def obtener_alquiler_por_id(self, alquiler_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un único alquiler por su ID de documento."""
        try:
            doc = self.db.collection('alquileres').document(alquiler_id).get()
            if doc.exists:
                alquiler = doc.to_dict()
                alquiler['id'] = doc.id
                return alquiler
            return None
        except Exception as e:
            logger.error(f"Error al obtener alquiler {alquiler_id}: {e}")
            return None

    # ==================== MODIFICADO: registrar_alquiler ====================
    def registrar_alquiler(self, datos: Dict[str, Any]) -> Optional[str]:
        """
        Registra un nuevo alquiler con soporte de modalidades:
          horas (default), volumen, fijo.
        Campos esperados según modalidad:
          horas: horas, precio_por_hora
          volumen: volumen_generado, precio_por_unidad, unidad_volumen (opcional)
          fijo: monto_fijo
        Siempre guarda 'monto' calculado y 'modalidad_facturacion'.
        """
        try:
            datos['fecha_creacion'] = datetime.now()
            datos['fecha_modificacion'] = datetime.now()
            if 'pagado' not in datos:
                datos['pagado'] = False

            # Calcular monto según modalidad
            monto, modalidad = self._calcular_monto_alquiler(datos)
            datos['monto'] = monto
            datos['modalidad_facturacion'] = modalidad

            # Normalizar estructura adicional
            if modalidad == "volumen":
                datos.setdefault("unidad_volumen", datos.get("unidad_volumen") or "")
            elif modalidad == "fijo":
                # horas y precio_por_hora ya se pusieron a None en helper
                pass

            datos = self._agregar_fecha_ano_mes(datos)

            if 'transaccion_id' not in datos:
                datos['transaccion_id'] = str(uuid.uuid4())

            doc_id = datos['transaccion_id']
            self.db.collection('alquileres').document(doc_id).set(datos)
            logger.info(f"Alquiler registrado (modalidad={modalidad}) ID: {doc_id} monto={monto:,.2f}")
            return doc_id
        except Exception as e:
            logger.error(f"Error al registrar alquiler: {e}", exc_info=True)
            return None

    # ==================== MODIFICADO: editar_alquiler ====================
    def editar_alquiler(self, alquiler_id: str, datos: Dict[str, Any]) -> bool:
        """
        Edita un alquiler existente recalculando el monto según modalidad.
        Si no se pasa modalidad_facturacion, se conserva la original.
        """
        try:
            original = self.obtener_alquiler_por_id(alquiler_id) or {}
            if not original:
                logger.warning(f"editar_alquiler: alquiler {alquiler_id} no encontrado.")
                return False

            datos['fecha_modificacion'] = datetime.now()

            # Calcular monto usando datos nuevos + original como fallback
            monto, modalidad = self._calcular_monto_alquiler(datos, original)
            datos['monto'] = monto
            datos['modalidad_facturacion'] = modalidad

            # Ajustes de campos según modalidad
            if modalidad == "volumen":
                datos.setdefault("unidad_volumen", datos.get("unidad_volumen", original.get("unidad_volumen")) or "")
            elif modalidad == "fijo":
                pass  # ya se limpian horas en helper

            datos = self._agregar_fecha_ano_mes(datos)

            self.db.collection('alquileres').document(alquiler_id).update(datos)
            logger.info(f"Alquiler {alquiler_id} actualizado (modalidad={modalidad}) monto={monto:,.2f}")
            return True
        except Exception as e:
            logger.error(f"Error al editar alquiler {alquiler_id}: {e}", exc_info=True)
            return False

    def eliminar_alquiler(self, alquiler_id: str) -> bool:
        """Elimina un alquiler."""
        try:
            self.db.collection('alquileres').document(alquiler_id).delete()
            logger.info(f"Alquiler {alquiler_id} eliminado")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar alquiler {alquiler_id}: {e}")
            return False

    # ==================== GASTOS ====================

    def crear_gasto(self, data: dict) -> str | None:
        """
        Crea documento en colección 'gastos'.
        Espera campos: fecha (yyyy-MM-dd), equipo_id, cuenta_id, categoria_id, subcategoria_id,
                    descripcion, monto, comentario.
        Retorna doc.id o None.
        """
        try:
            data_clean = dict(data)
            data_clean["created_at"] = time.time()
            doc_ref = self.db.collection("gastos").add(data_clean)[1]
            return doc_ref.id
        except Exception as e:
            logger.error(f"crear_gasto error: {e}", exc_info=True)
            return None

    def actualizar_gasto(self, gasto_id: str, data: dict) -> bool:
        try:
            data_update = dict(data)
            data_update["updated_at"] = time.time()
            self.db.collection("gastos").document(gasto_id).update(data_update)
            return True
        except Exception as e:
            logger.error(f"actualizar_gasto error: {e}", exc_info=True)
            return False

    def eliminar_gasto(self, gasto_id: str) -> bool:
        try:
            self.db.collection("gastos").document(gasto_id).delete()
            return True
        except Exception as e:
            logger.error(f"eliminar_gasto error: {e}", exc_info=True)
            return False

    def obtener_gasto_por_id(self, gasto_id: str) -> dict | None:
        try:
            doc = self.db.collection("gastos").document(gasto_id).get()
            if doc.exists:
                d = doc.to_dict()
                d["id"] = doc.id
                return d
            return None
        except Exception as e:
            logger.error(f"obtener_gasto_por_id error: {e}", exc_info=True)
            return None

    def obtener_gastos(self, filtros: dict) -> list[dict]:
        """
        Carga gastos por rango de fecha y filtra en Python por equipo_id / cuenta_id / categoria_id
        aceptando equivalencia por string (soluciona mezcla de tipos int/str en datos históricos).
        filtros: {fecha_inicio, fecha_fin, equipo_id?, cuenta_id?, categoria_id?}
        """
        try:
            col = self.db.collection("gastos")

            fi = filtros.get("fecha_inicio")
            ff = filtros.get("fecha_fin")
            if fi:
                col = col.where(filter=FieldFilter("fecha", ">=", fi))
            if ff:
                col = col.where(filter=FieldFilter("fecha", "<=", ff))

            docs = list(col.stream())
            out = []
            # Filtros opcionales en Python (tolerantes a tipo)
            f_eq = filtros.get("equipo_id")
            f_ct = filtros.get("cuenta_id")
            f_cat = filtros.get("categoria_id")

            def eq_str(a, b):
                if a is None or b is None:
                    return False
                return str(a) == str(b)

            for d in docs:
                data = d.to_dict()
                data["id"] = d.id

                if f_eq is not None and not eq_str(data.get("equipo_id"), f_eq):
                    continue
                if f_ct is not None and not eq_str(data.get("cuenta_id"), f_ct):
                    continue
                if f_cat is not None and not eq_str(data.get("categoria_id"), f_cat):
                    continue

                out.append(data)

            out.sort(key=lambda x: x.get("fecha", ""))
            logger.info(f"Obtenidos {len(out)} gastos con filtros: {filtros}")
            return out

        except Exception as e:
            logger.error(f"obtener_gastos error: {e}", exc_info=True)
            return []

# ... (encabezado original y demás métodos sin cambios previos del archivo que ya te pasé)
# Asegúrate de tener el __init__ con `storage_manager` como parámetro e instalado en self.storage_manager

    def subir_archivo_gasto(self, gasto_id: str, fecha: str, ruta_local: str) -> tuple[bool, str | None]:
        """
        Sube archivo del gasto a Storage: gastos/YYYY/MM/gasto_<id>.<ext>
        Retorna (ok, storage_path).
        Además, si es posible, guarda 'archivo_url' (URL firmada) en el documento del gasto.
        """
        try:
            if not getattr(self, "storage_manager", None):
                logger.warning("subir_archivo_gasto: StorageManager no disponible.")
                return False, None

            from datetime import datetime as dtm
            from pathlib import Path

            try:
                dt = dtm.strptime(fecha, "%Y-%m-%d")
                anio = dt.year
                mes = f"{dt.month:02d}"
            except Exception:
                now = dtm.now()
                anio = now.year
                mes = f"{now.month:02d}"

            ext = Path(ruta_local).suffix.lower() or ".dat"
            storage_path = f"gastos/{anio}/{mes}/gasto_{gasto_id}{ext}"

            blob = self.storage_manager.bucket.blob(storage_path)
            guess = getattr(self.storage_manager, "_guess_content_type_from_ext", None)
            content_type = guess(ext) if callable(guess) else None
            blob.upload_from_filename(ruta_local, content_type=content_type)

            # Con U-BLA (uniform bucket-level access) no usar ACL públicas
            url_firmada = None
            try:
                gen = getattr(self.storage_manager, "generate_signed_url", None) or getattr(self.storage_manager, "generar_url_firmada", None)
                if callable(gen):
                    # 7 días por coherencia con conduce
                    url_firmada = gen(storage_path, expiration_days=7) if gen.__code__.co_argcount >= 3 else gen(storage_path, 7)
            except Exception as e:
                logger.warning(f"No se pudo generar URL firmada para gasto {gasto_id}: {e}")

            # Guardar referencia en el documento (no rompe si campos no se usan)
            try:
                update = {"archivo_storage_path": storage_path}
                if url_firmada:
                    update["archivo_url"] = url_firmada
                self.db.collection("gastos").document(gasto_id).update(update)
            except Exception as e:
                logger.warning(f"No se pudo actualizar doc de gasto {gasto_id} con URL: {e}")

            logger.info(f"Archivo gasto subido: {storage_path}")
            return True, storage_path
        except Exception as e:
            logger.error(f"subir_archivo_gasto error: {e}", exc_info=True)
            return False, None

    def subir_archivo_pago_operador(self, pago_id: str, fecha: str, ruta_local: str) -> tuple[bool, str | None]:
        """
        Sube comprobante del pago a Storage: pagos_operadores/YYYY/MM/pago_<id>.<ext>
        Retorna (ok, storage_path).
        Además, si es posible, guarda 'comprobante_url' (URL firmada) en el documento del pago.
        """
        try:
            if not getattr(self, "storage_manager", None):
                logger.warning("subir_archivo_pago_operador: StorageManager no disponible.")
                return False, None

            from datetime import datetime as dtm
            from pathlib import Path

            try:
                dt = dtm.strptime(fecha, "%Y-%m-%d")
                anio = dt.year
                mes = f"{dt.month:02d}"
            except Exception:
                now = dtm.now()
                anio = now.year
                mes = f"{now.month:02d}"

            ext = Path(ruta_local).suffix.lower() or ".dat"
            storage_path = f"pagos_operadores/{anio}/{mes}/pago_{pago_id}{ext}"
            blob = self.storage_manager.bucket.blob(storage_path)
            guess = getattr(self.storage_manager, "_guess_content_type_from_ext", None)
            content_type = guess(ext) if callable(guess) else None
            blob.upload_from_filename(ruta_local, content_type=content_type)

            url_firmada = None
            try:
                gen = getattr(self.storage_manager, "generate_signed_url", None) or getattr(self.storage_manager, "generar_url_firmada", None)
                if callable(gen):
                    url_firmada = gen(storage_path, expiration_days=7) if gen.__code__.co_argcount >= 3 else gen(storage_path, 7)
            except Exception as e:
                logger.warning(f"No se pudo generar URL firmada para pago_operador {pago_id}: {e}")

            # Guardar referencia en el documento del pago
            try:
                update = {"comprobante_storage_path": storage_path}
                if url_firmada:
                    update["comprobante_url"] = url_firmada
                self.db.collection("pagos_operadores").document(pago_id).update(update)
            except Exception as e:
                logger.warning(f"No se pudo actualizar doc de pago_operador {pago_id} con URL: {e}")

            logger.info(f"Archivo pago subido: {storage_path}")
            return True, storage_path
        except Exception as e:
            logger.error(f"subir_archivo_pago_operador error: {e}", exc_info=True)
            return False, None
# ... (resto del archivo sin cambios)
    def registrar_gasto_equipo(self, datos: Dict[str, Any]) -> Optional[str]:
        """Registra un gasto asociado a un equipo."""
        try:
            datos['tipo'] = 'Gasto'  # Aseguramos el tipo
            datos['fecha_creacion'] = datetime.now()
            datos['fecha_modificacion'] = datetime.now()
            datos = self._agregar_fecha_ano_mes(datos)

            if 'id' not in datos:
                datos['id'] = str(uuid.uuid4())

            doc_id = datos['id']
            self.db.collection('gastos').document(doc_id).set(datos)
            logger.info(f"Gasto registrado con ID: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error al registrar gasto: {e}")
            return None

    def editar_gasto(self, gasto_id: str, datos: Dict[str, Any]) -> bool:
        """Edita un gasto existente."""
        try:
            datos['fecha_modificacion'] = datetime.now()
            datos = self._agregar_fecha_ano_mes(datos)
            self.db.collection('gastos').document(gasto_id).update(datos)
            logger.info(f"Gasto {gasto_id} actualizado")
            return True
        except Exception as e:
            logger.error(f"Error al editar gasto {gasto_id}: {e}")
            return False

    # ==================== ENTIDADES (CLIENTES Y OPERADORES) ====================

    @retry_on_quota_exceeded(max_retries=3, initial_delay=1.0)
    def obtener_entidades(self, tipo: str = None, activo: bool | None = None) -> list[dict]:
        """
        Lee colección 'entidades'. Si activo es True/False, acepta tanto booleanos como 1/0.
        """
        try:
            col = self.db.collection("entidades")
            if tipo:
                col = col.where(filter=FieldFilter("tipo", "==", tipo))
            if activo is True:
                col = col.where(filter=FieldFilter("activo", "in", [True, 1]))
            elif activo is False:
                col = col.where(filter=FieldFilter("activo", "in", [False, 0]))

            docs = list(col.stream())
            out = []
            for d in docs:
                data = d.to_dict()
                data["id"] = d.id
                out.append(data)
            logger.info(f"Obtenidas {len(out)} entidades (tipo={tipo}, activo={activo})")
            return out
        except Exception as e:
            logger.error(f"Error al obtener entidades: {e}", exc_info=True)
            return []

    def obtener_entidad_por_id(self, entidad_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = self.db.collection('entidades').document(entidad_id).get()
            if doc.exists:
                entidad = doc.to_dict()
                entidad['id'] = doc.id
                return entidad
            return None
        except Exception as e:
            logger.error(f"Error al obtener entidad {entidad_id}: {e}")
            return None

    def agregar_entidad(self, datos: Dict[str, Any]) -> Optional[str]:
        try:
            datos['fecha_creacion'] = datetime.now()
            datos['fecha_modificacion'] = datetime.now()
            if 'activo' not in datos:
                datos['activo'] = True
            doc_ref = self.db.collection('entidades').add(datos)
            entidad_id = doc_ref[1].id
            logger.info(f"Entidad creada con ID: {entidad_id}")
            return entidad_id
        except Exception as e:
            logger.error(f"Error al agregar entidad: {e}")
            return None

    def editar_entidad(self, entidad_id: str, datos: Dict[str, Any]) -> bool:
        try:
            datos['fecha_modificacion'] = datetime.now()
            self.db.collection('entidades').document(entidad_id).update(datos)
            logger.info(f"Entidad {entidad_id} actualizada")
            return True
        except Exception as e:
            logger.error(f"Error al editar entidad {entidad_id}: {e}")
            return False

    def eliminar_entidad(self, entidad_id: str, eliminar_fisicamente: bool = False) -> bool:
        try:
            if eliminar_fisicamente:
                self.db.collection('entidades').document(entidad_id).delete()
                logger.info(f"Entidad {entidad_id} eliminada físicamente")
            else:
                self.db.collection('entidades').document(entidad_id).update({'activo': False})
                logger.info(f"Entidad {entidad_id} marcada como inactiva")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar entidad {entidad_id}: {e}")
            return False

    # ==================== MANTENIMIENTOS ====================

    def obtener_mantenimientos(self, equipo_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene mantenimientos, opcionalmente filtrados por equipo.
        """
        try:
            query = self.db.collection('mantenimientos')
            if equipo_id:
                query = query.where(filter=FieldFilter('equipo_id', '==', equipo_id))
            query = query.order_by('fecha', direction=firestore.Query.DESCENDING)
            docs = query.stream()
            mantenimientos = []
            for doc in docs:
                mant = doc.to_dict()
                mant['id'] = doc.id
                mantenimientos.append(mant)
            logger.info(f"Obtenidos {len(mantenimientos)} mantenimientos")
            return mantenimientos
        except Exception as e:
            logger.error(f"Error al obtener mantenimientos: {e}", exc_info=True)
            raise e  # Propagar el error

    def obtener_mantenimiento_por_id(self, mantenimiento_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = self.db.collection('mantenimientos').document(mantenimiento_id).get()
            if doc.exists:
                mant = doc.to_dict()
                mant['id'] = doc.id
                return mant
            return None
        except Exception as e:
            logger.error(f"Error al obtener mantenimiento {mantenimiento_id}: {e}")
            return None

    def registrar_mantenimiento(self, datos: Dict[str, Any]) -> Optional[str]:
        try:
            datos['fecha_creacion'] = datetime.now()
            datos['fecha_modificacion'] = datetime.now()
            doc_ref = self.db.collection('mantenimientos').add(datos)
            mant_id = doc_ref[1].id
            logger.info(f"Mantenimiento registrado con ID: {mant_id}")
            return mant_id
        except Exception as e:
            logger.error(f"Error al registrar mantenimiento: {e}")
            return None

    def editar_mantenimiento(self, mantenimiento_id: str, datos: Dict[str, Any]) -> bool:
        try:
            datos['fecha_modificacion'] = datetime.now()
            self.db.collection('mantenimientos').document(mantenimiento_id).update(datos)
            logger.info(f"Mantenimiento {mantenimiento_id} actualizado")
            return True
        except Exception as e:
            logger.error(f"Error al editar mantenimiento {mantenimiento_id}: {e}")
            return False

    def eliminar_mantenimiento(self, mantenimiento_id: str) -> bool:
        try:
            self.db.collection('mantenimientos').document(mantenimiento_id).delete()
            logger.info(f"Mantenimiento {mantenimiento_id} eliminado")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar mantenimiento {mantenimiento_id}: {e}")
            return False

    # ==================== PAGOS A OPERADORES ====================

    def crear_pago_operador(self, data: dict) -> str | None:
        """
        Crea documento en colección 'pagos_operadores'.
        Campos esperados: fecha (YYYY-MM-DD), operador_id (str), concepto, metodo_pago, monto (float), nota.
        """
        try:
            payload = dict(data)
            payload["created_at"] = time.time()
            doc_ref = self.db.collection("pagos_operadores").add(payload)[1]
            return doc_ref.id
        except Exception as e:
            logger.error(f"crear_pago_operador error: {e}", exc_info=True)
            return None

    def actualizar_pago_operador(self, pago_id: str, data: dict) -> bool:
        try:
            payload = dict(data)
            payload["updated_at"] = time.time()
            self.db.collection("pagos_operadores").document(pago_id).update(payload)
            return True
        except Exception as e:
            logger.error(f"actualizar_pago_operador error: {e}", exc_info=True)
            return False

    def eliminar_pago_operador(self, pago_id: str) -> bool:
        try:
            self.db.collection("pagos_operadores").document(pago_id).delete()
            return True
        except Exception as e:
            logger.error(f"eliminar_pago_operador error: {e}", exc_info=True)
            return False

    def obtener_pago_operador_por_id(self, pago_id: str) -> dict | None:
        try:
            doc = self.db.collection("pagos_operadores").document(pago_id).get()
            if doc.exists:
                d = doc.to_dict() or {}
                d["id"] = doc.id
                return d
            return None
        except Exception as e:
            logger.error(f"obtener_pago_operador_por_id error: {e}", exc_info=True)
            return None

    def obtener_pagos_operadores(self, filtros: dict) -> list[dict]:
        """
        filtros: fecha_inicio?, fecha_fin?, operador_id?, metodo_pago?
        Si no se pasa fecha_inicio/fin, no filtra por fecha en Firestore.
        """
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter as QFieldFilter
            col = self.db.collection("pagos_operadores")

            fi = filtros.get("fecha_inicio")
            ff = filtros.get("fecha_fin")
            if fi:
                col = col.where(filter=QFieldFilter("fecha", ">=", fi))
            if ff:
                col = col.where(filter=QFieldFilter("fecha", "<=", ff))

            docs = list(col.stream())
            out = []
            f_op = filtros.get("operador_id")
            f_met = filtros.get("metodo_pago")

            for d in docs:
                data = d.to_dict() or {}
                data["id"] = d.id
                if f_op is not None and str(data.get("operador_id")) != str(f_op):
                    continue
                if f_met is not None and (data.get("metodo_pago") or "") != f_met:
                    continue
                out.append(data)

            out.sort(key=lambda x: x.get("fecha", ""))
            logger.info(f"Obtenidos {len(out)} pagos a operadores")
            return out
        except Exception as e:
            logger.error(f"obtener_pagos_operadores error: {e}", exc_info=True)
            return []


    def registrar_pago_operador(self, datos: Dict[str, Any]) -> Optional[str]:
        try:
            datos['fecha_creacion'] = datetime.now()
            datos['fecha_modificacion'] = datetime.now()
            datos = self._agregar_fecha_ano_mes(datos)
            if 'id' not in datos:
                datos['id'] = str(uuid.uuid4())
            doc_id = datos['id']
            self.db.collection('pagos_operadores').document(doc_id).set(datos)
            logger.info(f"Pago a operador registrado con ID: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error al registrar pago a operador: {e}")
            return None

    def editar_pago_operador(self, pago_id: str, datos: Dict[str, Any]) -> bool:
        try:
            datos['fecha_modificacion'] = datetime.now()
            datos = self._agregar_fecha_ano_mes(datos)
            self.db.collection('pagos_operadores').document(pago_id).update(datos)
            logger.info(f"Pago a operador {pago_id} actualizado")
            return True
        except Exception as e:
            logger.error(f"Error al editar pago a operador {pago_id}: {e}")
            return False

    def eliminar_pago_operador(self, pago_id: str) -> bool:
        try:
            self.db.collection('pagos_operadores').document(pago_id).delete()
            logger.info(f"Pago a operador {pago_id} eliminado")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar pago a operador {pago_id}: {e}")
            return False

    # ==================== UTILIDADES (DASHBOARD) ====================

    def obtener_estadisticas_dashboard(self, filtros: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas para el dashboard.
        """
        try:
            query_ingresos = self.db.collection('alquileres')
            query_gastos = self.db.collection('gastos')

            if filtros:
                if 'ano' in filtros:
                    query_ingresos = query_ingresos.where(filter=FieldFilter('ano', '==', filtros['ano']))
                    query_gastos = query_gastos.where(filter=FieldFilter('ano', '==', filtros['ano']))
                if 'mes' in filtros:
                    query_ingresos = query_ingresos.where(filter=FieldFilter('mes', '==', filtros['mes']))
                    query_gastos = query_gastos.where(filter=FieldFilter('mes', '==', filtros['mes']))
                if 'equipo_id' in filtros:
                    query_ingresos = query_ingresos.where(filter=FieldFilter('equipo_id', '==', filtros['equipo_id']))
                    query_gastos = query_gastos.where(filter=FieldFilter('equipo_id', '==', filtros['equipo_id']))

            ingresos = list(query_ingresos.stream())
            gastos = list(query_gastos.stream())

            total_ingresos = sum(doc.to_dict().get('monto', 0) for doc in ingresos)
            total_gastos = sum(doc.to_dict().get('monto', 0) for doc in gastos)

            utilidad = total_ingresos - total_gastos

            # Saldo pendiente (Total, sin filtro de fecha)
            pendientes = self.db.collection('alquileres').where(filter=FieldFilter('pagado', '==', False)).stream()
            saldo_pendiente = sum(doc.to_dict().get('monto', 0) for doc in pendientes)

            # Contar equipos activos
            try:
                equipos_activos = len(self.obtener_equipos(activo=True))
            except Exception:
                logger.warning("Falta índice para 'equipos activos' en Dashboard, contando todos.")
                equipos_activos = len(self.obtener_equipos(activo=None))

            return {
                'ingresos_mes': total_ingresos,
                'gastos_mes': total_gastos,
                'utilidad': utilidad,
                'equipos_activos': equipos_activos,
                'saldo_pendiente': saldo_pendiente,
                'ingresos_data': [doc.to_dict() for doc in ingresos]  # Pasa los datos para tops
            }
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}", exc_info=True)
            raise e  # Propagar el error

    # ==================== FUNCIONES PARA FILTROS DE FECHA DINÁMICOS ====================

    def obtener_fecha_primera_transaccion_alquileres(self) -> Optional[str]:
        """
        Obtiene la fecha de la primera transacción de alquileres en Firestore.
        """
        try:
            query = self.db.collection('alquileres').order_by('fecha').limit(1)
            docs = list(query.stream())

            if docs:
                primera_fecha = docs[0].to_dict().get('fecha')
                logger.info(f"Primera fecha de alquileres: {primera_fecha}")
                return primera_fecha
            else:
                logger.warning("No hay alquileres en la base de datos")
                return None
        except Exception as e:
            logger.error(f"Error al obtener primera fecha de alquileres: {e}", exc_info=True)
            return None

    def obtener_fecha_primera_transaccion_gastos(self) -> Optional[str]:
        """
        Obtiene la fecha de la primera transacción de gastos en Firestore.
        """
        try:
            query = self.db.collection('gastos').order_by('fecha').limit(1)
            docs = list(query.stream())

            if docs:
                primera_fecha = docs[0].to_dict().get('fecha')
                logger.info(f"Primera fecha de gastos: {primera_fecha}")
                return primera_fecha
            else:
                logger.warning("No hay gastos en la base de datos")
                return None
        except Exception as e:
            logger.error(f"Error al obtener primera fecha de gastos: {e}", exc_info=True)
            return None

    def obtener_fecha_primera_transaccion_pagos(self) -> str | None:
        """
        Retorna la fecha (YYYY-MM-DD) más antigua en la colección 'pagos_operadores',
        o None si no hay documentos.
        """
        try:
            snaps = list(self.db.collection("pagos_operadores").stream())
            fechas = []
            for s in snaps:
                data = s.to_dict() or {}
                f = data.get("fecha")
                if isinstance(f, str) and f:
                    fechas.append(f)
            if not fechas:
                return None
            return sorted(fechas)[0]
        except Exception as e:
            logger.error(f"obtener_fecha_primera_transaccion_pagos error: {e}", exc_info=True)
            return None

    def obtener_fecha_primera_transaccion_cliente(self, cliente_id: str) -> Optional[str]:
        """
        Obtiene la fecha de la primera transacción de un cliente específico.
        """
        try:
            query = (self.db.collection('alquileres')
                     .where(filter=FieldFilter('cliente_id', '==', cliente_id))
                     .order_by('fecha')
                     .limit(1))
            docs = list(query.stream())

            if docs:
                primera_fecha = docs[0].to_dict().get('fecha')
                logger.info(f"Primera fecha de transacción para cliente {cliente_id}: {primera_fecha}")
                return primera_fecha
            else:
                logger.warning(f"No hay transacciones para el cliente {cliente_id}")
                return None
        except Exception as e:
            logger.error(f"Error al obtener primera fecha de cliente {cliente_id}: {e}", exc_info=True)
            return None

    def obtener_fecha_primera_transaccion_equipo(self, equipo_id: str) -> Optional[str]:
        """
        Obtiene la fecha de la primera transacción de un equipo específico.
        Considera tanto alquileres como gastos del equipo.
        """
        try:
            # Buscar en alquileres
            query_alquileres = (self.db.collection('alquileres')
                                .where(filter=FieldFilter('equipo_id', '==', equipo_id))
                                .order_by('fecha')
                                .limit(1))
            docs_alquileres = list(query_alquileres.stream())

            # Buscar en gastos
            query_gastos = (self.db.collection('gastos')
                            .where(filter=FieldFilter('equipo_id', '==', equipo_id))
                            .order_by('fecha')
                            .limit(1))
            docs_gastos = list(query_gastos.stream())

            fechas = []
            if docs_alquileres:
                fechas.append(docs_alquileres[0].to_dict().get('fecha'))
            if docs_gastos:
                fechas.append(docs_gastos[0].to_dict().get('fecha'))

            if fechas:
                primera_fecha = min(fechas)
                logger.info(f"Primera fecha de transacción para equipo {equipo_id}: {primera_fecha}")
                return primera_fecha
            else:
                logger.warning(f"No hay transacciones para el equipo {equipo_id}")
                return None
        except Exception as e:
            logger.error(f"Error al obtener primera fecha de equipo {equipo_id}: {e}", exc_info=True)
            return None

    def obtener_fecha_primera_transaccion_operador(self, operador_id: str) -> Optional[str]:
        """
        Obtiene la fecha de la primera transacción de un operador específico.
        Considera tanto alquileres como pagos al operador.
        """
        try:
            # Buscar en alquileres
            query_alquileres = (self.db.collection('alquileres')
                                .where(filter=FieldFilter('operador_id', '==', operador_id))
                                .order_by('fecha')
                                .limit(1))
            docs_alquileres = list(query_alquileres.stream())

            # Buscar en pagos a operadores
            query_pagos = (self.db.collection('pagos_operadores')
                           .where(filter=FieldFilter('operador_id', '==', operador_id))
                           .order_by('fecha')
                           .limit(1))
            docs_pagos = list(query_pagos.stream())

            fechas = []
            if docs_alquileres:
                fechas.append(docs_alquileres[0].to_dict().get('fecha'))
            if docs_pagos:
                fechas.append(docs_pagos[0].to_dict().get('fecha'))

            if fechas:
                primera_fecha = min(fechas)
                logger.info(f"Primera fecha de transacción para operador {operador_id}: {primera_fecha}")
                return primera_fecha
            else:
                logger.warning(f"No hay transacciones para el operador {operador_id}")
                return None
        except Exception as e:
            logger.error(f"Error al obtener primera fecha de operador {operador_id}: {e}", exc_info=True)
            return None

    # ==================== REPORTES Y ESTADO DE CUENTA ====================

    def obtener_alquileres_para_reporte(
        self,
        cliente_id: Optional[str] = None,
        equipo_id: Optional[str] = None,
        operador_id: Optional[str] = None,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene alquileres para reportes con filtros opcionales.
        Incluye información relacionada (cliente, equipo, operador).
        """
        try:
            query = self.db.collection('alquileres')

            if cliente_id:
                query = query.where(filter=FieldFilter('cliente_id', '==', cliente_id))
            if equipo_id:
                query = query.where(filter=FieldFilter('equipo_id', '==', equipo_id))
            if operador_id:
                query = query.where(filter=FieldFilter('operador_id', '==', operador_id))
            if fecha_inicio:
                query = query.where(filter=FieldFilter('fecha', '>=', fecha_inicio))
            if fecha_fin:
                query = query.where(filter=FieldFilter('fecha', '<=', fecha_fin))

            query = query.order_by('fecha')
            docs = query.stream()

            alquileres = []
            for doc in docs:
                alquiler = doc.to_dict()
                alquiler['id'] = doc.id
                alquileres.append(alquiler)

            logger.info(f"Obtenidos {len(alquileres)} alquileres para reporte")
            return alquileres
        except Exception as e:
            logger.error(f"Error al obtener alquileres para reporte: {e}", exc_info=True)
            return []

    # ==================== GESTIÓN DE ABONOS ====================

    def obtener_abonos(
        self,
        cliente_id: Optional[str] = None,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene abonos de clientes con filtros opcionales.
        """
        try:
            query = self.db.collection('abonos')

            if cliente_id:
                query = query.where(filter=FieldFilter('cliente_id', '==', cliente_id))
            if fecha_inicio:
                query = query.where(filter=FieldFilter('fecha', '>=', fecha_inicio))
            if fecha_fin:
                query = query.where(filter=FieldFilter('fecha', '<=', fecha_fin))

            query = query.order_by('fecha', direction=firestore.Query.DESCENDING)
            docs = query.stream()

            abonos = []
            for doc in docs:
                abono = doc.to_dict()
                abono['id'] = doc.id
                abonos.append(abono)

            logger.info(f"Obtenidos {len(abonos)} abonos")
            return abonos
        except Exception as e:
            logger.error(f"Error al obtener abonos: {e}", exc_info=True)
            return []

    def crear_abono(self, datos: Dict[str, Any]) -> Optional[str]:
        """
        Crea un nuevo abono en Firestore.
        """
        try:
            datos['fecha_creacion'] = datetime.now()
            datos['fecha_modificacion'] = datetime.now()
            datos = self._agregar_fecha_ano_mes(datos)

            if 'id' not in datos:
                datos['id'] = str(uuid.uuid4())

            doc_id = datos['id']
            self.db.collection('abonos').document(doc_id).set(datos)
            logger.info(f"Abono creado con ID: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error al crear abono: {e}", exc_info=True)
            return None

    def editar_abono(self, abono_id: str, datos: Dict[str, Any]) -> bool:
        """
        Edita un abono existente.
        """
        try:
            datos['fecha_modificacion'] = datetime.now()
            datos = self._agregar_fecha_ano_mes(datos)
            self.db.collection('abonos').document(abono_id).update(datos)
            logger.info(f"Abono {abono_id} actualizado")
            return True
        except Exception as e:
            logger.error(f"Error al editar abono {abono_id}: {e}", exc_info=True)
            return False

    def eliminar_abono(self, abono_id: str) -> bool:
        """
        Elimina un abono.
        """
        try:
            self.db.collection('abonos').document(abono_id).delete()
            logger.info(f"Abono {abono_id} eliminado")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar abono {abono_id}: {e}", exc_info=True)
            return False

    def calcular_deuda_cliente(
        self,
        cliente_id: str,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calcula la deuda de un cliente (facturado - abonado).
        """
        try:
            # Obtener total facturado (alquileres)
            query_alquileres = self.db.collection('alquileres').where(
                filter=FieldFilter('cliente_id', '==', cliente_id)
            )
            if fecha_inicio:
                query_alquileres = query_alquileres.where(
                    filter=FieldFilter('fecha', '>=', fecha_inicio)
                )
            if fecha_fin:
                query_alquileres = query_alquileres.where(
                    filter=FieldFilter('fecha', '<=', fecha_fin)
                )

            alquileres = list(query_alquileres.stream())
            total_facturado = sum(doc.to_dict().get('monto', 0) for doc in alquileres)

            # Obtener total abonado
            query_abonos = self.db.collection('abonos').where(
                filter=FieldFilter('cliente_id', '==', cliente_id)
            )
            if fecha_inicio:
                query_abonos = query_abonos.where(
                    filter=FieldFilter('fecha', '>=', fecha_inicio)
                )
            if fecha_fin:
                query_abonos = query_abonos.where(
                    filter=FieldFilter('fecha', '<=', fecha_fin)
                )

            abonos = list(query_abonos.stream())
            total_abonado = sum(doc.to_dict().get('monto', 0) for doc in abonos)

            saldo = total_facturado - total_abonado

            logger.info(
                f"Deuda cliente {cliente_id}: "
                f"Facturado={total_facturado}, Abonado={total_abonado}, Saldo={saldo}"
            )

            return {
                'total_facturado': total_facturado,
                'total_abonado': total_abonado,
                'saldo': saldo
            }
        except Exception as e:
            logger.error(f"Error al calcular deuda del cliente {cliente_id}: {e}", exc_info=True)
            return {
                'total_facturado': 0,
                'total_abonado': 0,
                'saldo': 0
            }

    # ==================== CUENTAS ====================

    def obtener_cuentas(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de cuentas desde la colección 'cuentas'.
        """
        try:
            docs = self.db.collection("cuentas").order_by("nombre").stream()
            cuentas = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                cuentas.append(data)
            logger.info(f"Obtenidas {len(cuentas)} cuentas")
            return cuentas
        except Exception as e:
            logger.error(f"Error al obtener cuentas: {e}", exc_info=True)
            return []

    # ==================== FACTURAS PENDIENTES (ABONOS) ====================

    def obtener_facturas_pendientes_cliente(self, cliente_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene una lista de facturas (alquileres) pendientes de pago de un cliente,
        ordenadas por fecha ascendente.
        """
        try:
            query = (
                self.db.collection("alquileres")
                .where(filter=FieldFilter("cliente_id", "==", cliente_id))
                .where(filter=FieldFilter("pagado", "==", False))
                .order_by("fecha")
            )
            docs = list(query.stream())
            facturas = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                facturas.append(data)
            logger.info(f"Obtenidas {len(facturas)} facturas pendientes para cliente {cliente_id}")
            return facturas
        except Exception as e:
            logger.error(f"Error al obtener facturas pendientes para cliente {cliente_id}: {e}", exc_info=True)
            return []

    def _recalcular_estado_pago_alquiler(self, alquiler_id: str):
        """
        Recalcula el campo 'pagado' de un alquiler sumando los pagos de su subcolección 'pagos'.
        """
        try:
            doc_alquiler = self.db.collection("alquileres").document(alquiler_id).get()
            if not doc_alquiler.exists:
                logger.warning(f"Alquiler {alquiler_id} no existe al recalcular pagos.")
                return

            alquiler_data = doc_alquiler.to_dict()
            monto_total = float(alquiler_data.get("monto", 0) or 0)

            pagos_docs = self.db.collection("alquileres").document(alquiler_id).collection("pagos").stream()
            total_pagado = 0.0
            for pdoc in pagos_docs:
                pdata = pdoc.to_dict()
                total_pagado += float(pdata.get("monto", 0) or 0)

            pagado_flag = total_pagado >= monto_total and monto_total > 0

            self.db.collection("alquileres").document(alquiler_id).update(
                {"pagado": pagado_flag}
            )
            logger.info(
                f"Recalculado estado de pago para alquiler {alquiler_id}: "
                f"monto_total={monto_total}, total_pagado={total_pagado}, pagado={pagado_flag}"
            )
        except Exception as e:
            logger.error(f"Error al recalcular estado de pago para alquiler {alquiler_id}: {e}", exc_info=True)

    def registrar_abono_general_cliente(self, datos_pago: Dict[str, Any]):
        """
        Registra un abono general de un cliente y lo aplica a las facturas pendientes,
        de la más antigua a la más reciente.
        """
        try:
            cliente_id = datos_pago["cliente_id"]
            monto_abonar = float(datos_pago["monto"])
            fecha_abono = datos_pago["fecha"]
            cuenta_id = datos_pago.get("cuenta_id")
            comentario = datos_pago.get("comentario", "")

            if monto_abonar <= 0:
                raise ValueError("El monto del abono debe ser mayor que cero.")

            pendientes = self.obtener_facturas_pendientes_cliente(cliente_id)
            if not pendientes:
                return "Este cliente no tiene facturas pendientes de pago."

            monto_restante_abono = monto_abonar

            for factura in pendientes:
                if monto_restante_abono <= 0:
                    break

                alquiler_id = factura["id"]
                monto_factura = float(factura.get("monto", 0) or 0)

                pagos_docs = (
                    self.db.collection("alquileres")
                    .document(alquiler_id)
                    .collection("pagos")
                    .stream()
                )
                total_previo_pagado = 0.0
                for pdoc in pagos_docs:
                    pdata = pdoc.to_dict()
                    total_previo_pagado += float(pdata.get("monto", 0) or 0)

                monto_pendiente_factura = monto_factura - total_previo_pagado
                if monto_pendiente_factura <= 0:
                    continue

                monto_a_aplicar = min(monto_restante_abono, monto_pendiente_factura)

                pago_data = {
                    "fecha": fecha_abono,
                    "monto": monto_a_aplicar,
                    "comentario": comentario,
                    "cliente_id": cliente_id,
                }
                if cuenta_id:
                    pago_data["cuenta_id"] = cuenta_id

                pago_data = self._agregar_fecha_ano_mes(pago_data)
                pago_id = str(uuid.uuid4())

                self.db.collection("alquileres").document(alquiler_id).collection("pagos").document(pago_id).set(
                    pago_data
                )

                self._recalcular_estado_pago_alquiler(alquiler_id)

                monto_restante_abono -= monto_a_aplicar

            abono_resumen = {
                "cliente_id": cliente_id,
                "fecha": fecha_abono,
                "monto": monto_abonar,
                "comentario": comentario,
            }
            if cuenta_id:
                abono_resumen["cuenta_id"] = cuenta_id

            self.crear_abono(abono_resumen)

            logger.info(
                f"Abono general registrado para cliente {cliente_id} por monto {monto_abonar}. "
                f"Restante sin aplicar: {monto_restante_abono}"
            )
            return True

        except ValueError as ve:
            logger.warning(f"Validación al registrar abono general: {ve}")
            return str(ve)
        except Exception as e:
            logger.error(f"Error al registrar abono general de cliente: {e}", exc_info=True)
            return False

    def obtener_subcategorias_catalogo(self) -> list[dict]:
        """
        Retorna un catálogo de subcategorías con su categoría.
        """
        try:
            out = []
            for doc in self.db.collection("subcategorias").stream():
                d = doc.to_dict() or {}
                item = {
                    "id": str(doc.id),
                    "nombre": d.get("nombre", str(doc.id)),
                    "categoria_id": str(d.get("categoria_id")) if d.get("categoria_id") not in (None, "") else None,
                }
                out.append(item)
            return out
        except Exception as e:
            logger.error(f"obtener_subcategorias_catalogo error: {e}", exc_info=True)
            return []

    def ensure_categoria(self, nombre: str) -> str | None:
        """
        Retorna el id (doc.id) de la categoría con 'nombre'; si no existe, la crea.
        """
        try:
            col = self.db.collection("categorias")
            for d in col.stream():
                data = d.to_dict() or {}
                if str(data.get("nombre", "")).strip().lower() == nombre.strip().lower():
                    return str(d.id)
            ref = col.document()
            ref.set({"nombre": nombre})
            return str(ref.id)
        except Exception as e:
            logger.error(f"ensure_categoria error: {e}", exc_info=True)
            return None

    def ensure_subcategoria(self, nombre: str, categoria_id: str) -> str | None:
        """
        Retorna el id (doc.id) de la subcategoría con 'nombre' y 'categoria_id'; si no existe, la crea.
        """
        try:
            col = self.db.collection("subcategorias")
            for d in col.stream():
                data = d.to_dict() or {}
                if (str(data.get("nombre", "")).strip().lower() == nombre.strip().lower()
                        and str(data.get("categoria_id") or "") == str(categoria_id)):
                    return str(d.id)
            ref = col.document()
            ref.set({"nombre": nombre, "categoria_id": str(categoria_id)})
            return str(ref.id)
        except Exception as e:
            logger.error(f"ensure_subcategoria error: {e}", exc_info=True)
            return None

    def ensure_categoria_y_subcategoria_pago_operador(self, equipo_id: str | None) -> tuple[str | None, str | None]:
        """
        Asegura:
        - categoría 'PAGO HRS OPERADOR'
        - subcategoría = nombre del equipo (si se puede resolver), bajo esa categoría.
        """
        try:
            cat_id = self.ensure_categoria("PAGO HRS OPERADOR")
            sub_id = None
            equipo_nombre = None
            if equipo_id:
                edoc = self.db.collection("equipos").document(str(equipo_id)).get()
                if edoc.exists:
                    d = edoc.to_dict() or {}
                    equipo_nombre = d.get("nombre") or d.get("equipo")
            if cat_id and equipo_nombre:
                sub_id = self.ensure_subcategoria(equipo_nombre, cat_id)
            return cat_id, sub_id
        except Exception as e:
            logger.error(f"ensure_categoria_y_subcategoria_pago_operador error: {e}", exc_info=True)
            return None, None

    def obtener_cliente_y_ubicacion_equipo_actual(self, equipo_id: str) -> dict | None:
        """
        Busca el último alquiler del equipo para inferir cliente y ubicación actuales.
        """
        try:
            snaps = list(self.db.collection("alquileres").where("equipo_id", "==", str(equipo_id)).stream())
            if not snaps:
                return None
            clientes_map = {}
            if hasattr(self, "obtener_mapa_global"):
                clientes_map = self.obtener_mapa_global("clientes") or {}
            ultimo = sorted((s.to_dict() for s in snaps), key=lambda x: x.get("fecha", ""))[-1]
            cid = str(ultimo.get("cliente_id") or "")
            cliente_nombre = clientes_map.get(cid, cid) if cid else ""
            return {"cliente": cliente_nombre, "ubicacion": ultimo.get("ubicacion", "") or ""}
        except Exception as e:
            logger.error(f"obtener_cliente_y_ubicacion_equipo_actual error: {e}", exc_info=True)
            return None

    def obtener_fecha_primera_gasto_equipo(self) -> str | None:
        """
        Retorna la fecha (YYYY-MM-DD) más antigua en la colección 'gastos'.
        """
        try:
            snaps = list(self.db.collection("gastos").stream())
            fechas = []
            for s in snaps:
                data = s.to_dict() or {}
                f = data.get("fecha")
                if isinstance(f, str) and f:
                    fechas.append(f)
            if not fechas:
                return None
            return sorted(fechas)[0]
        except Exception as e:
            logger.error(f"obtener_fecha_primera_gasto_equipo error: {e}", exc_info=True)
            return None

    # ---------- MANTENIMIENTOS DE EQUIPOS (compatibilidad extendida) ----------

    def obtener_mantenimientos_por_equipo(self, equipo_id: str) -> list[dict]:
        """
        Devuelve todos los mantenimientos de un equipo, ordenados por fecha asc.
        """
        try:
            snaps = (
                self.db.collection("mantenimientos")
                .where("equipo_id", "==", str(equipo_id))
                .stream()
            )
            out = []
            for s in snaps:
                data = s.to_dict() or {}
                data["id"] = s.id
                data.setdefault("fecha_servicio", data.get("fecha"))
                data.setdefault("costo", data.get("valor", data.get("costo")))
                data.setdefault("horas_totales_equipo", data.get("odometro_horas"))
                data.setdefault("km_totales_equipo", data.get("odometro_km"))
                out.append(data)
            out.sort(key=lambda d: d.get("fecha_servicio") or d.get("fecha") or "")
            return out
        except Exception as e:
            logger.error(f"obtener_mantenimientos_por_equipo error: {e}", exc_info=True)
            return []

    def registrar_mantenimiento_ext(self, datos: dict) -> str | None:
        """
        Variante usada por VentanaGestionMantenimientos.
        """
        try:
            col = self.db.collection("mantenimientos")
            mid = datos.get("id")
            doc_ref = col.document(mid) if mid else col.document()

            payload = {
                "equipo_id": str(datos.get("equipo_id")),
                "fecha": datos.get("fecha"),
                "descripcion": datos.get("descripcion"),
                "tipo": datos.get("tipo"),
                "valor": float(datos.get("valor", 0) or 0),
                "odometro_horas": datos.get("odometro_horas"),
                "odometro_km": datos.get("odometro_km"),
                "lectura_es_horas": bool(datos.get("lectura_es_horas", True)),
            }
            if "proyecto_id" in datos:
                payload["proyecto_id"] = str(datos["proyecto_id"])

            doc_ref.set(payload, merge=True)
            return doc_ref.id
        except Exception as e:
            logger.error(f"registrar_mantenimiento_ext error: {e}", exc_info=True)
            return None

    def actualizar_mantenimiento_ext(self, datos: dict) -> bool:
        """
        Variante usada por VentanaGestionMantenimientos.
        """
        mid = datos.get("id")
        if not mid:
            logger.warning("actualizar_mantenimiento_ext llamado sin id")
            return False
        try:
            payload = {
                "equipo_id": str(datos.get("equipo_id")),
                "fecha": datos.get("fecha"),
                "descripcion": datos.get("descripcion"),
                "tipo": datos.get("tipo"),
                "valor": float(datos.get("valor", 0) or 0),
                "odometro_horas": datos.get("odometro_horas"),
                "odometro_km": datos.get("odometro_km"),
                "lectura_es_horas": bool(datos.get("lectura_es_horas", True)),
            }
            if "proyecto_id" in datos:
                payload["proyecto_id"] = str(datos["proyecto_id"])

            self.db.collection("mantenimientos").document(str(mid)).update(payload)
            return True
        except Exception as e:
            logger.error(f"actualizar_mantenimiento_ext error: {e}", exc_info=True)
            return False

    def eliminar_mantenimiento_ext(self, mantenimiento_id: str) -> bool:
        try:
            self.db.collection("mantenimientos").document(str(mantenimiento_id)).delete()
            return True
        except Exception as e:
            logger.error(f"eliminar_mantenimiento_ext error: {e}", exc_info=True)
            return False

    def obtener_estado_mantenimiento_equipos(self, proyecto_id: str | int) -> list[dict]:
        """
        Versión simplificada: calcula estado por equipo a partir de la tabla de mantenimientos
        + los equipos.
        """
        try:
            equipos = self.obtener_equipos(activo=None)
            equipos_por_id = {str(e["id"]): e for e in equipos}

            snaps = self.db.collection("mantenimientos").stream()
            mant_por_equipo: dict[str, list[dict]] = {}
            for s in snaps:
                d = s.to_dict() or {}
                eid = str(d.get("equipo_id") or "")
                if not eid:
                    continue
                d["id"] = s.id
                mant_por_equipo.setdefault(eid, []).append(d)

            estado = []
            for eid, eq in equipos_por_id.items():
                lista = mant_por_equipo.get(eid, [])
                if lista:
                    lista.sort(key=lambda d: d.get("fecha") or "")
                    ultimo = lista[-1]
                    fecha_ult = ultimo.get("fecha") or ""
                    estado.append({
                        "id": eid,
                        "nombre": eq.get("nombre", f"Equipo {eid}"),
                        "intervalo_txt": "N/D",
                        "uso_txt": f"Últ. serv: {fecha_ult}",
                        "restante_txt": "",
                        "progreso_txt": "",
                        "critico": False,
                        "alerta": False,
                    })
                else:
                    estado.append({
                        "id": eid,
                        "nombre": eq.get("nombre", f"Equipo {eid}"),
                        "intervalo_txt": "Sin datos",
                        "uso_txt": "Sin mantenimientos",
                        "restante_txt": "",
                        "progreso_txt": "",
                        "critico": False,
                        "alerta": False,
                    })

            return estado
        except Exception as e:
            logger.error(f"obtener_estado_mantenimiento_equipos error: {e}", exc_info=True)
            return []

    # ---------- Fechas mínimas para reportes ----------

    def obtener_fecha_primera_transaccion(self) -> str | None:
        """
        Devuelve la fecha más antigua (YYYY-MM-DD) entre todos los alquileres.
        """
        try:
            snaps = self.db.collection("alquileres").stream()
            fechas = []
            for s in snaps:
                f = (s.to_dict() or {}).get("fecha")
                if isinstance(f, str) and f:
                    fechas.append(f)
            if not fechas:
                return None
            return min(fechas)
        except Exception as e:
            logger.error(f"obtener_fecha_primera_transaccion error: {e}", exc_info=True)
            return None

    def obtener_fecha_primera_transaccion_cliente_simple(self, cliente_id: str) -> str | None:
        """
        Versión simple: fecha más antigua para un cliente específico.
        """
        try:
            snaps = (
                self.db.collection("alquileres")
                .where("cliente_id", "==", str(cliente_id))
                .stream()
            )
            fechas = []
            for s in snaps:
                f = (s.to_dict() or {}).get("fecha")
                if isinstance(f, str) and f:
                    fechas.append(f)
            if not fechas:
                return None
            return min(fechas)
        except Exception as e:
            logger.error(f"obtener_fecha_primera_transaccion_cliente_simple error: {e}", exc_info=True)
            return None

    def obtener_fecha_primera_transaccion_operador_simple(self, operador_id: str) -> str | None:
        """
        Versión simple: fecha más antigua para un operador específico.
        """
        try:
            snaps = (
                self.db.collection("alquileres")
                .where("operador_id", "==", str(operador_id))
                .stream()
            )
            fechas = []
            for s in snaps:
                f = (s.to_dict() or {}).get("fecha")
                if isinstance(f, str) and f:
                    fechas.append(f)
            if not fechas:
                return None
            return min(fechas)
        except Exception as e:
            logger.error(f"obtener_fecha_primera_transaccion_operador_simple error: {e}", exc_info=True)
            return None

    # ==================== MODIFICADO: obtener_rendimiento_por_equipo ====================
    def obtener_rendimiento_por_equipo(self, fecha_inicio: str, fecha_fin: str, equipo_id: str | None = None) -> list[dict]:
        """
        Calcula métricas de rendimiento por equipo en el rango de fechas:
          horas_facturadas (solo modalidad horas)
          volumen_facturado (solo modalidad volumen)
          monto_facturado (todas las modalidades)
          horas_pagadas_operador (pagos a operadores)
          monto_pagado_operador (pagos a operadores)
        """
        try:
            filtros_alq = {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
            }
            if equipo_id:
                filtros_alq["equipo_id"] = str(equipo_id)

            alquileres = self.obtener_alquileres(filtros_alq) or []

            por_equipo: dict[str, dict] = {}

            for alq in alquileres:
                eid = str(alq.get("equipo_id") or "")
                if not eid:
                    continue
                f = alq.get("fecha")
                if not isinstance(f, str) or not (fecha_inicio <= f <= fecha_fin):
                    continue

                monto = float(alq.get("monto", 0) or 0)
                modalidad = (alq.get("modalidad_facturacion") or "horas").strip().lower()

                info = por_equipo.setdefault(
                    eid,
                    {
                        "equipo_id": eid,
                        "equipo_nombre": alq.get("equipo_nombre", ""),
                        "horas_facturadas": 0.0,
                        "volumen_facturado": 0.0,
                        "monto_facturado": 0.0,
                        "horas_pagadas_operador": 0.0,
                        "monto_pagado_operador": 0.0,
                    },
                )

                if modalidad == "horas":
                    horas = float(alq.get("horas", 0) or 0)
                    info["horas_facturadas"] += horas
                elif modalidad == "volumen":
                    vol = float(alq.get("volumen_generado", 0) or 0)
                    info["volumen_facturado"] += vol
                # modalidad fijo: no suma horas ni volumen

                info["monto_facturado"] += monto

            # Pagos a operadores (sumar horas y montos)
            pagos = self.obtener_pagos_operadores({}) or []
            for p in pagos:
                eid = str(p.get("equipo_id") or "")
                if equipo_id and eid != str(equipo_id):
                    continue
                if not eid:
                    continue

                f = p.get("fecha")
                if not isinstance(f, str) or not (fecha_inicio <= f <= fecha_fin):
                    continue

                horas_p = float(p.get("horas", 0) or 0)
                monto_p = float(p.get("monto", 0) or 0)

                info = por_equipo.setdefault(
                    eid,
                    {
                        "equipo_id": eid,
                        "equipo_nombre": "",
                        "horas_facturadas": 0.0,
                        "volumen_facturado": 0.0,
                        "monto_facturado": 0.0,
                        "horas_pagadas_operador": 0.0,
                        "monto_pagado_operador": 0.0,
                    },
                )
                info["horas_pagadas_operador"] += horas_p
                info["monto_pagado_operador"] += monto_p

            return list(por_equipo.values())

        except Exception as e:
            logger.error(f"obtener_rendimiento_por_equipo error: {e}", exc_info=True)
            return []
        

    # ==================== HELPER OPCIONAL PARA MODALIDAD ====================
    def _calcular_monto_alquiler(self, datos: Dict[str, Any], original: Dict[str, Any] | None = None) -> tuple[float, str]:
        """
        Calcula el monto del alquiler según la modalidad.
        Modalidades soportadas:
          - horas: requiere horas, precio_por_hora
          - volumen: requiere volumen_generado, precio_por_unidad (unidad_volumen solo informativa)
          - fijo: requiere monto_fijo
        Si algún campo falta, usa 0 por defecto.
        Retorna (monto_calculado, modalidad_normalizada)
        """
        modalidad = (datos.get("modalidad_facturacion")
                     or (original or {}).get("modalidad_facturacion")
                     or "horas").strip().lower()

        if modalidad not in ("horas", "volumen", "fijo"):
            modalidad = "horas"

        if modalidad == "volumen":
            vol = float(datos.get("volumen_generado",
                                  (original or {}).get("volumen_generado", 0)) or 0)
            ppu = float(datos.get("precio_por_unidad",
                                  (original or {}).get("precio_por_unidad", 0)) or 0)
            monto = vol * ppu
            # No aplican horas
            datos.setdefault("horas", None)
            datos.setdefault("precio_por_hora", None)
        elif modalidad == "fijo":
            monto = float(datos.get("monto_fijo",
                                    (original or {}).get("monto_fijo", 0)) or 0)
            datos.setdefault("horas", None)
            datos.setdefault("precio_por_hora", None)
        else:  # horas
            horas = float(datos.get("horas",
                                    (original or {}).get("horas", 0)) or 0)
            pph = float(datos.get("precio_por_hora",
                                  (original or {}).get("precio_por_hora", 0)) or 0)
            monto = horas * pph

        return monto, modalidad

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("FirebaseManager - Módulo de gestión de Firestore para EQUIPOS 4.0")