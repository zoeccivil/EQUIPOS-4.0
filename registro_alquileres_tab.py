"""
Tab de Registro de Alquileres para EQUIPOS 4.0
¡MODIFICADO (V10)!
- Corregida la llamada al constructor de AlquilerDialog (pasando alquiler_data)
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QLabel, QDateEdit, QSpacerItem, QSizePolicy, QStyle
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QIcon, QColor
from datetime import datetime
import logging

from firebase_manager import FirebaseManager
from dialogos.alquiler_dialog import AlquilerDialog 
from storage_manager import StorageManager 

logger = logging.getLogger(__name__)

class RegistroAlquileresTab(QWidget):
    """
    Tab para gestionar el registro de alquileres (transacciones de ingreso).
    """
    
    recargar_dashboard = pyqtSignal()
    
    def __init__(self, firebase_manager: FirebaseManager, storage_manager: StorageManager = None):
        super().__init__()
        
        self.fm = firebase_manager
        self.sm = storage_manager # Guardar el storage_manager
        self.alquileres_cargados = [] # Caché de los alquileres
        
        # Mapas de nombres (se llenarán desde app_gui)
        self.equipos_mapa = {}
        self.clientes_mapa = {}
        self.operadores_mapa = {}

        self._init_ui()
        
    def _init_ui(self):
        """Inicializa la interfaz de usuario del tab."""
        main_layout = QVBoxLayout(self)
        
        # 1. Filtros y Acciones
        controles_layout = QVBoxLayout()
        self._crear_filtros(controles_layout)
        self._crear_botones_acciones(controles_layout)
        main_layout.addLayout(controles_layout)
        
        # 2. Tabla de Alquileres
        self._crear_tabla_alquileres()
        main_layout.addWidget(self.tabla_alquileres)
        
        # 3. Totales
        totales_layout = QHBoxLayout()
        self._crear_totales(totales_layout)
        main_layout.addLayout(totales_layout)
        
        self.setLayout(main_layout)
        
        # Conectar señales
        self.btn_buscar.clicked.connect(self._cargar_alquileres)
        self.btn_nuevo.clicked.connect(self.abrir_dialogo_alquiler)
        self.btn_editar.clicked.connect(self.editar_alquiler_seleccionado)
        self.btn_eliminar.clicked.connect(self.eliminar_alquiler_seleccionado)
        
        # Conectar doble clic en tabla para editar
        self.tabla_alquileres.itemDoubleClicked.connect(self.editar_alquiler_seleccionado)

    def _crear_filtros(self, layout: QVBoxLayout):
        """Crea los widgets de filtro en layout horizontal."""
        filtros_layout = QHBoxLayout()
        
        # Controles de Fecha
        filtros_layout.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit(calendarPopup=True)
        self.date_desde.setDisplayFormat("yyyy-MM-dd")
        # Fecha inicial se establecerá dinámicamente en _inicializar_fechas_filtro()
        self.date_desde.setDate(QDate.currentDate().addMonths(-1))
        filtros_layout.addWidget(self.date_desde)
        
        filtros_layout.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit(calendarPopup=True)
        self.date_hasta.setDisplayFormat("yyyy-MM-dd")
        # Fecha "Hasta" siempre es la fecha actual
        self.date_hasta.setDate(QDate.currentDate())
        filtros_layout.addWidget(self.date_hasta)
        
        filtros_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        # Combos
        filtros_layout.addWidget(QLabel("Equipo:"))
        self.combo_equipo = QComboBox()
        self.combo_equipo.setMinimumWidth(150)
        filtros_layout.addWidget(self.combo_equipo)
        
        filtros_layout.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        self.combo_cliente.setMinimumWidth(150)
        filtros_layout.addWidget(self.combo_cliente)
        
        filtros_layout.addWidget(QLabel("Operador:"))
        self.combo_operador = QComboBox()
        self.combo_operador.setMinimumWidth(150)
        filtros_layout.addWidget(self.combo_operador)
        
        filtros_layout.addWidget(QLabel("Estado Pago:"))
        self.combo_pagado = QComboBox()
        filtros_layout.addWidget(self.combo_pagado)
        
        filtros_layout.addStretch()
        layout.addLayout(filtros_layout)
    
    def _crear_botones_acciones(self, layout: QVBoxLayout):
        """Crea los botones de acción en layout horizontal."""
        acciones_layout = QHBoxLayout()
        
        self.btn_buscar = QPushButton("🔍 Buscar")
        icon_search = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
        self.btn_buscar.setIcon(icon_search)
        acciones_layout.addWidget(self.btn_buscar)
        
        self.btn_nuevo = QPushButton("➕ Registrar Nuevo Alquiler")
        icon_new = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder)
        self.btn_nuevo.setIcon(icon_new)
        acciones_layout.addWidget(self.btn_nuevo)
        
        self.btn_editar = QPushButton("✏️ Editar Seleccionado")
        icon_edit = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        self.btn_editar.setIcon(icon_edit)
        acciones_layout.addWidget(self.btn_editar)
        
        self.btn_eliminar = QPushButton("🗑️ Eliminar Seleccionado")
        icon_delete = self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        self.btn_eliminar.setIcon(icon_delete)
        acciones_layout.addWidget(self.btn_eliminar)
        
        acciones_layout.addStretch()
        layout.addLayout(acciones_layout)
        
    def _crear_tabla_alquileres(self):
        """Crea la tabla de alquileres (sin columna 'Acciones')."""
        self.tabla_alquileres = QTableWidget()
        
        self.tabla_alquileres.setColumnCount(10)
        
        HEADERS = [
            "Fecha", "Equipo", "Cliente", "Operador", "Conduce", 
            "Horas", "Precio", "Monto", "Ubicación", "Pagado"
        ]
        self.tabla_alquileres.setHorizontalHeaderLabels(HEADERS)
        
        self.tabla_alquileres.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_alquileres.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_alquileres.setAlternatingRowColors(True)
        self.tabla_alquileres.setSortingEnabled(True) # Habilitar orden
        
        header = self.tabla_alquileres.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Fecha
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Equipo
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Cliente
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)          # Operador
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Conduce
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # Horas
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents) # Precio
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents) # Monto
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)          # Ubicación
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents) # Pagado

    def _crear_totales(self, layout: QHBoxLayout):
        """Crea los labels de totales."""
        self.lbl_total_alquileres = QLabel("Total Alquileres: 0")
        self.lbl_total_monto = QLabel("Monto Total: 0.00")
        
        layout.addStretch()
        layout.addWidget(self.lbl_total_alquileres)
        layout.addSpacing(20)
        layout.addWidget(self.lbl_total_monto)

    def actualizar_mapas(self, mapas: dict):
        """Recibe los mapas desde la ventana principal y puebla los filtros."""
        self.equipos_mapa = mapas.get("equipos", {})
        self.clientes_mapa = mapas.get("clientes", {})
        self.operadores_mapa = mapas.get("operadores", {})
        
        logger.info("RegistroAlquileres: Mapas recibidos. Poblando filtros...")
        
        try:
            # --- Poblar Equipos ---
            self.combo_equipo.clear()
            self.combo_equipo.addItem("Todos", None)
            for eq_id, nombre in sorted(self.equipos_mapa.items(), key=lambda item: item[1]):
                self.combo_equipo.addItem(nombre, eq_id)
                
            # --- Poblar Clientes ---
            self.combo_cliente.clear()
            self.combo_cliente.addItem("Todos", None)
            for cl_id, nombre in sorted(self.clientes_mapa.items(), key=lambda item: item[1]):
                self.combo_cliente.addItem(nombre, cl_id)
                
            # --- Poblar Operadores ---
            self.combo_operador.clear()
            self.combo_operador.addItem("Todos", None)
            for op_id, nombre in sorted(self.operadores_mapa.items(), key=lambda item: item[1]):
                self.combo_operador.addItem(nombre, op_id)

            # --- Poblar Estado de Pago ---
            self.combo_pagado.clear()
            self.combo_pagado.addItem("Todos", None)
            self.combo_pagado.addItem("Pendientes", False)
            self.combo_pagado.addItem("Pagados", True)
            
            # --- Inicializar fechas dinámicas ---
            self._inicializar_fechas_filtro()

        except Exception as e:
            logger.error(f"Error al poblar filtros de alquileres: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"No se pudieron cargar los filtros: {e}")
    
    def _inicializar_fechas_filtro(self):
        """
        Inicializa los filtros de fecha de forma dinámica.
        La fecha "Desde" se establece como la fecha de la primera transacción.
        La fecha "Hasta" se establece como la fecha actual.
        """
        try:
            # Obtener fecha de la primera transacción
            primera_fecha_str = self.fm.obtener_fecha_primera_transaccion_alquileres()
            
            if primera_fecha_str:
                # Convertir string a QDate
                primera_fecha = QDate.fromString(primera_fecha_str, "yyyy-MM-dd")
                self.date_desde.setDate(primera_fecha)
                logger.info(f"Fecha 'Desde' inicializada con primera transacción: {primera_fecha_str}")
            else:
                # Si no hay transacciones, usar primer día del mes actual
                self.date_desde.setDate(QDate.currentDate().addMonths(-1))
                logger.warning("No hay transacciones, usando fecha por defecto (mes anterior)")
            
            # Fecha "Hasta" siempre es la fecha actual
            self.date_hasta.setDate(QDate.currentDate())
            
        except Exception as e:
            logger.error(f"Error al inicializar fechas de filtro: {e}", exc_info=True)
            # En caso de error, usar fechas por defecto
            self.date_desde.setDate(QDate.currentDate().addMonths(-1))
            self.date_hasta.setDate(QDate.currentDate())

    def _cargar_alquileres(self):
        """Carga los alquileres desde Firebase usando los filtros seleccionados."""
        # No cargar si los mapas no están listos
        if not self.equipos_mapa:
            logger.warning("RegistroAlquileres: Mapas no listos, saltando carga.")
            return

        filtros = {}
        
        # Recolectar filtros de fecha
        filtros['fecha_inicio'] = self.date_desde.date().toString("yyyy-MM-dd")
        filtros['fecha_fin'] = self.date_hasta.date().toString("yyyy-MM-dd")
        
        # Convertir IDs de string (del combo) a int (para Firestore)
        equipo_id_str = self.combo_equipo.currentData()
        if equipo_id_str:
            filtros['equipo_id'] = int(equipo_id_str)
            
        cliente_id_str = self.combo_cliente.currentData()
        if cliente_id_str:
            filtros['cliente_id'] = int(cliente_id_str)
            
        operador_id_str = self.combo_operador.currentData()
        if operador_id_str:
            filtros['operador_id'] = int(operador_id_str)
            
        if self.combo_pagado.currentData() is not None:
            filtros['pagado'] = self.combo_pagado.currentData()
            
        try:
            logger.info(f"Cargando alquileres con filtros: {filtros}")
            self.alquileres_cargados = self.fm.obtener_alquileres(filtros)
            
            self.tabla_alquileres.setSortingEnabled(False) # Deshabilitar orden mientras se puebla
            self.tabla_alquileres.setRowCount(0) # Limpiar tabla
            if not self.alquileres_cargados:
                logger.warning("No se encontraron alquileres con esos filtros.")
                self.lbl_total_alquileres.setText("Total Alquileres: 0")
                self.lbl_total_monto.setText("Monto Total: 0.00")
                return

            self.tabla_alquileres.setRowCount(len(self.alquileres_cargados))
            total_monto = 0.0
            
            for row, alquiler in enumerate(self.alquileres_cargados):
                # --- Traducción de IDs a Nombres ---
                try:
                    equipo_id = str(int(alquiler.get('equipo_id', 0)))
                except (ValueError, TypeError):
                    equipo_id = "0"
                
                try:
                    cliente_id = str(int(alquiler.get('cliente_id', 0)))
                except (ValueError, TypeError):
                    cliente_id = "0"
                
                try:
                    operador_id = str(int(alquiler.get('operador_id', 0)))
                except (ValueError, TypeError):
                    operador_id = "0"

                equipo_nombre = self.equipos_mapa.get(equipo_id, f"ID: {equipo_id}")
                cliente_nombre = self.clientes_mapa.get(cliente_id, f"ID: {cliente_id}")
                operador_nombre = self.operadores_mapa.get(operador_id, f"ID: {operador_id}")
                
                # --- Poblar la tabla ---
                item_fecha = QTableWidgetItem(alquiler.get('fecha', ''))
                item_fecha.setData(Qt.ItemDataRole.UserRole, alquiler['id']) 
                self.tabla_alquileres.setItem(row, 0, item_fecha)

                self.tabla_alquileres.setItem(row, 1, QTableWidgetItem(equipo_nombre))
                self.tabla_alquileres.setItem(row, 2, QTableWidgetItem(cliente_nombre))
                self.tabla_alquileres.setItem(row, 3, QTableWidgetItem(operador_nombre))
                self.tabla_alquileres.setItem(row, 4, QTableWidgetItem(alquiler.get('conduce', '')))
                
                horas = alquiler.get('horas', 0)
                precio = alquiler.get('precio_por_hora', 0)
                monto = alquiler.get('monto', 0)
                total_monto += float(monto)
                
                self.tabla_alquileres.setItem(row, 5, QTableWidgetItem(f"{float(horas):,.2f}"))
                self.tabla_alquileres.setItem(row, 6, QTableWidgetItem(f"{float(precio):,.2f}"))
                self.tabla_alquileres.setItem(row, 7, QTableWidgetItem(f"{float(monto):,.2f}"))
                
                self.tabla_alquileres.setItem(row, 8, QTableWidgetItem(alquiler.get('ubicacion', '')))
                
                pagado = alquiler.get('pagado', False)
                item_pagado = QTableWidgetItem("Sí" if pagado else "No")
                item_pagado.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_pagado.setForeground(QColor('green') if pagado else QColor('red'))
                self.tabla_alquileres.setItem(row, 9, item_pagado)


            # Actualizar totales
            self.lbl_total_alquileres.setText(f"Total Alquileres: {len(self.alquileres_cargados)}")
            self.lbl_total_monto.setText(f"Monto Total: {total_monto:,.2f}")
            self.tabla_alquileres.setSortingEnabled(True) # Habilitar orden

        except Exception as e:
            logger.error(f"Error al cargar alquileres: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los alquileres (¿Falta un índice en Firebase?):\n\n{e}")

    def _obtener_id_seleccionado(self):
        """Obtiene el ID de Firestore del item seleccionado en la tabla."""
        selected_items = self.tabla_alquileres.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Sin Selección", "Por favor, seleccione un alquiler de la tabla.")
            return None
        
        selected_row = selected_items[0].row()
        item_con_id = self.tabla_alquileres.item(selected_row, 0) # El ID está en la primera columna
        alquiler_id = item_con_id.data(Qt.ItemDataRole.UserRole)
        return alquiler_id

    def abrir_dialogo_alquiler(self, alquiler_id: str = None):
        """Abre el diálogo para crear o editar un alquiler."""
        alquiler_data_para_dialogo = None
        if alquiler_id is False: # Señal de "Nuevo"
            alquiler_id = None
        
        # --- ¡INICIO DE CORRECCIÓN (V10)! ---
        if alquiler_id:
            # Si es una edición, buscar los datos completos del alquiler
            try:
                alquiler_data_para_dialogo = self.fm.obtener_alquiler_por_id(alquiler_id)
                if not alquiler_data_para_dialogo:
                    QMessageBox.critical(self, "Error", f"No se pudieron cargar los datos para el alquiler ID: {alquiler_id}")
                    return
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al cargar datos de alquiler: {e}")
                return
        
        dialog = AlquilerDialog(
            firebase_manager=self.fm, 
            storage_manager=self.sm, 
            equipos_mapa=self.equipos_mapa, 
            clientes_mapa=self.clientes_mapa, 
            operadores_mapa=self.operadores_mapa, 
            alquiler_data=alquiler_data_para_dialogo,  # <-- ¡CORREGIDO! Pasar el dict o None
            parent=self
        )
        # --- FIN DE CORRECCIÓN (V10)! ---
        
        if dialog.exec():
            self._cargar_alquileres()
            self.recargar_dashboard.emit()
        
    def editar_alquiler_seleccionado(self):
        """Abre el diálogo de edición para el alquiler seleccionado."""
        alquiler_id = self._obtener_id_seleccionado()
        if alquiler_id:
            self.abrir_dialogo_alquiler(alquiler_id)

    def eliminar_alquiler_seleccionado(self):
        """Elimina el alquiler seleccionado tras confirmación."""
        alquiler_id = self._obtener_id_seleccionado()
        if alquiler_id:
            reply = QMessageBox.question(self, "Confirmar Eliminación",
                                         f"¿Está seguro de que desea eliminar este registro (ID: {alquiler_id})?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    if self.fm.eliminar_alquiler(alquiler_id):
                        QMessageBox.information(self, "Éxito", "Alquiler eliminado correctamente.")
                        self._cargar_alquileres()
                        self.recargar_dashboard.emit()
                    else:
                        QMessageBox.warning(self, "Error", "No se pudo eliminar el alquiler.")
                except Exception as e:
                    logger.error(f"Error al eliminar alquiler {alquiler_id}: {e}")
                    QMessageBox.critical(self, "Error", f"Error al eliminar:\n{e}")