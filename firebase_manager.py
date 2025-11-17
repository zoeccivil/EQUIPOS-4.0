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

logger = logging.getLogger(__name__)


class FirebaseManager:
    """
    Gestor de conexión y operaciones con Firebase Firestore.
    Proporciona métodos CRUD para todas las entidades de EQUIPOS.
    """
    
    def __init__(self, credentials_path: str, project_id: str):
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
                pass # Ignorar si la fecha es inválida o no existe
        return datos

    # ==================== MAPAS GLOBALES ====================
    
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
            raise e # Propagar el error

    # ==================== EQUIPOS ====================
    
    def obtener_equipos(self, activo: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de equipos.
        """
        try:
            equipos_ref = self.db.collection('equipos')
            if activo is not None:
                query = equipos_ref.where(filter=FieldFilter('activo', '==', activo))
            else:
                query = equipos_ref
            docs = query.order_by('nombre').stream() # Requiere índice
            equipos = []
            for doc in docs:
                equipo = doc.to_dict()
                equipo['id'] = doc.id
                equipos.append(equipo)
            logger.info(f"Obtenidos {len(equipos)} equipos (activo={activo})")
            return equipos
        except Exception as e:
            logger.error(f"Error al obtener equipos (activo={activo}): {e}", exc_info=True)
            raise e # Propagar el error
    
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
            raise e # Propagar el error

    # --- ¡INICIO DE CORRECCIÓN (V10)! ---
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
    # --- FIN DE CORRECCIÓN (V10)! ---

    def registrar_alquiler(self, datos: Dict[str, Any]) -> Optional[str]:
        """Registra un nuevo alquiler."""
        try:
            datos['fecha_creacion'] = datetime.now()
            datos['fecha_modificacion'] = datetime.now()
            if 'pagado' not in datos:
                datos['pagado'] = False
            
            datos = self._agregar_fecha_ano_mes(datos)
            
            if 'transaccion_id' not in datos:
                 datos['transaccion_id'] = str(uuid.uuid4())

            doc_id = datos['transaccion_id']
            self.db.collection('alquileres').document(doc_id).set(datos)
            logger.info(f"Alquiler registrado con ID: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error al registrar alquiler: {e}")
            return None

    def editar_alquiler(self, alquiler_id: str, datos: Dict[str, Any]) -> bool:
        """Edita un alquiler existente."""
        try:
            datos['fecha_modificacion'] = datetime.now()
            datos = self._agregar_fecha_ano_mes(datos)
            self.db.collection('alquileres').document(alquiler_id).update(datos)
            logger.info(f"Alquiler {alquiler_id} actualizado")
            return True
        except Exception as e:
            logger.error(f"Error al editar alquiler {alquiler_id}: {e}")
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

    def obtener_gastos(self, filtros: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Obtiene gastos con filtros opcionales.
        """
        try:
            query = self.db.collection('gastos')
            
            if filtros:
                if 'fecha_inicio' in filtros:
                    query = query.where(filter=FieldFilter('fecha', '>=', filtros['fecha_inicio']))
                if 'fecha_fin' in filtros:
                    query = query.where(filter=FieldFilter('fecha', '<=', filtros['fecha_fin']))
                if 'equipo_id' in filtros:
                    query = query.where(filter=FieldFilter('equipo_id', '==', filtros['equipo_id']))
                if 'cuenta_id' in filtros:
                    query = query.where(filter=FieldFilter('cuenta_id', '==', filtros['cuenta_id']))
                if 'categoria_id' in filtros:
                    query = query.where(filter=FieldFilter('categoria_id', '==', filtros['categoria_id']))
            
            query = query.order_by('fecha', direction=firestore.Query.DESCENDING)
            docs = query.stream()
            
            gastos = []
            for doc in docs:
                gasto = doc.to_dict()
                gasto['id'] = doc.id
                gastos.append(gasto)
            
            logger.info(f"Obtenidos {len(gastos)} gastos con filtros: {filtros}")
            return gastos
            
        except Exception as e:
            logger.error(f"Error al obtener gastos: {e}", exc_info=True)
            raise e # Propagar el error

    def registrar_gasto_equipo(self, datos: Dict[str, Any]) -> Optional[str]:
        """Registra un gasto asociado a un equipo."""
        try:
            datos['tipo'] = 'Gasto' # Aseguramos el tipo
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

    def eliminar_gasto(self, gasto_id: str) -> bool:
        """Elimina un gasto."""
        try:
            self.db.collection('gastos').document(gasto_id).delete()
            logger.info(f"Gasto {gasto_id} eliminado")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar gasto {gasto_id}: {e}")
            return False

    # ==================== ENTIDADES (CLIENTES Y OPERADORES) ====================
    
    def obtener_entidades(self, tipo: Optional[str] = None, activo: Optional[bool] = None) -> List[Dict[str, Any]]: # MODIFICADO: activo=None
        """
        Obtiene entidades (clientes u operadores).
        """
        try:
            query = self.db.collection('entidades')
            if tipo:
                query = query.where(filter=FieldFilter('tipo', '==', tipo))
            if activo is not None:
                query = query.where(filter=FieldFilter('activo', '==', activo))
            
            docs = query.order_by('nombre').stream() 
            entidades = []
            for doc in docs:
                entidad = doc.to_dict()
                entidad['id'] = doc.id
                entidades.append(entidad)
            logger.info(f"Obtenidas {len(entidades)} entidades (tipo={tipo}, activo={activo})")
            return entidades
        except Exception as e:
            logger.error(f"Error al obtener entidades (tipo={tipo}, activo={activo}): {e}", exc_info=True)
            raise e # Propagar el error
    
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
            raise e # Propagar el error
            
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
    
    def obtener_pagos_operadores(self, filtros: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Obtiene pagos a operadores con filtros opcionales.
        """
        try:
            query = self.db.collection('pagos_operadores')
            if filtros:
                if 'operador_id' in filtros:
                    query = query.where(filter=FieldFilter('operador_id', '==', filtros['operador_id']))
                if 'equipo_id' in filtros:
                    query = query.where(filter=FieldFilter('equipo_id', '==', filtros['equipo_id']))
                if 'fecha_inicio' in filtros:
                    query = query.where(filter=FieldFilter('fecha', '>=', filtros['fecha_inicio']))
                if 'fecha_fin' in filtros:
                    query = query.where(filter=FieldFilter('fecha', '<=', filtros['fecha_fin']))

            query = query.order_by('fecha', direction=firestore.Query.DESCENDING)
            docs = query.stream()
            pagos = []
            for doc in docs:
                pago = doc.to_dict()
                pago['id'] = doc.id
                pagos.append(pago)
            logger.info(f"Obtenidos {len(pagos)} pagos a operadores")
            return pagos
        except Exception as e:
            logger.error(f"Error al obtener pagos a operadores: {e}", exc_info=True)
            raise e # Propagar el error
    
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
                'ingresos_data': [doc.to_dict() for doc in ingresos] # Pasa los datos para tops
            }
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}", exc_info=True)
            raise e # Propagar el error

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("FirebaseManager - Módulo de gestión de Firestore para EQUIPOS 4.0")