"""
Tab de Pagos a Operadores para EQUIPOS 4.0
¡MODIFICADO (V8)!
- Corregida la conversión de tipo de ID (str a int) en los filtros.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QLabel, QDateEdit, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from datetime import datetime
import logging

from firebase_manager import FirebaseManager
# from dialogs.pago_operador_dialog import PagoOperadorDialog # Futuro

logger = logging.getLogger(__name__)

class TabPagosOperadores(QWidget):
    """
    Tab para gestionar los pagos a operadores.
    """
    
    recargar_dashboard = pyqtSignal()

    def __init__(self, firebase_manager: FirebaseManager):
        super().__init__()
        
        self.fm = firebase_manager
        self.pagos_cargados = [] # Caché de los pagos
        
        # Mapas (se cargarán desde el padre)
        self.equipos_mapa = {}
        self.operadores_mapa = {}
        self.cuentas_mapa = {}
        
        self._init_ui()
        
    def _init_ui(self):
        """Inicializa la interfaz de usuario del tab."""
        main_layout = QVBoxLayout(self)
        
        # 1. Filtros y Acciones
        controles_layout = QVBoxLayout()
        self._crear_filtros(controles_layout)
        self._crear_botones_acciones(controles_layout)
        main_layout.addLayout(controles_layout)
        
        # 2. Tabla de Pagos
        self._crear_tabla_pagos()
        main_layout.addWidget(self.tabla_pagos)
        
        # 3. Totales
        totales_layout = QHBoxLayout()
        self._crear_totales(totales_layout)
        main_layout.addLayout(totales_layout)
        
        self.setLayout(main_layout)
        
        # Conectar señales
        self.btn_buscar_pagos.clicked.connect(self._cargar_pagos)
        self.btn_nuevo_pago.clicked.connect(self.abrir_dialogo_pago)
        self.btn_editar_pago.clicked.connect(self.editar_pago_seleccionado)
        self.btn_eliminar_pago.clicked.connect(self.eliminar_pago_seleccionado)
        
        # Conectar doble clic en tabla para editar
        self.tabla_pagos.itemDoubleClicked.connect(self.editar_pago_seleccionado)

    def _crear_filtros(self, layout: QVBoxLayout):
        """Crea los widgets de filtro en layout horizontal."""
        filtros_layout = QHBoxLayout()
        
        # Controles de Fecha
        filtros_layout.addWidget(QLabel("Desde:"))
        self.date_desde_pagos = QDateEdit(calendarPopup=True)
        self.date_desde_pagos.setDisplayFormat("yyyy-MM-dd")
        # Fecha inicial se establecerá dinámicamente en _inicializar_fechas_filtro()
        self.date_desde_pagos.setDate(QDate.currentDate().addMonths(-1))
        filtros_layout.addWidget(self.date_desde_pagos)
        
        filtros_layout.addWidget(QLabel("Hasta:"))
        self.date_hasta_pagos = QDateEdit(calendarPopup=True)
        self.date_hasta_pagos.setDisplayFormat("yyyy-MM-dd")
        # Fecha "Hasta" siempre es la fecha actual
        self.date_hasta_pagos.setDate(QDate.currentDate())
        filtros_layout.addWidget(self.date_hasta_pagos)
        
        filtros_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        # Combos
        filtros_layout.addWidget(QLabel("Operador:"))
        self.combo_operador_pagos = QComboBox()
        self.combo_operador_pagos.setMinimumWidth(150)
        filtros_layout.addWidget(self.combo_operador_pagos)

        filtros_layout.addWidget(QLabel("Equipo:"))
        self.combo_equipo_pagos = QComboBox()
        self.combo_equipo_pagos.setMinimumWidth(150)
        filtros_layout.addWidget(self.combo_equipo_pagos)
        
        filtros_layout.addStretch()
        layout.addLayout(filtros_layout)
        
    def _crear_botones_acciones(self, layout: QVBoxLayout):
        """Crea los botones de acción en layout horizontal."""
        acciones_layout = QHBoxLayout()
        
        self.btn_buscar_pagos = QPushButton("Buscar Pagos")
        acciones_layout.addWidget(self.btn_buscar_pagos)
        
        self.btn_nuevo_pago = QPushButton("Registrar Nuevo Pago")
        acciones_layout.addWidget(self.btn_nuevo_pago)
        
        self.btn_editar_pago = QPushButton("Editar Seleccionado")
        acciones_layout.addWidget(self.btn_editar_pago)
        
        self.btn_eliminar_pago = QPushButton("Eliminar Seleccionado")
        acciones_layout.addWidget(self.btn_eliminar_pago)
        
        acciones_layout.addStretch()
        layout.addLayout(acciones_layout)

    def _crear_tabla_pagos(self):
        """Crea la tabla de pagos (sin columna 'Acciones')."""
        self.tabla_pagos = QTableWidget()
        
        self.tabla_pagos.setColumnCount(8)
        
        HEADERS = [
            "Fecha", "Operador", "Equipo", "Cuenta",
            "Descripción", "Horas", "Monto", "Comentario"
        ]
        self.tabla_pagos.setHorizontalHeaderLabels(HEADERS)
        
        self.tabla_pagos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_pagos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_pagos.setAlternatingRowColors(True)
        self.tabla_pagos.setSortingEnabled(True) # Habilitar orden
        
        header = self.tabla_pagos.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Fecha
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Operador
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Equipo
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Cuenta
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)          # Descripción
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # Horas
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents) # Monto
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)          # Comentario

    def _crear_totales(self, layout: QHBoxLayout):
        """Crea los labels de totales."""
        self.lbl_total_pagos = QLabel("Total Pagos: 0")
        self.lbl_monto_total_pagos = QLabel("Monto Total: 0.00")
        
        layout.addStretch()
        layout.addWidget(self.lbl_total_pagos)
        layout.addSpacing(20)
        layout.addWidget(self.lbl_monto_total_pagos)

    def actualizar_mapas(self, mapas: dict):
        """Recibe los mapas desde la ventana principal y puebla los filtros."""
        self.equipos_mapa = mapas.get("equipos", {})
        self.operadores_mapa = mapas.get("operadores", {})
        self.cuentas_mapa = mapas.get("cuentas", {})
        
        logger.info("PagosOperadores: Mapas recibidos. Poblando filtros...")

        try:
            # --- Poblar Equipos ---
            self.combo_equipo_pagos.clear()
            self.combo_equipo_pagos.addItem("Todos", None)
            for eq_id, nombre in sorted(self.equipos_mapa.items(), key=lambda item: item[1]):
                self.combo_equipo_pagos.addItem(nombre, eq_id)
                
            # --- Poblar Operadores ---
            self.combo_operador_pagos.clear()
            self.combo_operador_pagos.addItem("Todos", None)
            for op_id, nombre in sorted(self.operadores_mapa.items(), key=lambda item: item[1]):
                self.combo_operador_pagos.addItem(nombre, op_id)
            
            # --- Inicializar fechas dinámicas ---
            self._inicializar_fechas_filtro()

        except Exception as e:
            logger.error(f"Error al poblar filtros de pagos: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"No se pudieron cargar los filtros de pagos: {e}")
    
    def _inicializar_fechas_filtro(self):
        """
        Inicializa los filtros de fecha de forma dinámica.
        La fecha "Desde" se establece como la fecha de la primera transacción de pagos a operadores.
        La fecha "Hasta" se establece como la fecha actual.
        """
        try:
            # Obtener fecha de la primera transacción de pagos a operadores
            primera_fecha_str = self.fm.obtener_fecha_primera_transaccion_pagos_operadores()
            
            if primera_fecha_str:
                # Convertir string a QDate
                primera_fecha = QDate.fromString(primera_fecha_str, "yyyy-MM-dd")
                self.date_desde_pagos.setDate(primera_fecha)
                logger.info(f"Fecha 'Desde' inicializada con primera transacción de pagos: {primera_fecha_str}")
            else:
                # Si no hay transacciones, usar primer día del mes actual
                self.date_desde_pagos.setDate(QDate.currentDate().addMonths(-1))
                logger.warning("No hay pagos a operadores, usando fecha por defecto (mes anterior)")
            
            # Fecha "Hasta" siempre es la fecha actual
            self.date_hasta_pagos.setDate(QDate.currentDate())
            
        except Exception as e:
            logger.error(f"Error al inicializar fechas de filtro: {e}", exc_info=True)
            # En caso de error, usar fechas por defecto
            self.date_desde_pagos.setDate(QDate.currentDate().addMonths(-1))
            self.date_hasta_pagos.setDate(QDate.currentDate())

    def _cargar_pagos(self):
        """Carga los pagos desde Firebase usando los filtros seleccionados."""
        # No cargar si los mapas no están listos
        if not self.operadores_mapa:
            logger.warning("PagosOperadores: Mapas no listos, saltando carga.")
            return

        filtros = {}
        
        # Recolectar filtros de fecha
        filtros['fecha_inicio'] = self.date_desde_pagos.date().toString("yyyy-MM-dd")
        filtros['fecha_fin'] = self.date_hasta_pagos.date().toString("yyyy-MM-dd")

        # --- ¡INICIO DE CORRECCIÓN (V8)! ---
        # Convertir IDs de string (del combo) a int (para Firestore)
        equipo_id_str = self.combo_equipo_pagos.currentData()
        if equipo_id_str:
            filtros['equipo_id'] = int(equipo_id_str)
            
        operador_id_str = self.combo_operador_pagos.currentData()
        if operador_id_str:
            filtros['operador_id'] = int(operador_id_str)
        # --- FIN DE CORRECCIÓN (V8)! ---
            
        try:
            logger.info(f"Cargando pagos a operadores con filtros: {filtros}")
            self.pagos_cargados = self.fm.obtener_pagos_operadores(filtros)
            
            self.tabla_pagos.setSortingEnabled(False) # Deshabilitar orden
            self.tabla_pagos.setRowCount(0) # Limpiar tabla
            if not self.pagos_cargados:
                logger.warning("No se encontraron pagos con esos filtros.")
                self.lbl_total_pagos.setText("Total Pagos: 0")
                self.lbl_monto_total_pagos.setText("Monto Total: 0.00")
                return

            self.tabla_pagos.setRowCount(len(self.pagos_cargados))
            total_monto_pagos = 0.0
            
            for row, pago in enumerate(self.pagos_cargados):
                # --- Traducción de IDs a Nombres ---
                try:
                    equipo_id = str(int(pago.get('equipo_id', 0)))
                except (ValueError, TypeError):
                    equipo_id = "0"
                try:
                    operador_id = str(int(pago.get('operador_id', 0)))
                except (ValueError, TypeError):
                    operador_id = "0"
                try:
                    cuenta_id = str(int(pago.get('cuenta_id', 0)))
                except (ValueError, TypeError):
                    cuenta_id = "0"
                
                equipo_nombre = self.equipos_mapa.get(equipo_id, f"ID: {equipo_id}")
                operador_nombre = self.operadores_mapa.get(operador_id, f"ID: {operador_id}")
                cuenta_nombre = self.cuentas_mapa.get(cuenta_id, "")
                
                # --- Poblar la tabla ---
                item_fecha = QTableWidgetItem(pago.get('fecha', ''))
                item_fecha.setData(Qt.ItemDataRole.UserRole, pago['id'])
                self.tabla_pagos.setItem(row, 0, item_fecha)
                
                self.tabla_pagos.setItem(row, 1, QTableWidgetItem(operador_nombre))
                self.tabla_pagos.setItem(row, 2, QTableWidgetItem(equipo_nombre))
                self.tabla_pagos.setItem(row, 3, QTableWidgetItem(cuenta_nombre))
                self.tabla_pagos.setItem(row, 4, QTableWidgetItem(pago.get('descripcion', '')))
                
                horas = pago.get('horas', 0)
                monto = pago.get('monto', 0)
                total_monto_pagos += float(monto)
                
                self.tabla_pagos.setItem(row, 5, QTableWidgetItem(f"{float(horas):,.2f}"))
                self.tabla_pagos.setItem(row, 6, QTableWidgetItem(f"{float(monto):,.2f}"))
                self.tabla_pagos.setItem(row, 7, QTableWidgetItem(pago.get('comentario', '')))
                
            # Actualizar totales
            self.lbl_total_pagos.setText(f"Total Pagos: {len(self.pagos_cargados)}")
            self.lbl_monto_total_pagos.setText(f"Monto Total: {total_monto_pagos:,.2f}")
            self.tabla_pagos.setSortingEnabled(True) # Habilitar orden

        except Exception as e:
            logger.error(f"Error al cargar pagos a operadores: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los pagos (¿Falta un índice en Firebase?):\n\n{e}")

    def _obtener_id_seleccionado_pago(self):
        """Obtiene el ID de Firestore del item seleccionado en la tabla."""
        selected_items = self.tabla_pagos.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Sin Selección", "Por favor, seleccione un pago de la tabla.")
            return None
        
        selected_row = selected_items[0].row()
        item_con_id = self.tabla_pagos.item(selected_row, 0) # El ID está en la primera columna
        pago_id = item_con_id.data(Qt.ItemDataRole.UserRole)
        return pago_id

    def abrir_dialogo_pago(self, pago_id: str = None):
        """Abre el diálogo para crear o editar un pago."""
        if pago_id is False: # Señal de "Nuevo"
            pago_id = None
        QMessageBox.information(self, "En desarrollo", f"Aquí se abriría el diálogo para el ID: {pago_id if pago_id else 'Nuevo'}")
        
    def editar_pago_seleccionado(self):
        """Abre el diálogo de edición para el pago seleccionado."""
        pago_id = self._obtener_id_seleccionado_pago()
        if pago_id:
            self.abrir_dialogo_pago(pago_id)

    def eliminar_pago_seleccionado(self):
        """Elimina el pago seleccionado tras confirmación."""
        pago_id = self._obtener_id_seleccionado_pago()
        if pago_id:
            reply = QMessageBox.question(self, "Confirmar Eliminación",
                                         f"¿Está seguro de que desea eliminar este pago (ID: {pago_id})?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    if self.fm.eliminar_pago_operador(pago_id):
                        QMessageBox.information(self, "Éxito", "Pago eliminado correctamente.")
                        self._cargar_pagos()
                        self.recargar_dashboard.emit()
                    else:
                        QMessageBox.warning(self, "Error", "No se pudo eliminar el pago.")
                except Exception as e:
                    logger.error(f"Error al eliminar pago {pago_id}: {e}")
                    QMessageBox.critical(self, "Error", f"Error al eliminar:\n{e}")