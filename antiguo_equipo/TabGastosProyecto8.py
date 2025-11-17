import sqlite3
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QTableWidget,
    QTableWidgetItem, QLineEdit, QDateEdit, QMessageBox, QFileDialog, QHeaderView
)
from PyQt6.QtCore import QDate, Qt
import datetime

class TabGastosProyecto8(QWidget):
    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        self._build_ui()
        self.recargar_filtros()
        self.cargar_gastos()

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

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(9)
        self.tabla.setHorizontalHeaderLabels([
            "Fecha", "Cuenta", "Categoría", "Subcategoría", "Equipo",
            "Descripción", "Monto", "Comentario", "ID"
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
        self.tabla.setColumnWidth(8, 80)    # ID (oculta si no quieres mostrarla)

        self.tabla.verticalHeader().setDefaultSectionSize(26)  # Alto de fila compacto

        layout.addWidget(self.tabla)

        # Resumen abajo
        self.lbl_resumen = QLabel("Total Gastos: RD$ 0.00")
        layout.addWidget(self.lbl_resumen)

        self.setLayout(layout)

    def recargar_filtros(self):
        # Cuentas usadas en proyecto 8
        cuentas = self._fetchall("SELECT DISTINCT c.id, c.nombre FROM transacciones t JOIN cuentas c ON t.cuenta_id = c.id WHERE t.proyecto_id = 8 ORDER BY c.nombre")
        self.cuenta_cb.clear()
        self.cuenta_cb.addItem("Todas", None)
        for c in cuentas:
            self.cuenta_cb.addItem(c["nombre"], c["id"])

        # Categorías usadas en proyecto 8 (solo gastos)
        cats = self._fetchall("SELECT DISTINCT ca.id, ca.nombre FROM transacciones t JOIN categorias ca ON t.categoria_id = ca.id WHERE t.proyecto_id = 8 AND t.tipo = 'Gasto' ORDER BY ca.nombre")
        self.categoria_cb.clear()
        for c in cats:
            self.categoria_cb.addItem(c["nombre"], c["id"])
        # Esto disparará _on_categoria_change que carga subcategoría

        # Equipos del proyecto 8
        equipos = self._fetchall("SELECT DISTINCT nombre FROM equipos WHERE proyecto_id = 8 ORDER BY nombre")
        self.equipo_cb.clear()
        self.equipo_cb.addItem("Todos", None)
        for eq in equipos:
            self.equipo_cb.addItem(eq["nombre"], eq["nombre"])

    def _on_categoria_change(self):
        # Subcategorías para la categoría seleccionada en este proyecto
        cat_id = self.categoria_cb.currentData()
        if cat_id is None:
            self.subcategoria_cb.clear()
            self.subcategoria_cb.addItem("Todas", None)
            return
        subcats = self._fetchall(
            "SELECT DISTINCT s.id, s.nombre FROM transacciones t JOIN subcategorias s ON t.subcategoria_id = s.id WHERE t.proyecto_id = 8 AND t.categoria_id = ? AND t.tipo = 'Gasto' ORDER BY s.nombre",
            (cat_id,)
        )
        self.subcategoria_cb.clear()
        self.subcategoria_cb.addItem("Todas", None)
        for s in subcats:
            self.subcategoria_cb.addItem(s["nombre"], s["id"])
        self.cargar_gastos()

    def cargar_gastos(self):
        q = """
            SELECT t.id, t.fecha, c.nombre as cuenta, ca.nombre as categoria, s.nombre as subcategoria,
                   t.descripcion, t.monto, t.comentario, eq.nombre as equipo
            FROM transacciones t
                LEFT JOIN cuentas c ON t.cuenta_id = c.id
                LEFT JOIN categorias ca ON t.categoria_id = ca.id
                LEFT JOIN subcategorias s ON t.subcategoria_id = s.id
                LEFT JOIN equipos eq ON t.equipo_id = eq.id
            WHERE t.proyecto_id = 8 AND t.tipo = 'Gasto'
              AND (t.cuenta_id = :cuenta_id OR :cuenta_id IS NULL)
              AND (t.categoria_id = :categoria_id OR :categoria_id IS NULL)
              AND (t.subcategoria_id = :subcategoria_id OR :subcategoria_id IS NULL)
              AND (eq.nombre = :equipo OR :equipo IS NULL)
              AND date(t.fecha) BETWEEN :fecha_desde AND :fecha_hasta
              AND (
                    :texto='' OR
                    t.descripcion LIKE '%'||:texto||'%' OR
                    t.comentario LIKE '%'||:texto||'%'
              )
            ORDER BY date(t.fecha) DESC, t.id DESC
        """
        params = {
            "cuenta_id": self.cuenta_cb.currentData(),
            "categoria_id": self.categoria_cb.currentData(),
            "subcategoria_id": self.subcategoria_cb.currentData(),
            "equipo": self.equipo_cb.currentData(),
            "fecha_desde": self.fecha_desde.date().toString("yyyy-MM-dd"),
            "fecha_hasta": self.fecha_hasta.date().toString("yyyy-MM-dd"),
            "texto": self.texto_busqueda.text().strip()
        }
        filas = self._fetchall(q, params)
        self.tabla.setRowCount(0)
        total_gastos = 0.0
        for row in filas:
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
            self.tabla.setItem(idx, 8, QTableWidgetItem(str(row["id"])))
            total_gastos += row["monto"] or 0.0
        self.resumen_label.setText(f"Total Gastos: RD$ {total_gastos:,.2f}")
        self.tabla.resizeColumnsToContents()

    def _fetchall(self, q, params=None):
        cur = self.conn.cursor()
        if params is None:
            cur.execute(q)
        else:
            cur.execute(q, params)
        return [dict(row) for row in cur.fetchall()]

    def nuevo_gasto(self):
        QMessageBox.information(self, "Próximamente", "Aquí irá el formulario para añadir un gasto.")

# Para pruebas independientes
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QFileDialog
    app = QApplication(sys.argv)
    db_path, _ = QFileDialog.getOpenFileName(
        None, "Selecciona tu Base de Datos", "", "Archivos DB (*.db *.sqlite *.sqlite3)"
    )
    if not db_path:
        print("No DB selected.")
        sys.exit(0)
    w = TabGastosProyecto8(db_path)
    w.resize(1200, 700)
    w.show()
    sys.exit(app.exec())