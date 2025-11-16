from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget, QTableWidgetItem,
    QLineEdit, QDateEdit, QPushButton, QMessageBox, QHeaderView
)
from PyQt6.QtCore import QDate, Qt
from DialogoPagoOperador import DialogoPagoOperador

class TabPagosOperadores(QWidget):
    def __init__(self, db_manager, proyecto_id=8, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.proyecto_id = proyecto_id

        self._build_ui()
        self._cargar_filtros()
        self._cargar_pagos()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Filtros arriba
        filtros_layout = QHBoxLayout()
        self.cuenta_cb = QComboBox()
        self.operador_cb = QComboBox()
        self.equipo_cb = QComboBox()
        self.fecha_desde = QDateEdit()
        self.fecha_hasta = QDateEdit()
        self.buscar_edit = QLineEdit()
        filtros_layout.addWidget(QLabel("Cuenta:"))
        filtros_layout.addWidget(self.cuenta_cb)
        filtros_layout.addWidget(QLabel("Operador:"))
        filtros_layout.addWidget(self.operador_cb)
        filtros_layout.addWidget(QLabel("Equipo:"))
        filtros_layout.addWidget(self.equipo_cb)
        filtros_layout.addWidget(QLabel("Desde:"))
        filtros_layout.addWidget(self.fecha_desde)
        filtros_layout.addWidget(QLabel("Hasta:"))
        filtros_layout.addWidget(self.fecha_hasta)
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
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "Fecha", "Cuenta", "Operador", "Equipo", "Horas", "Descripción",
            "Monto", "Comentario"
        ])
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.tabla.setColumnWidth(0, 90)   # Fecha
        self.tabla.setColumnWidth(1, 120)  # Cuenta
        self.tabla.setColumnWidth(2, 140)  # Operador
        self.tabla.setColumnWidth(3, 130)  # Equipo
        self.tabla.setColumnWidth(4, 60)   # Horas
        self.tabla.setColumnWidth(5, 180)  # Descripción
        self.tabla.setColumnWidth(6, 100)  # Monto
        self.tabla.setColumnWidth(7, 220)  # Comentario

        self.tabla.verticalHeader().setDefaultSectionSize(26)  # Alto de fila compacto

        # ... (todo tu código previo)

        layout.addWidget(self.tabla)

        # Resumen abajo
        self.lbl_resumen = QLabel("Total Pagado: RD$ 0.00")
        layout.addWidget(self.lbl_resumen)

        # CONEXIONES DE BOTONES
        self.btn_aniadir.clicked.connect(self._nuevo_pago)
        self.btn_editar.clicked.connect(self._editar_pago)
        self.btn_eliminar.clicked.connect(self._eliminar_pago)

        self.setLayout(layout)

    def _cargar_filtros(self):
        # Fecha inicial automática (primera transacción de pago a operador)
        fecha_primera = self.db.fetchone(
            "SELECT fecha FROM transacciones WHERE proyecto_id = ? AND tipo = 'Gasto' AND categoria_id IN (SELECT id FROM categorias WHERE nombre = ?) ORDER BY fecha ASC LIMIT 1",
            (self.proyecto_id, "PAGO HRS OPERADOR")
        )
        if fecha_primera and fecha_primera.get("fecha"):
            y, m, d = map(int, fecha_primera["fecha"].split("-"))
            self.fecha_desde.setDate(QDate(y, m, d))
        else:
            self.fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_hasta.setDate(QDate.currentDate())

        self.cuenta_cb.clear()
        cuentas = self.db.obtener_cuentas_por_proyecto(self.proyecto_id)
        self.cuenta_cb.addItem("Todas", None)
        for c in cuentas:
            self.cuenta_cb.addItem(c["nombre"], c["id"])

        self.operador_cb.clear()
        self.operador_cb.addItem("Todos", None)
        operadores = self.db.obtener_operadores_por_proyecto(self.proyecto_id)
        for o in operadores:
            self.operador_cb.addItem(o["nombre"], o["id"])

        self.equipo_cb.clear()
        self.equipo_cb.addItem("Todos", None)
        equipos = self.db.obtener_equipos_por_proyecto(self.proyecto_id)
        for e in equipos:
            self.equipo_cb.addItem(e["nombre"], e["id"])

    def _cargar_pagos(self):
        filtros = {
            "cuenta_id": self.cuenta_cb.currentData(),
            "operador_id": self.operador_cb.currentData(),
            "equipo_id": self.equipo_cb.currentData(),
            "fecha_desde": self.fecha_desde.date().toString("yyyy-MM-dd"),
            "fecha_hasta": self.fecha_hasta.date().toString("yyyy-MM-dd"),
            "texto": self.buscar_edit.text().strip() or None,
        }
        self._pagos_actuales = self.db.obtener_pagos_a_operadores(self.proyecto_id, filtros)
        self.tabla.setRowCount(0)
        total = 0.0
        for row in self._pagos_actuales:
            idx = self.tabla.rowCount()
            self.tabla.insertRow(idx)
            self.tabla.setItem(idx, 0, QTableWidgetItem(str(row["fecha"])))
            self.tabla.setItem(idx, 1, QTableWidgetItem(str(row["cuenta"] or "")))
            self.tabla.setItem(idx, 2, QTableWidgetItem(str(row["operador"] or "")))
            self.tabla.setItem(idx, 3, QTableWidgetItem(str(row["equipo"] or "")))
            # CORRECCIÓN: si 'horas' es None o no numérico, muestra 0.00
            horas_valor = row.get("horas")
            try:
                horas_float = float(horas_valor) if horas_valor is not None else 0.0
            except Exception:
                horas_float = 0.0
            self.tabla.setItem(idx, 4, QTableWidgetItem(f"{horas_float:.2f}"))
            self.tabla.setItem(idx, 5, QTableWidgetItem(str(row["descripcion"] or "")))
            self.tabla.setItem(idx, 6, QTableWidgetItem(f"RD$ {row['monto']:,.2f}"))
            self.tabla.setItem(idx, 7, QTableWidgetItem(str(row["comentario"] or "")))
            total += row["monto"] or 0.0
        self.lbl_resumen.setText(f"Total Pagado: RD$ {total:,.2f}")
        self.tabla.resizeRowsToContents()
    def _nuevo_pago(self):
        dialogo = DialogoPagoOperador(self.db, self.proyecto_id, self)
        if dialogo.exec():
            self._cargar_filtros()
            self._cargar_pagos()

    def _editar_pago(self):
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._pagos_actuales):
            QMessageBox.warning(self, "Edición", "Selecciona un pago para editar.")
            return
        pago = self._pagos_actuales[fila]
        dialogo = DialogoPagoOperador(self.db, self.proyecto_id, self, pago=pago)
        if dialogo.exec():
            self._cargar_filtros()
            self._cargar_pagos()

    def _eliminar_pago(self):
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._pagos_actuales):
            QMessageBox.warning(self, "Eliminación", "Selecciona un pago para eliminar.")
            return
        pago = self._pagos_actuales[fila]
        reply = QMessageBox.question(
            self, "Eliminar Pago",
            f"¿Seguro que deseas eliminar el pago?\n\n{pago['descripcion']}\nMonto: RD$ {pago['monto']:,.2f}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            exito = self.db.eliminar_pago_operador(pago['id'])
            if exito:
                self._cargar_filtros()
                self._cargar_pagos()
                QMessageBox.information(self, "Eliminado", "Pago eliminado correctamente.")
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el pago.")