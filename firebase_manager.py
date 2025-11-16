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
        """
        Inicializa la conexión con Firebase.
        
        Args:
            credentials_path: Ruta al archivo JSON de credenciales de Firebase
            project_id: ID del proyecto de Firebase
            
        Raises:
            FileNotFoundError: Si no se encuentra el archivo de credenciales
            Exception: Si hay error al inicializar Firebase
        """
        try:
            # Verificar si Firebase ya está inicializado
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
    
    # ==================== EQUIPOS ====================
    
    def obtener_equipos(self, activo: Optional[bool] = True) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de equipos.
        
        Args:
            activo: Si es True, solo equipos activos. Si es None, todos los equipos.
            
        Returns:
            Lista de diccionarios con los datos de los equipos
        """
        try:
            equipos_ref = self.db.collection('equipos')
            
            if activo is not None:
                query = equipos_ref.where(filter=FieldFilter('activo', '==', activo))
            else:
                query = equipos_ref
            
            docs = query.stream()
            equipos = []
            for doc in docs:
                equipo = doc.to_dict()
                equipo['id'] = doc.id
                equipos.append(equipo)
            
            logger.info(f"Obtenidos {len(equipos)} equipos")
            return equipos
            
        except Exception as e:
            logger.error(f"Error al obtener equipos: {e}")
            return []
    
    def obtener_equipo_por_id(self, equipo_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un equipo por su ID.
        
        Args:
            equipo_id: ID del equipo
            
        Returns:
            Diccionario con los datos del equipo o None si no existe
        """
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
        """
        Agrega un nuevo equipo.
        
        Args:
            datos: Diccionario con los datos del equipo
                Campos: nombre, marca, modelo, categoria, placa, ficha, activo, etc.
                
        Returns:
            ID del equipo creado o None si hay error
        """
        try:
            # Agregar timestamp de creación
            datos['fecha_creacion'] = datetime.now()
            datos['fecha_modificacion'] = datetime.now()
            
            # Si no tiene el campo activo, establecerlo en True
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
        """
        Edita un equipo existente.
        
        Args:
            equipo_id: ID del equipo a editar
            datos: Diccionario con los datos a actualizar
            
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        try:
            # Agregar timestamp de modificación
            datos['fecha_modificacion'] = datetime.now()
            
            self.db.collection('equipos').document(equipo_id).update(datos)
            logger.info(f"Equipo {equipo_id} actualizado")
            return True
            
        except Exception as e:
            logger.error(f"Error al editar equipo {equipo_id}: {e}")
            return False
    
    def eliminar_equipo(self, equipo_id: str, eliminar_fisicamente: bool = False) -> bool:
        """
        Elimina o desactiva un equipo.
        
        Args:
            equipo_id: ID del equipo a eliminar
            eliminar_fisicamente: Si es True, elimina el documento. Si es False, solo lo marca como inactivo.
            
        Returns:
            True si se eliminó/desactivó correctamente, False en caso contrario
        """
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
    
    # ==================== TRANSACCIONES (ALQUILERES) ====================
    
    def obtener_transacciones(self, filtros: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Obtiene transacciones con filtros opcionales.
        
        Args:
            filtros: Diccionario con filtros opcionales:
                - tipo: 'Ingreso' o 'Gasto'
                - equipo_id: ID del equipo
                - cliente_id: ID del cliente
                - operador_id: ID del operador
                - fecha_inicio: fecha mínima
                - fecha_fin: fecha máxima
                - pagado: bool
                
        Returns:
            Lista de diccionarios con las transacciones
        """
        try:
            query = self.db.collection('transacciones')
            
            if filtros:
                if 'tipo' in filtros:
                    query = query.where(filter=FieldFilter('tipo', '==', filtros['tipo']))
                if 'equipo_id' in filtros:
                    query = query.where(filter=FieldFilter('equipo_id', '==', filtros['equipo_id']))
                if 'cliente_id' in filtros:
                    query = query.where(filter=FieldFilter('cliente_id', '==', filtros['cliente_id']))
                if 'operador_id' in filtros:
                    query = query.where(filter=FieldFilter('operador_id', '==', filtros['operador_id']))
                if 'pagado' in filtros:
                    query = query.where(filter=FieldFilter('pagado', '==', filtros['pagado']))
                if 'fecha_inicio' in filtros:
                    query = query.where(filter=FieldFilter('fecha', '>=', filtros['fecha_inicio']))
                if 'fecha_fin' in filtros:
                    query = query.where(filter=FieldFilter('fecha', '<=', filtros['fecha_fin']))
            
            # Ordenar por fecha descendente
            query = query.order_by('fecha', direction=firestore.Query.DESCENDING)
            
            docs = query.stream()
            transacciones = []
            for doc in docs:
                transaccion = doc.to_dict()
                transaccion['id'] = doc.id
                transacciones.append(transaccion)
            
            logger.info(f"Obtenidas {len(transacciones)} transacciones")
            return transacciones
            
        except Exception as e:
            logger.error(f"Error al obtener transacciones: {e}")
            return []
    
    def obtener_transaccion_por_id(self, transaccion_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una transacción por su ID."""
        try:
            doc = self.db.collection('transacciones').document(transaccion_id).get()
            if doc.exists:
                transaccion = doc.to_dict()
                transaccion['id'] = doc.id
                return transaccion
            return None
        except Exception as e:
            logger.error(f"Error al obtener transacción {transaccion_id}: {e}")
            return None
    
    def registrar_alquiler(self, datos: Dict[str, Any]) -> Optional[str]:
        """
        Registra un nuevo alquiler (transacción de ingreso).
        
        Args:
            datos: Diccionario con los datos del alquiler
                Campos requeridos: equipo_id, cliente_id, fecha, monto
                Campos opcionales: operador_id, descripcion, horas, precio_por_hora,
                                   conduce, ubicacion, pagado, comentario
                
        Returns:
            ID de la transacción creada o None si hay error
        """
        try:
            # Establecer valores por defecto
            datos['tipo'] = 'Ingreso'
            datos['fecha_creacion'] = datetime.now()
            datos['fecha_modificacion'] = datetime.now()
            
            if 'pagado' not in datos:
                datos['pagado'] = False
            
            doc_ref = self.db.collection('transacciones').add(datos)
            transaccion_id = doc_ref[1].id
            logger.info(f"Alquiler registrado con ID: {transaccion_id}")
            return transaccion_id
            
        except Exception as e:
            logger.error(f"Error al registrar alquiler: {e}")
            return None
    
    def registrar_gasto_equipo(self, datos: Dict[str, Any]) -> Optional[str]:
        """
        Registra un gasto asociado a un equipo.
        
        Args:
            datos: Diccionario con los datos del gasto
                Campos: equipo_id, fecha, monto, descripcion, categoria, subcategoria, etc.
                
        Returns:
            ID de la transacción creada o None si hay error
        """
        try:
            datos['tipo'] = 'Gasto'
            datos['fecha_creacion'] = datetime.now()
            datos['fecha_modificacion'] = datetime.now()
            
            doc_ref = self.db.collection('transacciones').add(datos)
            transaccion_id = doc_ref[1].id
            logger.info(f"Gasto registrado con ID: {transaccion_id}")
            return transaccion_id
            
        except Exception as e:
            logger.error(f"Error al registrar gasto: {e}")
            return None
    
    def editar_transaccion(self, transaccion_id: str, datos: Dict[str, Any]) -> bool:
        """Edita una transacción existente."""
        try:
            datos['fecha_modificacion'] = datetime.now()
            self.db.collection('transacciones').document(transaccion_id).update(datos)
            logger.info(f"Transacción {transaccion_id} actualizada")
            return True
        except Exception as e:
            logger.error(f"Error al editar transacción {transaccion_id}: {e}")
            return False
    
    def eliminar_transaccion(self, transaccion_id: str) -> bool:
        """Elimina una transacción."""
        try:
            self.db.collection('transacciones').document(transaccion_id).delete()
            logger.info(f"Transacción {transaccion_id} eliminada")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar transacción {transaccion_id}: {e}")
            return False
    
    # ==================== ENTIDADES (CLIENTES Y OPERADORES) ====================
    
    def obtener_entidades(self, tipo: Optional[str] = None, activo: Optional[bool] = True) -> List[Dict[str, Any]]:
        """
        Obtiene entidades (clientes u operadores).
        
        Args:
            tipo: 'Cliente' u 'Operador'. Si es None, obtiene ambos.
            activo: Si es True, solo activos. Si es None, todos.
            
        Returns:
            Lista de entidades
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
            
            logger.info(f"Obtenidas {len(entidades)} entidades (tipo={tipo})")
            return entidades
            
        except Exception as e:
            logger.error(f"Error al obtener entidades: {e}")
            return []
    
    def obtener_entidad_por_id(self, entidad_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una entidad por su ID."""
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
        """
        Agrega una nueva entidad (cliente u operador).
        
        Args:
            datos: Diccionario con los datos
                Campos: nombre, tipo ('Cliente' o 'Operador'), telefono, cedula, activo
        """
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
        """Edita una entidad existente."""
        try:
            datos['fecha_modificacion'] = datetime.now()
            self.db.collection('entidades').document(entidad_id).update(datos)
            logger.info(f"Entidad {entidad_id} actualizada")
            return True
        except Exception as e:
            logger.error(f"Error al editar entidad {entidad_id}: {e}")
            return False
    
    def eliminar_entidad(self, entidad_id: str, eliminar_fisicamente: bool = False) -> bool:
        """Elimina o desactiva una entidad."""
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
        
        Args:
            equipo_id: ID del equipo. Si es None, obtiene todos los mantenimientos.
            
        Returns:
            Lista de mantenimientos
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
            logger.error(f"Error al obtener mantenimientos: {e}")
            return []
    
    def obtener_mantenimiento_por_id(self, mantenimiento_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un mantenimiento por su ID."""
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
        """
        Registra un nuevo mantenimiento.
        
        Args:
            datos: Diccionario con los datos del mantenimiento
                Campos: equipo_id, fecha, descripcion, tipo, costo, odometro_horas,
                        odometro_km, notas, proximo_tipo, proximo_valor, proximo_fecha
        """
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
        """Edita un mantenimiento existente."""
        try:
            datos['fecha_modificacion'] = datetime.now()
            self.db.collection('mantenimientos').document(mantenimiento_id).update(datos)
            logger.info(f"Mantenimiento {mantenimiento_id} actualizado")
            return True
        except Exception as e:
            logger.error(f"Error al editar mantenimiento {mantenimiento_id}: {e}")
            return False
    
    def eliminar_mantenimiento(self, mantenimiento_id: str) -> bool:
        """Elimina un mantenimiento."""
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
        
        Args:
            filtros: Diccionario con filtros:
                - operador_id: ID del operador
                - equipo_id: ID del equipo
                - fecha_inicio, fecha_fin
                
        Returns:
            Lista de pagos
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
            logger.error(f"Error al obtener pagos a operadores: {e}")
            return []
    
    def registrar_pago_operador(self, datos: Dict[str, Any]) -> Optional[str]:
        """
        Registra un pago a un operador.
        
        Args:
            datos: Diccionario con los datos del pago
                Campos: operador_id, fecha, monto, horas, equipo_id, descripcion, comentario
        """
        try:
            datos['fecha_creacion'] = datetime.now()
            datos['fecha_modificacion'] = datetime.now()
            
            doc_ref = self.db.collection('pagos_operadores').add(datos)
            pago_id = doc_ref[1].id
            logger.info(f"Pago a operador registrado con ID: {pago_id}")
            return pago_id
            
        except Exception as e:
            logger.error(f"Error al registrar pago a operador: {e}")
            return None
    
    def editar_pago_operador(self, pago_id: str, datos: Dict[str, Any]) -> bool:
        """Edita un pago a operador existente."""
        try:
            datos['fecha_modificacion'] = datetime.now()
            self.db.collection('pagos_operadores').document(pago_id).update(datos)
            logger.info(f"Pago a operador {pago_id} actualizado")
            return True
        except Exception as e:
            logger.error(f"Error al editar pago a operador {pago_id}: {e}")
            return False
    
    def eliminar_pago_operador(self, pago_id: str) -> bool:
        """Elimina un pago a operador."""
        try:
            self.db.collection('pagos_operadores').document(pago_id).delete()
            logger.info(f"Pago a operador {pago_id} eliminado")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar pago a operador {pago_id}: {e}")
            return False
    
    # ==================== UTILIDADES ====================
    
    def obtener_estadisticas_dashboard(self, fecha_inicio: str, fecha_fin: str) -> Dict[str, Any]:
        """
        Obtiene estadísticas para el dashboard.
        
        Args:
            fecha_inicio: Fecha de inicio en formato ISO
            fecha_fin: Fecha de fin en formato ISO
            
        Returns:
            Diccionario con estadísticas
        """
        try:
            # Obtener ingresos
            ingresos_query = self.db.collection('transacciones')\
                .where(filter=FieldFilter('tipo', '==', 'Ingreso'))\
                .where(filter=FieldFilter('fecha', '>=', fecha_inicio))\
                .where(filter=FieldFilter('fecha', '<=', fecha_fin))\
                .stream()
            
            total_ingresos = sum(doc.to_dict().get('monto', 0) for doc in ingresos_query)
            
            # Obtener gastos
            gastos_query = self.db.collection('transacciones')\
                .where(filter=FieldFilter('tipo', '==', 'Gasto'))\
                .where(filter=FieldFilter('fecha', '>=', fecha_inicio))\
                .where(filter=FieldFilter('fecha', '<=', fecha_fin))\
                .stream()
            
            total_gastos = sum(doc.to_dict().get('monto', 0) for doc in gastos_query)
            
            # Calcular utilidad
            utilidad = total_ingresos - total_gastos
            
            # Contar equipos activos
            equipos_activos = len(self.obtener_equipos(activo=True))
            
            return {
                'ingresos': total_ingresos,
                'gastos': total_gastos,
                'utilidad': utilidad,
                'equipos_activos': equipos_activos
            }
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            return {
                'ingresos': 0,
                'gastos': 0,
                'utilidad': 0,
                'equipos_activos': 0
            }


if __name__ == "__main__":
    # Pruebas básicas
    logging.basicConfig(level=logging.INFO)
    print("FirebaseManager - Módulo de gestión de Firestore para EQUIPOS 4.0")
