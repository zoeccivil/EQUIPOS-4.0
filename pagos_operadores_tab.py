"""
Pagos a Operadores Tab para EQUIPOS 4.0
Adaptado para trabajar con Firebase en lugar de SQLite
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget, QTableWidgetItem,
    QLineEdit, QDateEdit, QPushButton, QMessageBox, QHeaderView
)
from PyQt6.QtCore import QDate, Qt
from firebase_manager import FirebaseManager


class TabPagosOperadores(QWidget):
    def __init__(self, firebase_manager: FirebaseManager, parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self._pagos_actuales = []

        self._build_ui()
        self._cargar_filtros()
        self._cargar_pagos()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Filtros arriba
        filtros_layout = QHBoxLayout()
        self.operador_cb = QComboBox()
        self.equipo_cb = QComboBox()
        self.fecha_desde = QDateEdit()
        self.fecha_hasta = QDateEdit()
        self.buscar_edit = QLineEdit()
        
        filtros_layout.addWidget(QLabel("Operador:"))
        filtros_layout.addWidget(self.operador_cb)
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
        self.btn_aniadir = QPushButton("Añadir Pago")
        self.btn_editar = QPushButton("Editar Seleccionado")
        self.btn_eliminar = QPushButton("Eliminar Seleccionado")
        btn_layout.addWidget(self.btn_aniadir)
        btn_layout.addWidget(self.btn_editar)
        btn_layout.addWidget(self.btn_eliminar)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels([
            "Fecha", "Operador", "Equipo", "Horas", "Monto", "Descripción"
        ])
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.tabla.setColumnWidth(0, 90)   # Fecha
        self.tabla.setColumnWidth(1, 140)  # Operador
        self.tabla.setColumnWidth(2, 130)  # Equipo
        self.tabla.setColumnWidth(3, 60)   # Horas
        self.tabla.setColumnWidth(4, 100)  # Monto

        self.tabla.verticalHeader().setDefaultSectionSize(26)

        layout.addWidget(self.tabla)

        # Resumen abajo
        self.lbl_resumen = QLabel("Total Pagado: RD$ 0.00 | Total Horas: 0.00")
        layout.addWidget(self.lbl_resumen)

        # CONEXIONES DE BOTONES
        self.btn_aniadir.clicked.connect(self._nuevo_pago)
        self.btn_editar.clicked.connect(self._editar_pago)
        self.btn_eliminar.clicked.connect(self._eliminar_pago)
        
        # Conexiones de filtros
        self.operador_cb.currentIndexChanged.connect(self._cargar_pagos)
        self.equipo_cb.currentIndexChanged.connect(self._cargar_pagos)
        self.fecha_desde.dateChanged.connect(self._cargar_pagos)
        self.fecha_hasta.dateChanged.connect(self._cargar_pagos)
        self.buscar_edit.textChanged.connect(self._cargar_pagos)

        self.setLayout(layout)

    def _cargar_filtros(self):
        """Carga los filtros iniciales"""
        # Establecer fechas
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_desde.setCalendarPopup(True)
        self.fecha_hasta.setDate(QDate.currentDate())
        self.fecha_hasta.setCalendarPopup(True)

        # Cargar operadores
        self.operador_cb.clear()
        self.operador_cb.addItem("Todos", None)
        try:
            operadores = self.fm.obtener_entidades(tipo='Operador') or []
            for o in operadores:
                self.operador_cb.addItem(o.get("nombre", ""), o.get("id"))
        except Exception as e:
            print(f"Error cargando operadores: {e}")

        # Cargar equipos
        self.equipo_cb.clear()
        self.equipo_cb.addItem("Todos", None)
        try:
            equipos = self.fm.obtener_equipos() or []
            for e in equipos:
                self.equipo_cb.addItem(e.get("nombre", ""), e.get("id"))
        except Exception as e:
            print(f"Error cargando equipos: {e}")

    def _cargar_pagos(self):
        """Carga los pagos según los filtros actuales"""
        filtros = {
            'fecha_inicio': self.fecha_desde.date().toString("yyyy-MM-dd"),
            'fecha_fin': self.fecha_hasta.date().toString("yyyy-MM-dd"),
        }
        
        operador_id = self.operador_cb.currentData()
        if operador_id:
            filtros['operador_id'] = operador_id
        
        equipo_id = self.equipo_cb.currentData()
        if equipo_id:
            filtros['equipo_id'] = equipo_id
        
        texto_busqueda = self.buscar_edit.text().strip()
        
        try:
            self._pagos_actuales = self.fm.obtener_pagos_operadores(filtros) or []
            
            # Filtro de texto en memoria
            if texto_busqueda:
                texto_lower = texto_busqueda.lower()
                self._pagos_actuales = [
                    p for p in self._pagos_actuales
                    if texto_lower in p.get('descripcion', '').lower()
                ]
            
            self.tabla.setRowCount(0)
            total_monto = 0.0
            total_horas = 0.0
            
            for row in self._pagos_actuales:
                idx = self.tabla.rowCount()
                self.tabla.insertRow(idx)
                
                # Guardar ID en primera celda
                item_fecha = QTableWidgetItem(str(row.get("fecha", "")))
                item_fecha.setData(Qt.ItemDataRole.UserRole, row.get("id"))
                self.tabla.setItem(idx, 0, item_fecha)
                
                # Operador
                operador_nombre = self._get_nombre_entidad(row.get("operador_id"))
                self.tabla.setItem(idx, 1, QTableWidgetItem(operador_nombre))
                
                # Equipo
                equipo_nombre = self._get_nombre_equipo(row.get("equipo_id"))
                self.tabla.setItem(idx, 2, QTableWidgetItem(equipo_nombre))
                
                # Horas
                horas = row.get("horas", 0)
                try:
                    horas_float = float(horas) if horas is not None else 0.0
                except:
                    horas_float = 0.0
                self.tabla.setItem(idx, 3, QTableWidgetItem(f"{horas_float:.2f}"))
                
                # Monto
                monto = row.get("monto", 0)
                self.tabla.setItem(idx, 4, QTableWidgetItem(f"RD$ {monto:,.2f}"))
                
                # Descripción
                self.tabla.setItem(idx, 5, QTableWidgetItem(str(row.get("descripcion", ""))))
                
                total_monto += monto
                total_horas += horas_float
            
            self.lbl_resumen.setText(f"Total Pagado: RD$ {total_monto:,.2f} | Total Horas: {total_horas:.2f}")
            self.tabla.resizeRowsToContents()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error cargando pagos: {e}")

    def _nuevo_pago(self):
        """Añade un nuevo pago (simplificado)"""
        QMessageBox.information(self, "Info", 
                               "Función de registro completa pendiente de implementar.\n"
                               "Use la consola de Firebase temporalmente.")

    def _editar_pago(self):
        """Edita el pago seleccionado"""
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._pagos_actuales):
            QMessageBox.warning(self, "Edición", "Selecciona un pago para editar.")
            return
        
        QMessageBox.information(self, "Info", 
                               "Función de edición completa pendiente de implementar.\n"
                               "Use la consola de Firebase temporalmente.")

    def _eliminar_pago(self):
        """Elimina el pago seleccionado"""
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._pagos_actuales):
            QMessageBox.warning(self, "Eliminación", "Selecciona un pago para eliminar.")
            return
        
        pago = self._pagos_actuales[fila]
        reply = QMessageBox.question(
            self, "Eliminar Pago",
            f"¿Seguro que deseas eliminar el pago?\n\n{pago.get('descripcion', '')}\nMonto: RD$ {pago.get('monto', 0):,.2f}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.fm.eliminar_pago_operador(pago['id'])
                self._cargar_pagos()
                QMessageBox.information(self, "Eliminado", "Pago eliminado correctamente.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo eliminar el pago: {e}")

    def _get_nombre_entidad(self, entidad_id):
        """Obtiene el nombre de una entidad por ID"""
        if not entidad_id:
            return ""
        try:
            entidad = self.fm.obtener_entidad(entidad_id)
            return entidad.get('nombre', '') if entidad else ''
        except:
            return ""

    def _get_nombre_equipo(self, equipo_id):
        """Obtiene el nombre de un equipo por ID"""
        if not equipo_id:
            return ""
        try:
            equipo = self.fm.obtener_equipo(equipo_id)
            return equipo.get('nombre', '') if equipo else ''
        except:
            return ""
