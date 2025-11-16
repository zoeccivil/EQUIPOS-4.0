"""
Tab de Gastos de Equipos para EQUIPOS 4.0
¡MODIFICADO (V7)!
- Corregida la conversión de tipo de ID (float a str)
- Filtros por rango de fecha (QDateEdit)
- Layout de filtros y botones horizontal
- Sin columna de "Acciones"
- Lógica de carga de mapas actualizada
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
# from dialogs.gasto_dialog import GastoDialog # Futuro

logger = logging.getLogger(__name__)

class TabGastosEquipos(QWidget):
    """
    Tab para gestionar los gastos asociados a los equipos.
    """
    
    recargar_dashboard = pyqtSignal()

    def __init__(self, firebase_manager: FirebaseManager):
        super().__init__()
        
        self.fm = firebase_manager
        self.gastos_cargados = [] # Caché de los gastos
        
        # Mapas (se cargarán desde el padre)
        self.equipos_mapa = {}
        self.cuentas_mapa = {}
        self.categorias_mapa = {}
        self.subcategorias_mapa = {}
        
        self._init_ui()
        
    def _init_ui(self):
        """Inicializa la interfaz de usuario del tab."""
        main_layout = QVBoxLayout(self)
        
        # 1. Filtros y Acciones
        controles_layout = QVBoxLayout()
        self._crear_filtros(controles_layout)
        self._crear_botones_acciones(controles_layout)
        main_layout.addLayout(controles_layout)
        
        # 2. Tabla de Gastos
        self._crear_tabla_gastos()
        main_layout.addWidget(self.tabla_gastos)
        
        # 3. Totales
        totales_layout = QHBoxLayout()
        self._crear_totales(totales_layout)
        main_layout.addLayout(totales_layout)
        
        self.setLayout(main_layout)
        
        # Conectar señales
        self.btn_buscar_gastos.clicked.connect(self._cargar_gastos)
        self.btn_nuevo_gasto.clicked.connect(self.abrir_dialogo_gasto)
        self.btn_editar_gasto.clicked.connect(self.editar_gasto_seleccionado)
        self.btn_eliminar_gasto.clicked.connect(self.eliminar_gasto_seleccionado)
        
        # Conectar doble clic en tabla para editar
        self.tabla_gastos.itemDoubleClicked.connect(self.editar_gasto_seleccionado)

    def _crear_filtros(self, layout: QVBoxLayout):
        """Crea los widgets de filtro en layout horizontal."""
        filtros_layout = QHBoxLayout()
        
        # Controles de Fecha
        filtros_layout.addWidget(QLabel("Desde:"))
        self.date_desde_gastos = QDateEdit(calendarPopup=True)
        self.date_desde_gastos.setDisplayFormat("yyyy-MM-dd")
        self.date_desde_gastos.setDate(datetime.now().replace(day=1))
        filtros_layout.addWidget(self.date_desde_gastos)
        
        filtros_layout.addWidget(QLabel("Hasta:"))
        self.date_hasta_gastos = QDateEdit(calendarPopup=True)
        self.date_hasta_gastos.setDisplayFormat("yyyy-MM-dd")
        self.date_hasta_gastos.setDate(datetime.now())
        filtros_layout.addWidget(self.date_hasta_gastos)
        
        filtros_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        # Combos
        filtros_layout.addWidget(QLabel("Equipo:"))
        self.combo_equipo_gastos = QComboBox()
        self.combo_equipo_gastos.setMinimumWidth(150)
        filtros_layout.addWidget(self.combo_equipo_gastos)

        filtros_layout.addWidget(QLabel("Cuenta:"))
        self.combo_cuenta_gastos = QComboBox()
        self.combo_cuenta_gastos.setMinimumWidth(150)
        filtros_layout.addWidget(self.combo_cuenta_gastos)
        
        filtros_layout.addWidget(QLabel("Categoría:"))
        self.combo_categoria_gastos = QComboBox()
        self.combo_categoria_gastos.setMinimumWidth(150)
        filtros_layout.addWidget(self.combo_categoria_gastos)
        
        filtros_layout.addStretch()
        layout.addLayout(filtros_layout)
        
    def _crear_botones_acciones(self, layout: QVBoxLayout):
        """Crea los botones de acción en layout horizontal."""
        acciones_layout = QHBoxLayout()
        
        self.btn_buscar_gastos = QPushButton("Buscar Gastos")
        acciones_layout.addWidget(self.btn_buscar_gastos)
        
        self.btn_nuevo_gasto = QPushButton("Registrar Nuevo Gasto")
        acciones_layout.addWidget(self.btn_nuevo_gasto)
        
        self.btn_editar_gasto = QPushButton("Editar Seleccionado")
        acciones_layout.addWidget(self.btn_editar_gasto)
        
        self.btn_eliminar_gasto = QPushButton("Eliminar Seleccionado")
        acciones_layout.addWidget(self.btn_eliminar_gasto)
        
        acciones_layout.addStretch()
        layout.addLayout(acciones_layout)

    def _crear_tabla_gastos(self):
        """Crea la tabla de gastos (sin columna 'Acciones')."""
        self.tabla_gastos = QTableWidget()
        
        self.tabla_gastos.setColumnCount(8)
        
        HEADERS = [
            "Fecha", "Equipo", "Cuenta", "Categoría", "Subcategoría",
            "Descripción", "Monto", "Comentario"
        ]
        self.tabla_gastos.setHorizontalHeaderLabels(HEADERS)
        
        self.tabla_gastos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_gastos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_gastos.setAlternatingRowColors(True)
        self.tabla_gastos.setSortingEnabled(True) # Habilitar orden
        
        header = self.tabla_gastos.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Fecha
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Equipo
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Cuenta
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Categoría
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Subcategoría
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)          # Descripción
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents) # Monto
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)          # Comentario

    def _crear_totales(self, layout: QHBoxLayout):
        """Crea los labels de totales."""
        self.lbl_total_gastos = QLabel("Total Gastos: 0")
        self.lbl_monto_total_gastos = QLabel("Monto Total: 0.00")
        
        layout.addStretch()
        layout.addWidget(self.lbl_total_gastos)
        layout.addSpacing(20)
        layout.addWidget(self.lbl_monto_total_gastos)

    def actualizar_mapas(self, mapas: dict):
        """Recibe los mapas desde la ventana principal y puebla los filtros."""
        self.equipos_mapa = mapas.get("equipos", {})
        self.cuentas_mapa = mapas.get("cuentas", {})
        self.categorias_mapa = mapas.get("categorias", {})
        self.subcategorias_mapa = mapas.get("subcategorias", {})
        
        logger.info("GastosEquipos: Mapas recibidos. Poblando filtros...")

        try:
            # --- Poblar Equipos ---
            self.combo_equipo_gastos.clear()
            self.combo_equipo_gastos.addItem("Todos", None)
            for eq_id, nombre in sorted(self.equipos_mapa.items(), key=lambda item: item[1]):
                self.combo_equipo_gastos.addItem(nombre, eq_id)
                
            # --- Poblar Cuentas ---
            self.combo_cuenta_gastos.clear()
            self.combo_cuenta_gastos.addItem("Todas", None)
            for ct_id, nombre in sorted(self.cuentas_mapa.items(), key=lambda item: item[1]):
                self.combo_cuenta_gastos.addItem(nombre, ct_id)
                
            # --- Poblar Categorías ---
            self.combo_categoria_gastos.clear()
            self.combo_categoria_gastos.addItem("Todas", None)
            for cat_id, nombre in sorted(self.categorias_mapa.items(), key=lambda item: item[1]):
                self.combo_categoria_gastos.addItem(nombre, cat_id)

        except Exception as e:
            logger.error(f"Error al poblar filtros de gastos: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"No se pudieron cargar los filtros de gastos: {e}")

    def _cargar_gastos(self):
        """Carga los gastos desde Firebase usando los filtros seleccionados."""
        # No cargar si los mapas no están listos
        if not self.equipos_mapa:
            logger.warning("GastosEquipos: Mapas no listos, saltando carga.")
            return

        filtros = {}
        
        # Recolectar filtros de fecha
        filtros['fecha_inicio'] = self.date_desde_gastos.date().toString("yyyy-MM-dd")
        filtros['fecha_fin'] = self.date_hasta_gastos.date().toString("yyyy-MM-dd")

        # Recolectar filtros de combos
        if self.combo_equipo_gastos.currentData():
            filtros['equipo_id'] = self.combo_equipo_gastos.currentData()
        if self.combo_cuenta_gastos.currentData():
            filtros['cuenta_id'] = self.combo_cuenta_gastos.currentData()
        if self.combo_categoria_gastos.currentData():
            filtros['categoria_id'] = self.combo_categoria_gastos.currentData()
            
        try:
            logger.info(f"Cargando gastos con filtros: {filtros}")
            self.gastos_cargados = self.fm.obtener_gastos(filtros)
            
            self.tabla_gastos.setSortingEnabled(False) # Deshabilitar orden mientras se puebla
            self.tabla_gastos.setRowCount(0) # Limpiar tabla
            if not self.gastos_cargados:
                logger.warning("No se encontraron gastos con esos filtros.")
                self.lbl_total_gastos.setText("Total Gastos: 0")
                self.lbl_monto_total_gastos.setText("Monto Total: 0.00")
                return

            self.tabla_gastos.setRowCount(len(self.gastos_cargados))
            total_monto_gastos = 0.0
            
            for row, gasto in enumerate(self.gastos_cargados):
                # --- ¡INICIO DE CORRECCIÓN (V7)! ---
                # Forzar la conversión a int y luego a str para llaves de mapa
                try:
                    equipo_id = str(int(gasto.get('equipo_id', 0)))
                except (ValueError, TypeError):
                    equipo_id = "0"
                
                try:
                    cuenta_id = str(int(gasto.get('cuenta_id', 0)))
                except (ValueError, TypeError):
                    cuenta_id = "0"
                
                try:
                    categoria_id = str(int(gasto.get('categoria_id', 0)))
                except (ValueError, TypeError):
                    categoria_id = "0"
                    
                try:
                    subcategoria_id = str(int(gasto.get('subcategoria_id', 0)))
                except (ValueError, TypeError):
                    subcategoria_id = "0"
                # --- FIN DE CORRECCIÓN (V7)! ---

                
                equipo_nombre = self.equipos_mapa.get(equipo_id, f"ID: {equipo_id}")
                cuenta_nombre = self.cuentas_mapa.get(cuenta_id, "")
                categoria_nombre = self.categorias_mapa.get(categoria_id, "")
                subcat_nombre = self.subcategorias_mapa.get(subcategoria_id, "")
                
                # --- Poblar la tabla ---
                item_fecha = QTableWidgetItem(gasto.get('fecha', ''))
                # Guardar el ID del documento en la fila (oculto)
                item_fecha.setData(Qt.ItemDataRole.UserRole, gasto['id'])
                self.tabla_gastos.setItem(row, 0, item_fecha)
                
                self.tabla_gastos.setItem(row, 1, QTableWidgetItem(equipo_nombre))
                self.tabla_gastos.setItem(row, 2, QTableWidgetItem(cuenta_nombre))
                self.tabla_gastos.setItem(row, 3, QTableWidgetItem(categoria_nombre))
                self.tabla_gastos.setItem(row, 4, QTableWidgetItem(subcat_nombre))
                
                self.tabla_gastos.setItem(row, 5, QTableWidgetItem(gasto.get('descripcion', '')))
                
                monto = gasto.get('monto', 0)
                total_monto_gastos += float(monto)
                self.tabla_gastos.setItem(row, 6, QTableWidgetItem(f"{float(monto):,.2f}"))
                
                self.tabla_gastos.setItem(row, 7, QTableWidgetItem(gasto.get('comentario', '')))
                

            # Actualizar totales
            self.lbl_total_gastos.setText(f"Total Gastos: {len(self.gastos_cargados)}")
            self.lbl_monto_total_gastos.setText(f"Monto Total: {total_monto_gastos:,.2f}")
            self.tabla_gastos.setSortingEnabled(True) # Habilitar orden

        except Exception as e:
            logger.error(f"Error al cargar gastos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los gastos (¿Falta un índice en Firebase?):\n\n{e}")

    def _obtener_id_seleccionado_gasto(self):
        """Obtiene el ID de Firestore del item seleccionado en la tabla."""
        selected_items = self.tabla_gastos.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Sin Selección", "Por favor, seleccione un gasto de la tabla.")
            return None
        
        selected_row = selected_items[0].row()
        item_con_id = self.tabla_gastos.item(selected_row, 0) # El ID está en la primera columna
        gasto_id = item_con_id.data(Qt.ItemDataRole.UserRole)
        return gasto_id

    def abrir_dialogo_gasto(self, gasto_id: str = None):
        """Abre el diálogo para crear o editar un gasto."""
        if gasto_id is False: # Señal de "Nuevo"
            gasto_id = None
            
        QMessageBox.information(self, "En desarrollo", f"Aquí se abriría el diálogo para el ID: {gasto_id if gasto_id else 'Nuevo'}")
        
    def editar_gasto_seleccionado(self):
        """Abre el diálogo de edición para el gasto seleccionado."""
        gasto_id = self._obtener_id_seleccionado_gasto()
        if gasto_id:
            self.abrir_dialogo_gasto(gasto_id)

    def eliminar_gasto_seleccionado(self):
        """Elimina el gasto seleccionado tras confirmación."""
        gasto_id = self._obtener_id_seleccionado_gasto()
        if gasto_id:
            reply = QMessageBox.question(self, "Confirmar Eliminación",
                                         f"¿Está seguro de que desea eliminar este gasto (ID: {gasto_id})?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    if self.fm.eliminar_gasto(gasto_id):
                        QMessageBox.information(self, "Éxito", "Gasto eliminado correctamente.")
                        self._cargar_gastos()
                        self.recargar_dashboard.emit()
                    else:
                        QMessageBox.warning(self, "Error", "No se pudo eliminar el gasto.")
                except Exception as e:
                    logger.error(f"Error al eliminar gasto {gasto_id}: {e}")
                    QMessageBox.critical(self, "Error", f"Error al eliminar:\n{e}")