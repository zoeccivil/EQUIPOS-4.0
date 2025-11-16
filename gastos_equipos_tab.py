"""
Gastos de Equipos Tab para EQUIPOS 4.0
Adaptado para trabajar con Firebase en lugar de SQLite
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget, QTableWidgetItem,
    QLineEdit, QDateEdit, QPushButton, QMessageBox, QHeaderView
)
from PyQt6.QtCore import QDate, Qt
from firebase_manager import FirebaseManager


class TabGastosEquipos(QWidget):
    def __init__(self, firebase_manager: FirebaseManager, parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self._gastos_actuales = []

        self._build_ui()
        self._cargar_filtros()
        self._cargar_gastos()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Filtros arriba
        filtros_layout = QHBoxLayout()
        
        self.equipo_cb = QComboBox()
        self.fecha_desde = QDateEdit()
        self.fecha_hasta = QDateEdit()
        self.buscar_edit = QLineEdit()
        
        filtros_layout.addWidget(QLabel("Equipo:"))
        filtros_layout.addWidget(self.equipo_cb)
        filtros_layout.addWidget(QLabel("Desde:"))
        filtros_layout.addWidget(self.fecha_desde)
        filtros_layout.addWidget(QLabel("Hasta:"))
        filtros_layout.addWidget(self.fecha_hasta)
        filtros_layout.addWidget(QLabel("Buscar:"))
        filtros_layout.addWidget(self.buscar_edit)
        layout.addLayout(filtros_layout)

        # Botones
        btn_layout = QHBoxLayout()
        self.btn_aniadir = QPushButton("Añadir Gasto")
        self.btn_editar = QPushButton("Editar Seleccionado")
        self.btn_eliminar = QPushButton("Eliminar Seleccionado")
        btn_layout.addWidget(self.btn_aniadir)
        btn_layout.addWidget(self.btn_editar)
        btn_layout.addWidget(self.btn_eliminar)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        # Tabla (simplificada sin cuentas/categorías)
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(5)
        self.tabla.setHorizontalHeaderLabels([
            "Fecha", "Equipo", "Descripción", "Monto", "Comentario"
        ])
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.tabla.setColumnWidth(0, 90)    # Fecha
        self.tabla.setColumnWidth(1, 150)   # Equipo
        self.tabla.setColumnWidth(2, 250)   # Descripción
        self.tabla.setColumnWidth(3, 100)   # Monto
        
        self.tabla.verticalHeader().setDefaultSectionSize(26)

        layout.addWidget(self.tabla)

        # Resumen abajo
        self.lbl_resumen = QLabel("Total Gastos: RD$ 0.00")
        layout.addWidget(self.lbl_resumen)

        # CONEXIONES DE BOTONES
        self.btn_aniadir.clicked.connect(self._nuevo_gasto)
        self.btn_editar.clicked.connect(self._editar_gasto)
        self.btn_eliminar.clicked.connect(self._eliminar_gasto)
        
        # Conexiones de filtros
        self.equipo_cb.currentIndexChanged.connect(self._cargar_gastos)
        self.fecha_desde.dateChanged.connect(self._cargar_gastos)
        self.fecha_hasta.dateChanged.connect(self._cargar_gastos)
        self.buscar_edit.textChanged.connect(self._cargar_gastos)

        self.setLayout(layout)

    def _cargar_filtros(self):
        """Carga los filtros iniciales"""
        # Establecer fechas
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_desde.setCalendarPopup(True)
        self.fecha_hasta.setDate(QDate.currentDate())
        self.fecha_hasta.setCalendarPopup(True)

        # Cargar equipos
        self.equipo_cb.clear()
        self.equipo_cb.addItem("Todos", None)
        try:
            equipos = self.fm.obtener_equipos() or []
            for e in equipos:
                self.equipo_cb.addItem(e.get("nombre", ""), e.get("id"))
        except Exception as e:
            print(f"Error cargando equipos: {e}")

    def _cargar_gastos(self):
        """Carga los gastos según los filtros actuales"""
        filtros = {
            'tipo': 'Gasto',
            'fecha_inicio': self.fecha_desde.date().toString("yyyy-MM-dd"),
            'fecha_fin': self.fecha_hasta.date().toString("yyyy-MM-dd"),
        }
        
        equipo_id = self.equipo_cb.currentData()
        if equipo_id:
            filtros['equipo_id'] = equipo_id
        
        texto_busqueda = self.buscar_edit.text().strip()
        if texto_busqueda:
            # Firebase no soporta búsqueda de texto, filtraremos en memoria
            pass
        
        try:
            self._gastos_actuales = self.fm.obtener_transacciones(filtros) or []
            
            # Filtro de texto en memoria
            if texto_busqueda:
                texto_lower = texto_busqueda.lower()
                self._gastos_actuales = [
                    g for g in self._gastos_actuales
                    if texto_lower in g.get('descripcion', '').lower() or
                       texto_lower in g.get('comentario', '').lower()
                ]
            
            self.tabla.setRowCount(0)
            total = 0.0
            
            for row in self._gastos_actuales:
                idx = self.tabla.rowCount()
                self.tabla.insertRow(idx)
                
                # Guardar ID en primera celda
                item_fecha = QTableWidgetItem(str(row.get("fecha", "")))
                item_fecha.setData(Qt.ItemDataRole.UserRole, row.get("id"))
                self.tabla.setItem(idx, 0, item_fecha)
                
                # Equipo
                equipo_nombre = self._get_nombre_equipo(row.get("equipo_id"))
                self.tabla.setItem(idx, 1, QTableWidgetItem(equipo_nombre))
                
                # Otros campos
                self.tabla.setItem(idx, 2, QTableWidgetItem(str(row.get("descripcion", ""))))
                self.tabla.setItem(idx, 3, QTableWidgetItem(f"RD$ {row.get('monto', 0):,.2f}"))
                self.tabla.setItem(idx, 4, QTableWidgetItem(str(row.get("comentario", ""))))
                
                total += row.get("monto", 0)
            
            self.lbl_resumen.setText(f"Total Gastos: RD$ {total:,.2f}")
            self.tabla.resizeRowsToContents()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error cargando gastos: {e}")

    def _nuevo_gasto(self):
        """Añade un nuevo gasto (simplificado)"""
        QMessageBox.information(self, "Info", 
                               "Función de registro completa pendiente de implementar.\n"
                               "Use la consola de Firebase temporalmente.")

    def _editar_gasto(self):
        """Edita el gasto seleccionado"""
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._gastos_actuales):
            QMessageBox.warning(self, "Edición", "Selecciona un gasto para editar.")
            return
        
        QMessageBox.information(self, "Info", 
                               "Función de edición completa pendiente de implementar.\n"
                               "Use la consola de Firebase temporalmente.")

    def _eliminar_gasto(self):
        """Elimina el gasto seleccionado"""
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._gastos_actuales):
            QMessageBox.warning(self, "Eliminación", "Selecciona un gasto para eliminar.")
            return
        
        gasto = self._gastos_actuales[fila]
        reply = QMessageBox.question(
            self, "Eliminar Gasto",
            f"¿Seguro que deseas eliminar el gasto?\n\n{gasto.get('descripcion', '')}\nMonto: RD$ {gasto.get('monto', 0):,.2f}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.fm.eliminar_transaccion(gasto['id'])
                self._cargar_gastos()
                QMessageBox.information(self, "Eliminado", "Gasto eliminado correctamente.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo eliminar el gasto: {e}")

    def _get_nombre_equipo(self, equipo_id):
        """Obtiene el nombre de un equipo por ID"""
        if not equipo_id:
            return ""
        try:
            equipo = self.fm.obtener_equipo(equipo_id)
            return equipo.get('nombre', '') if equipo else ''
        except:
            return ""
