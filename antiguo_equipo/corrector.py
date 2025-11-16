import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QFileDialog, QMessageBox, QListWidgetItem, QComboBox
)
from PyQt6.QtCore import Qt

class CorrectorSubcategoriasApp(QWidget):
    def __init__(self):
        super().__init__()
        self.db_path = None
        self.setWindowTitle("Corrección de Subcategorías con Equipos (Todas las Categorías, Proyecto Id 8)")
        self.setMinimumSize(800, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Selección de Base de Datos
        db_layout = QHBoxLayout()
        self.db_label = QLabel("Base de Datos: (Ninguna seleccionada)")
        db_button = QPushButton("Seleccionar DB")
        db_button.clicked.connect(self.seleccionar_db)
        db_layout.addWidget(self.db_label)
        db_layout.addStretch()
        db_layout.addWidget(db_button)
        layout.addLayout(db_layout)

        # Selección de categoría
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel("Categoría:"))
        self.categoria_combo = QComboBox()
        self.categoria_combo.currentIndexChanged.connect(self.cargar_datos)
        cat_layout.addWidget(self.categoria_combo)
        cat_layout.addStretch()
        layout.addLayout(cat_layout)

        # Listas de Subcategorías y Equipos
        lists_layout = QHBoxLayout()

        # Subcategorías
        subcat_layout = QVBoxLayout()
        subcat_layout.addWidget(QLabel("Subcategorías usadas en transacciones (Proyecto Id=8):"))
        self.subcat_list = QListWidget()
        subcat_layout.addWidget(self.subcat_list)
        lists_layout.addLayout(subcat_layout)

        # Flecha y botón de emparejar
        arrow_layout = QVBoxLayout()
        arrow_layout.addStretch()
        self.match_btn = QPushButton("→ Reemplazar nombre por Equipo")
        self.match_btn.setEnabled(False)
        self.match_btn.clicked.connect(self.reemplazar_subcategoria)
        arrow_layout.addWidget(self.match_btn)
        arrow_layout.addStretch()
        lists_layout.addLayout(arrow_layout)

        # Equipos
        equipos_layout = QVBoxLayout()
        equipos_layout.addWidget(QLabel("Equipos disponibles (Proyecto Id=8):"))
        self.equipos_combo = QComboBox()
        equipos_layout.addWidget(self.equipos_combo)
        lists_layout.addLayout(equipos_layout)

        layout.addLayout(lists_layout)

        # Botón de recarga
        reload_layout = QHBoxLayout()
        self.reload_btn = QPushButton("Recargar Listas")
        self.reload_btn.clicked.connect(self.cargar_datos)
        self.reload_btn.setEnabled(False)
        reload_layout.addStretch()
        reload_layout.addWidget(self.reload_btn)
        layout.addLayout(reload_layout)

    def seleccionar_db(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Selecciona tu Base de Datos", "", "Archivos DB (*.db *.sqlite *.sqlite3)"
        )
        if filepath:
            self.db_path = filepath
            self.db_label.setText(f"Base de Datos: ...{self.db_path[-40:]}")
            self.cargar_categorias()
            self.reload_btn.setEnabled(True)
            self.match_btn.setEnabled(True)

    def cargar_categorias(self):
        """Carga todas las categorías presentes en transacciones del proyecto 8."""
        self.categoria_combo.clear()
        if not self.db_path:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT c.id, c.nombre
                FROM transacciones t
                JOIN categorias c ON t.categoria_id = c.id
                WHERE t.proyecto_id = 8
                ORDER BY c.nombre
            """)
            categorias = cur.fetchall()
            for row in categorias:
                self.categoria_combo.addItem(f"{row['nombre']} (ID: {row['id']})", row['id'])
            conn.close()
            # Cargar datos iniciales para la primera categoría
            if self.categoria_combo.count() > 0:
                self.cargar_datos()
        except Exception as e:
            QMessageBox.critical(self, "Error al cargar categorías", f"Ocurrió un error:\n{e}")

    def cargar_datos(self):
        """Carga subcategorías y equipos según la categoría seleccionada."""
        self.subcat_list.clear()
        self.equipos_combo.clear()
        if not self.db_path or self.categoria_combo.count() == 0:
            return

        categoria_id = self.categoria_combo.currentData()
        if categoria_id is None:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Subcategorías asociadas al proyecto 8 y la categoría seleccionada (usadas en transacciones)
            cur.execute("""
                SELECT DISTINCT s.id, s.nombre
                FROM transacciones t
                JOIN subcategorias s ON t.subcategoria_id = s.id
                WHERE t.proyecto_id = 8 AND t.categoria_id = ?
                ORDER BY s.nombre
            """, (categoria_id,))
            subcats = cur.fetchall()
            for row in subcats:
                item_text = f"ID: {row['id']}  |  Nombre actual: {row['nombre']}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, (row['id'], row['nombre']))
                self.subcat_list.addItem(item)

            # Equipos activos del proyecto 8 desde la tabla 'equipos'
            cur.execute("""
                SELECT DISTINCT nombre FROM equipos
                WHERE proyecto_id = 8
                ORDER BY nombre
            """)
            equipos = [r["nombre"] for r in cur.fetchall()]
            self.equipos_combo.addItems(equipos)

            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Error al cargar datos", f"Ocurrió un error:\n{e}")

    def reemplazar_subcategoria(self):
        item_sel = self.subcat_list.currentItem()
        equipo_nombre = self.equipos_combo.currentText()
        if not item_sel or not equipo_nombre:
            QMessageBox.warning(self, "Faltan datos", "Selecciona una subcategoría y un equipo.")
            return

        subcat_id, subcat_nombre = item_sel.data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(
            self, "Confirmar reemplazo",
            f"¿Reemplazar el nombre de la subcategoría:\n\n"
            f"ID: {subcat_id}\nNombre actual: {subcat_nombre}\n\n"
            f"por el nombre del equipo:\n{equipo_nombre} ?\n\n"
            f"Esto afectará TODAS las transacciones y referencias a esta subcategoría.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                "UPDATE subcategorias SET nombre = ? WHERE id = ?",
                (equipo_nombre, subcat_id)
            )
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Éxito", "¡Nombre de subcategoría actualizado correctamente!")
            self.cargar_datos()
        except Exception as e:
            QMessageBox.critical(self, "Error al actualizar", f"Ocurrió un error al actualizar:\n{e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CorrectorSubcategoriasApp()
    window.show()
    sys.exit(app.exec())