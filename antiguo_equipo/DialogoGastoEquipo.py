import uuid
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QTextEdit,
    QDateEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import QDate

class DialogoGastoEquipo(QDialog):
    def __init__(self, db_manager, proyecto_id, parent=None, gasto=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Gasto de Equipo" if gasto else "Registrar Gasto de Equipo")
        self.setFixedSize(420, 450)
        self.db = db_manager
        self.proyecto_id = proyecto_id
        self.gasto = gasto

        layout = QVBoxLayout(self)

        # Cuenta
        layout.addWidget(QLabel("Cuenta:"))
        self.cuenta_cb = QComboBox()
        self._cuentas = self.db.obtener_cuentas_por_proyecto(self.proyecto_id)
        for c in self._cuentas:
            self.cuenta_cb.addItem(c["nombre"], c["id"])
        layout.addWidget(self.cuenta_cb)

        # Categoría
        layout.addWidget(QLabel("Categoría:"))
        self.categoria_cb = QComboBox()
        self._categorias = self.db.obtener_categorias_por_proyecto(self.proyecto_id, tipo="Gasto")
        for cat in self._categorias:
            self.categoria_cb.addItem(cat["nombre"], cat["id"])
        layout.addWidget(self.categoria_cb)

        # Subcategoría
        layout.addWidget(QLabel("Subcategoría:"))
        self.subcategoria_cb = QComboBox()
        self._cargar_subcategorias()
        layout.addWidget(self.subcategoria_cb)
        self.categoria_cb.currentIndexChanged.connect(self._cargar_subcategorias)

        # Equipo
        layout.addWidget(QLabel("Equipo (opcional):"))
        self.equipo_cb = QComboBox()
        self.equipo_cb.addItem("Ninguno", None)
        self._equipos = self.db.obtener_equipos_por_proyecto(self.proyecto_id)
        for eq in self._equipos:
            self.equipo_cb.addItem(eq["nombre"], eq["id"])
        layout.addWidget(self.equipo_cb)

        # Descripción
        layout.addWidget(QLabel("Descripción:"))
        self.descripcion_edit = QLineEdit()
        layout.addWidget(self.descripcion_edit)

        # Monto
        layout.addWidget(QLabel("Monto:"))
        self.monto_edit = QLineEdit()
        layout.addWidget(self.monto_edit)

        # Fecha
        layout.addWidget(QLabel("Fecha:"))
        self.fecha_edit = QDateEdit()
        self.fecha_edit.setCalendarPopup(True)
        self.fecha_edit.setDate(QDate.currentDate())
        layout.addWidget(self.fecha_edit)

        # Comentario
        layout.addWidget(QLabel("Comentario:"))
        self.comentario_edit = QTextEdit()
        layout.addWidget(self.comentario_edit)

        # Botones
        btns = QHBoxLayout()
        btn_guardar = QPushButton("Guardar")
        btn_guardar.clicked.connect(self.guardar)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btns.addWidget(btn_guardar)
        btns.addWidget(btn_cancelar)
        layout.addLayout(btns)

        # Precarga si se edita
        if gasto:
            # Cuenta
            idx_cuenta = self.cuenta_cb.findText(str(gasto.get("cuenta", "")))
            if idx_cuenta >= 0:
                self.cuenta_cb.setCurrentIndex(idx_cuenta)
            # Categoría
            idx_cat = self.categoria_cb.findText(str(gasto.get("categoria", "")))
            if idx_cat >= 0:
                self.categoria_cb.setCurrentIndex(idx_cat)
            self._cargar_subcategorias()  # asegúrate que el combo esté actualizado
            # Subcategoría
            idx_subcat = self.subcategoria_cb.findText(str(gasto.get("subcategoria", "")))
            if idx_subcat >= 0:
                self.subcategoria_cb.setCurrentIndex(idx_subcat)
            # Equipo
            idx_equipo = self.equipo_cb.findText(str(gasto.get("equipo", "")))
            if idx_equipo >= 0:
                self.equipo_cb.setCurrentIndex(idx_equipo)
            # Descripción
            self.descripcion_edit.setText(str(gasto.get("descripcion", "")))
            # Monto
            self.monto_edit.setText(str(gasto.get("monto", "")))
            # Fecha
            if gasto.get("fecha"):
                if isinstance(gasto["fecha"], str):
                    # formato YYYY-MM-DD
                    year, month, day = map(int, gasto["fecha"].split("-"))
                    self.fecha_edit.setDate(QDate(year, month, day))
                elif isinstance(gasto["fecha"], QDate):
                    self.fecha_edit.setDate(gasto["fecha"])
            # Comentario
            self.comentario_edit.setText(str(gasto.get("comentario", "")))

    def _cargar_subcategorias(self):
        self.subcategoria_cb.clear()
        cat_id = self.categoria_cb.currentData()
        subs = self.db.obtener_subcategorias_por_categoria(cat_id)
        if not subs:
            self.subcategoria_cb.addItem("N/A", None)
        else:
            for s in subs:
                self.subcategoria_cb.addItem(s["nombre"], s["id"])

    def guardar(self):
        cuenta_id = self.cuenta_cb.currentData()
        categoria_id = self.categoria_cb.currentData()
        subcategoria_id = self.subcategoria_cb.currentData()
        equipo_id = self.equipo_cb.currentData()
        descripcion = self.descripcion_edit.text().strip()
        try:
            monto = float(self.monto_edit.text().replace(",", "").replace(" ", ""))
        except Exception:
            QMessageBox.warning(self, "Error", "El monto debe ser un número.")
            return
        fecha = self.fecha_edit.date().toPyDate()
        comentario = self.comentario_edit.toPlainText().strip()

        # Si la subcategoría no existe y no es "N/A", la crea automáticamente
        if subcategoria_id is None and self.subcategoria_cb.currentText() != "N/A":
            subcategoria_id = self.db.crear_subcategoria(self.subcategoria_cb.currentText(), categoria_id)

        datos = {
            'proyecto_id': self.proyecto_id,
            'cuenta_id': cuenta_id,
            'categoria_id': categoria_id,
            'subcategoria_id': subcategoria_id,
            'equipo_id': equipo_id,
            'tipo': "Gasto",
            'descripcion': descripcion,
            'comentario': comentario,
            'monto': monto,
            'fecha': fecha
        }
        if self.gasto and "id" in self.gasto:
            datos['id'] = self.gasto['id']
            exito = self.db.editar_gasto_equipo(datos)
        else:
            datos['id'] = uuid.uuid4().hex
            exito = self.db.guardar_gasto_equipo(datos)
        if exito:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "No se pudo guardar el gasto.")