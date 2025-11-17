import sqlite3
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget, QTableWidgetItem,
    QLineEdit, QDateEdit, QPushButton, QMessageBox, QHeaderView
)
from PyQt6.QtCore import QDate, Qt
from DialogoGastoEquipo import DialogoGastoEquipo

class TabGastosEquipos(QWidget):
    def __init__(self, db_manager, proyecto_id=8, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.proyecto_id = proyecto_id

        self._build_ui()
        self._cargar_filtros()
        self._cargar_gastos()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Filtros arriba
        filtros_layout = QHBoxLayout()
        self.cuenta_cb = QComboBox()
        self.categoria_cb = QComboBox()
        self.subcategoria_cb = QComboBox()
        self.equipo_cb = QComboBox()
        self.fecha_desde = QDateEdit()
        self.fecha_hasta = QDateEdit()
        self.buscar_edit = QLineEdit()
        filtros_layout.addWidget(QLabel("Cuenta:"))
        filtros_layout.addWidget(self.cuenta_cb)
        filtros_layout.addWidget(QLabel("Categoría:"))
        filtros_layout.addWidget(self.categoria_cb)
        filtros_layout.addWidget(QLabel("Subcategoría:"))
        filtros_layout.addWidget(self.subcategoria_cb)
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
        self.btn_aniadir = QPushButton("Añadir Gasto")
        self.btn_editar = QPushButton("Editar Seleccionado")
        self.btn_eliminar = QPushButton("Eliminar Seleccionado")
        btn_layout.addWidget(self.btn_aniadir)
        btn_layout.addWidget(self.btn_editar)
        btn_layout.addWidget(self.btn_eliminar)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        # Tabla (sin columna ID)
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "Fecha", "Cuenta", "Categoría", "Subcategoría", "Equipo",
            "Descripción", "Monto", "Comentario"
        ])
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.tabla.setColumnWidth(0, 90)    # Fecha
        self.tabla.setColumnWidth(1, 120)   # Cuenta
        self.tabla.setColumnWidth(2, 120)   # Categoría
        self.tabla.setColumnWidth(3, 130)   # Subcategoría
        self.tabla.setColumnWidth(4, 120)   # Equipo
        self.tabla.setColumnWidth(5, 200)   # Descripción
        self.tabla.setColumnWidth(6, 100)   # Monto
        self.tabla.setColumnWidth(7, 220)   # Comentario

        self.tabla.verticalHeader().setDefaultSectionSize(26)  # Alto de fila compacto

        # ... (todo tu código previo)

        layout.addWidget(self.tabla)

        # Resumen abajo
        self.lbl_resumen = QLabel("Total Gastos: RD$ 0.00")
        layout.addWidget(self.lbl_resumen)

        # CONEXIONES DE BOTONES
        self.btn_aniadir.clicked.connect(self._nuevo_gasto)
        self.btn_editar.clicked.connect(self._editar_gasto)
        self.btn_eliminar.clicked.connect(self._eliminar_gasto)

        self.setLayout(layout)
                
    def _cargar_filtros(self):
        # Fecha inicial automática (primera transacción)
        fecha_primera = self.db.fetchone(
            "SELECT fecha FROM transacciones WHERE proyecto_id = ? AND tipo = 'Gasto' ORDER BY fecha ASC LIMIT 1",
            (self.proyecto_id,)
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

        self.categoria_cb.clear()
        self.categoria_cb.addItem("Todas", None)
        cats = self.db.obtener_categorias_por_proyecto(self.proyecto_id, tipo="Gasto")
        for c in cats:
            self.categoria_cb.addItem(c["nombre"], c["id"])
        self.categoria_cb.setCurrentIndex(0)  # Selecciona "Todas" al iniciar

        self._on_categoria_change()

        self.equipo_cb.clear()
        self.equipo_cb.addItem("Todos", None)
        equipos = self.db.obtener_equipos_por_proyecto(self.proyecto_id)
        for e in equipos:
            self.equipo_cb.addItem(e["nombre"], e["id"])

    def _on_categoria_change(self):
        self.subcategoria_cb.clear()
        self.subcategoria_cb.addItem("Todas", None)
        cat_id = self.categoria_cb.currentData()
        if cat_id is None:
            # Si "Todas", muestra todas las subcategorías posibles
            subcats = self.db.fetchall(
                "SELECT DISTINCT id, nombre FROM subcategorias WHERE id IN (SELECT subcategoria_id FROM transacciones WHERE proyecto_id = ? AND tipo = 'Gasto') ORDER BY nombre",
                (self.proyecto_id,)
            )
        else:
            subcats = self.db.obtener_subcategorias_por_categoria(cat_id)
        for s in subcats:
            self.subcategoria_cb.addItem(s["nombre"], s["id"])
        self.subcategoria_cb.setCurrentIndex(0)
        self._cargar_gastos()

    def _cargar_gastos(self):
        filtros = {
            "cuenta_id": self.cuenta_cb.currentData(),
            "categoria_id": self.categoria_cb.currentData(),
            "subcategoria_id": self.subcategoria_cb.currentData(),
            "equipo_id": self.equipo_cb.currentData(),
            "fecha_desde": self.fecha_desde.date().toString("yyyy-MM-dd"),
            "fecha_hasta": self.fecha_hasta.date().toString("yyyy-MM-dd"),
            "texto": self.buscar_edit.text().strip() or None,
        }
        self._gastos_actuales = self.db.obtener_gastos_equipo(self.proyecto_id, filtros)
        self.tabla.setRowCount(0)
        total = 0.0
        for row in self._gastos_actuales:
            idx = self.tabla.rowCount()
            self.tabla.insertRow(idx)
            self.tabla.setItem(idx, 0, QTableWidgetItem(str(row["fecha"])))
            self.tabla.setItem(idx, 1, QTableWidgetItem(str(row["cuenta"] or "")))
            self.tabla.setItem(idx, 2, QTableWidgetItem(str(row["categoria"] or "")))
            self.tabla.setItem(idx, 3, QTableWidgetItem(str(row["subcategoria"] or "")))
            self.tabla.setItem(idx, 4, QTableWidgetItem(str(row["equipo"] or "")))
            self.tabla.setItem(idx, 5, QTableWidgetItem(str(row["descripcion"] or "")))
            self.tabla.setItem(idx, 6, QTableWidgetItem(f"RD$ {row['monto']:,.2f}"))
            self.tabla.setItem(idx, 7, QTableWidgetItem(str(row["comentario"] or "")))
            total += row["monto"] or 0.0
        self.lbl_resumen.setText(f"Total Gastos: RD$ {total:,.2f}")
        self.tabla.resizeRowsToContents()

    def _nuevo_gasto(self):
        dialogo = DialogoGastoEquipo(self.db, self.proyecto_id, self)
        if dialogo.exec():
            self._cargar_filtros()
            self._cargar_gastos()

    def _editar_gasto(self):
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._gastos_actuales):
            QMessageBox.warning(self, "Edición", "Selecciona un gasto para editar.")
            return
        gasto = self._gastos_actuales[fila]
        dialogo = DialogoGastoEquipo(self.db, self.proyecto_id, self, gasto=gasto)
        if dialogo.exec():
            self._cargar_filtros()
            self._cargar_gastos()

    def _eliminar_gasto(self):
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._gastos_actuales):
            QMessageBox.warning(self, "Eliminación", "Selecciona un gasto para eliminar.")
            return
        gasto = self._gastos_actuales[fila]
        reply = QMessageBox.question(
            self, "Eliminar Gasto",
            f"¿Seguro que deseas eliminar el gasto?\n\n{gasto['descripcion']}\nMonto: RD$ {gasto['monto']:,.2f}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            exito = self.db.eliminar_gasto_equipo(gasto['id'])
            if exito:
                self._cargar_filtros()
                self._cargar_gastos()
                QMessageBox.information(self, "Eliminado", "Gasto eliminado correctamente.")
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el gasto.")