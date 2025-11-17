from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)

class VentanaGestionEquipos(QDialog):
    def __init__(self, db, proyecto_actual, parent=None):
        super().__init__(parent)
        self.db = db
        self.proyecto_actual = proyecto_actual
        self.setWindowTitle("Gestión de Equipos")
        self.resize(700, 420)

        layout = QVBoxLayout(self)

        # Tabla/listado - agregamos columna ID oculta
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Nombre", "Matrícula/Placa", "Ficha", "Estado", "ID"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setColumnHidden(4, True)  # Oculta columna ID
        layout.addWidget(self.table)

        # Botones
        btns = QHBoxLayout()
        btn_agregar = QPushButton("Agregar")
        btn_editar = QPushButton("Editar")
        btn_eliminar = QPushButton("Eliminar")
        btns.addWidget(btn_agregar)
        btns.addWidget(btn_editar)
        btns.addWidget(btn_eliminar)
        layout.addLayout(btns)

        # Conexiones
        btn_agregar.clicked.connect(self.agregar)
        btn_editar.clicked.connect(self.editar)
        btn_eliminar.clicked.connect(self.eliminar)

        self.refrescar()

    def refrescar(self):
        self.table.setRowCount(0)
        # Siempre filtra por proyecto_actual['id']
        equipos = self.db.obtener_entidades_por_tipo(self.proyecto_actual['id'])
        for e in equipos:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(e['nombre'])))
            self.table.setItem(row, 1, QTableWidgetItem(str(e.get('placa', ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(e.get('ficha', ""))))
            estado = "Activo" if e.get('activo', 1) else "Inactivo"
            self.table.setItem(row, 3, QTableWidgetItem(estado))
            self.table.setItem(row, 4, QTableWidgetItem(str(e['id'])))  # columna ID oculta

    def agregar(self):
        dlg = DialogoEquipoEntidad(self.db, self.proyecto_actual, parent=self)
        if dlg.exec():
            self.refrescar()

    def editar(self):
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un equipo para editar.")
            return
        equipo_id = self.table.item(selected, 4).text()
        equipos = self.db.obtener_entidades_por_tipo(self.proyecto_actual['id'])
        equipo = next((e for e in equipos if str(e['id']) == equipo_id), None)
        if not equipo:
            QMessageBox.warning(self, "Error", "No se encontró el equipo.")
            return
        dlg = DialogoEquipoEntidad(self.db, self.proyecto_actual, equipo, parent=self)
        if dlg.exec():
            self.refrescar()

    def eliminar(self):
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un equipo para eliminar.")
            return
        equipo_id = self.table.item(selected, 4).text()
        equipos = self.db.obtener_entidades_por_tipo(self.proyecto_actual['id'])
        equipo = next((e for e in equipos if str(e['id']) == equipo_id), None)
        if not equipo:
            QMessageBox.warning(self, "Error", "No se encontró el equipo.")
            return
        confirm = QMessageBox.question(self, "Confirmar", f"¿Eliminar a '{equipo['nombre']}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            exito = self.db.eliminar_entidad_equipo(equipo['id'])
            if exito:
                QMessageBox.information(self, "Éxito", "Equipo eliminado correctamente.")
                self.refrescar()
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el equipo. Puede estar en uso.")

class DialogoEquipoEntidad(QDialog):
    def __init__(self, db, proyecto_actual, datos=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.proyecto_actual = proyecto_actual
        self.datos = datos
        self.setWindowTitle("Editar Equipo" if datos else "Nuevo Equipo")
        layout = QVBoxLayout(self)

        self.edit_nombre = QLineEdit(datos['nombre'] if datos and 'nombre' in datos else "")
        self.edit_placa = QLineEdit(datos['placa'] if datos and 'placa' in datos else "")
        self.edit_ficha = QLineEdit(datos['ficha'] if datos and 'ficha' in datos else "")
        self.combo_estado = QComboBox()
        self.combo_estado.addItems(["Activo", "Inactivo"])
        if datos and 'activo' in datos and not datos.get("activo", 1):
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

        btn_guardar.clicked.connect(self.guardar)
        btn_cancelar.clicked.connect(self.reject)

    def guardar(self):
        nombre = self.edit_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
            return
        datos = {
            "proyecto_id": self.proyecto_actual['id'],
            "tipo": "Equipo",
            "nombre": nombre,
            "placa": self.edit_placa.text().strip(),
            "ficha": self.edit_ficha.text().strip(),
            "activo": 1 if self.combo_estado.currentText() == "Activo" else 0
        }
        equipo_id = self.datos['id'] if self.datos and 'id' in self.datos else None
        resultado = self.db.guardar_entidad(datos, equipo_id)
        if resultado:
            QMessageBox.information(self, "Éxito", "Equipo guardado correctamente.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "No se pudo guardar el equipo. ¿Nombre duplicado?")