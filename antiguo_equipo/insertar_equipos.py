import sys
import sqlite3
from tkinter import Tk, filedialog
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)

# --- Selección de archivo de base de datos (filedialog) ---
root = Tk()
root.withdraw()
db_path = filedialog.askopenfilename(
    title="Selecciona tu archivo de base de datos SQLite",
    filetypes=[("SQLite DB", "*.db *.sqlite3 *.sqlite"), ("Todos los archivos", "*.*")]
)
root.destroy()
if not db_path:
    print("No seleccionaste ningún archivo. Saliendo...")
    sys.exit()

# --- Clase de acceso directo a equipos ---
class EquiposDB:
    def __init__(self, db_path, proyecto_id):
        self.db_path = db_path
        self.proyecto_id = proyecto_id
        self._crear_tabla_equipos_si_no_existe()

    def _crear_tabla_equipos_si_no_existe(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS equipos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proyecto_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                placa TEXT,
                ficha TEXT,
                activo INTEGER DEFAULT 1
            )
        """)
        conn.commit()
        conn.close()

    def listar(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, placa, ficha, activo FROM equipos WHERE proyecto_id = ?", (self.proyecto_id,))
        equipos = [
            {"id": r[0], "nombre": r[1], "placa": r[2], "ficha": r[3], "activo": r[4]}
            for r in cur.fetchall()
        ]
        conn.close()
        return equipos

    def agregar(self, datos):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO equipos (proyecto_id, nombre, placa, ficha, activo)
                VALUES (?, ?, ?, ?, ?)
            """, (self.proyecto_id, datos['nombre'], datos['placa'], datos['ficha'], datos['activo']))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def editar(self, equipo_id, datos):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE equipos
                SET nombre = ?, placa = ?, ficha = ?, activo = ?
                WHERE id = ? AND proyecto_id = ?
            """, (datos['nombre'], datos['placa'], datos['ficha'], datos['activo'], equipo_id, self.proyecto_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def eliminar(self, equipo_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM equipos WHERE id = ? AND proyecto_id = ?", (equipo_id, self.proyecto_id))
        conn.commit()
        n = cur.rowcount
        conn.close()
        return n > 0

# --- Diálogo para agregar/editar equipos ---
class DialogoEquipo(QDialog):
    def __init__(self, datos=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Equipo" if datos else "Nuevo Equipo")
        layout = QVBoxLayout(self)

        self.edit_nombre = QLineEdit(datos['nombre'] if datos else "")
        self.edit_placa = QLineEdit(datos['placa'] if datos else "")
        self.edit_ficha = QLineEdit(datos['ficha'] if datos else "")
        self.combo_estado = QComboBox()
        self.combo_estado.addItems(["Activo", "Inactivo"])
        if datos and not datos.get("activo", 1):
            self.combo_estado.setCurrentIndex(1)

        layout.addWidget(QLabel("Nombre:"))
        layout.addWidget(self.edit_nombre)
        layout.addWidget(QLabel("Matrícula/Placa:"))
        layout.addWidget(self.edit_placa)
        layout.addWidget(QLabel("Ficha:"))
        layout.addWidget(self.edit_ficha)
        layout.addWidget(QLabel("Estado:"))
        layout.addWidget(self.combo_estado)

        btns = QHBoxLayout()
        btn_guardar = QPushButton("Guardar")
        btn_cancelar = QPushButton("Cancelar")
        btns.addWidget(btn_guardar)
        btns.addWidget(btn_cancelar)
        layout.addLayout(btns)

        btn_guardar.clicked.connect(self.accept)
        btn_cancelar.clicked.connect(self.reject)

    def get_datos(self):
        return {
            "nombre": self.edit_nombre.text().strip(),
            "placa": self.edit_placa.text().strip(),
            "ficha": self.edit_ficha.text().strip(),
            "activo": 1 if self.combo_estado.currentIndex() == 0 else 0
        }

# --- Ventana principal de gestión de equipos ---
class VentanaGestionEquipos(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Gestión de Equipos")
        self.resize(700, 420)

        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Nombre", "Matrícula/Placa", "Ficha", "Estado"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btns = QHBoxLayout()
        btn_agregar = QPushButton("Agregar")
        btn_editar = QPushButton("Editar")
        btn_eliminar = QPushButton("Eliminar")
        btns.addWidget(btn_agregar)
        btns.addWidget(btn_editar)
        btns.addWidget(btn_eliminar)
        layout.addLayout(btns)

        btn_agregar.clicked.connect(self.agregar)
        btn_editar.clicked.connect(self.editar)
        btn_eliminar.clicked.connect(self.eliminar)

        self.refrescar()

    def refrescar(self):
        self.table.setRowCount(0)
        equipos = self.db.listar()
        for e in equipos:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(e['nombre'])))
            self.table.setItem(row, 1, QTableWidgetItem(str(e['placa'])))
            self.table.setItem(row, 2, QTableWidgetItem(str(e['ficha'])))
            estado = "Activo" if e['activo'] else "Inactivo"
            self.table.setItem(row, 3, QTableWidgetItem(estado))

    def agregar(self):
        dlg = DialogoEquipo(parent=self)
        if dlg.exec():
            datos = dlg.get_datos()
            if not datos['nombre']:
                QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
                return
            exito = self.db.agregar(datos)
            if exito:
                QMessageBox.information(self, "Éxito", "Equipo agregado correctamente.")
                self.refrescar()
            else:
                QMessageBox.warning(self, "Error", "No se pudo agregar el equipo. ¿Nombre duplicado?")

    def editar(self):
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un equipo para editar.")
            return
        nombre = self.table.item(selected, 0).text()
        equipos = self.db.listar()
        equipo = next((e for e in equipos if e['nombre'] == nombre), None)
        if not equipo:
            QMessageBox.warning(self, "Error", "No se encontró el equipo.")
            return
        dlg = DialogoEquipo(equipo, parent=self)
        if dlg.exec():
            datos = dlg.get_datos()
            if not datos['nombre']:
                QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
                return
            exito = self.db.editar(equipo['id'], datos)
            if exito:
                QMessageBox.information(self, "Éxito", "Equipo editado correctamente.")
                self.refrescar()
            else:
                QMessageBox.warning(self, "Error", "No se pudo editar el equipo.")

    def eliminar(self):
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un equipo para eliminar.")
            return
        nombre = self.table.item(selected, 0).text()
        equipos = self.db.listar()
        equipo = next((e for e in equipos if e['nombre'] == nombre), None)
        if not equipo:
            QMessageBox.warning(self, "Error", "No se encontró el equipo.")
            return
        confirm = QMessageBox.question(self, "Confirmar", f"¿Eliminar a '{nombre}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            exito = self.db.eliminar(equipo['id'])
            if exito:
                QMessageBox.information(self, "Éxito", "Equipo eliminado correctamente.")
                self.refrescar()
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el equipo.")

if __name__ == "__main__":
    # Cambia este valor si tu proyecto_id es otro distinto de 8
    proyecto_id = 8
    app = QApplication(sys.argv)
    db = EquiposDB(db_path, proyecto_id)
    win = VentanaGestionEquipos(db)
    win.exec()
