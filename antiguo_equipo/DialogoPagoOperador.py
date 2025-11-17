import uuid
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QTextEdit,
    QDateEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import QDate

class DialogoPagoOperador(QDialog):
    def __init__(self, db_manager, proyecto_id, parent=None, pago=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Pago a Operador" if pago else "Registrar Pago a Operador")
        self.setFixedSize(420, 480)
        self.db = db_manager
        self.proyecto_id = proyecto_id
        self.pago = pago

        layout = QVBoxLayout(self)

        # Cuenta
        layout.addWidget(QLabel("Cuenta:"))
        self.cuenta_cb = QComboBox()
        for c in self.db.obtener_cuentas_por_proyecto(self.proyecto_id):
            self.cuenta_cb.addItem(c["nombre"], c["id"])
        layout.addWidget(self.cuenta_cb)

        # Operador
        layout.addWidget(QLabel("Operador:"))
        self.operador_cb = QComboBox()
        self._operadores = self.db.obtener_operadores_por_proyecto(self.proyecto_id)
        for o in self._operadores:
            self.operador_cb.addItem(o["nombre"], o["id"])
        layout.addWidget(self.operador_cb)

        # Equipo
        layout.addWidget(QLabel("Equipo:"))
        self.equipo_cb = QComboBox()
        self._equipos = self.db.obtener_equipos_por_proyecto(self.proyecto_id)
        for eq in self._equipos:
            self.equipo_cb.addItem(eq["nombre"], eq["id"])
        layout.addWidget(self.equipo_cb)

        # Horas
        layout.addWidget(QLabel("Horas:"))
        self.horas_edit = QLineEdit()
        layout.addWidget(self.horas_edit)

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

        # Descripción
        layout.addWidget(QLabel("Descripción:"))
        self.descripcion_edit = QLineEdit()
        layout.addWidget(self.descripcion_edit)

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
        if pago:
            idx_cuenta = self.cuenta_cb.findText(str(pago.get("cuenta", "")))
            if idx_cuenta >= 0:
                self.cuenta_cb.setCurrentIndex(idx_cuenta)

            idx_operador = self.operador_cb.findText(str(pago.get("operador", "")))
            if idx_operador >= 0:
                self.operador_cb.setCurrentIndex(idx_operador)

            idx_equipo = self.equipo_cb.findText(str(pago.get("equipo", "")))
            if idx_equipo >= 0:
                self.equipo_cb.setCurrentIndex(idx_equipo)

            self.horas_edit.setText(str(pago.get("horas", "")))
            self.monto_edit.setText(str(pago.get("monto", "")))
            if pago.get("fecha"):
                year, month, day = map(int, str(pago["fecha"]).split("-"))
                self.fecha_edit.setDate(QDate(year, month, day))
            self.descripcion_edit.setText(str(pago.get("descripcion", "")))
            self.comentario_edit.setText(str(pago.get("comentario", "")))
        else:
            # Prellenado automático para nuevo pago
            self.operador_cb.currentIndexChanged.connect(self._autocompletar_textos)
            self.equipo_cb.currentIndexChanged.connect(self._autocompletar_textos)
            self.horas_edit.textChanged.connect(self._autocompletar_textos)
            self._autocompletar_textos()

    def _autocompletar_textos(self):
        operador = self.operador_cb.currentText()
        equipo = self.equipo_cb.currentText()
        horas = self.horas_edit.text()
        cliente = self.db.obtener_cliente_equipo(self.proyecto_id, self.equipo_cb.currentData()) or ""
        ubicacion = self.db.obtener_ubicacion_equipo(self.proyecto_id, self.equipo_cb.currentData()) or ""
        desc = f"Pago {horas} Horas Operador {operador}"
        comm = f"Pago {horas} Horas, Operador {operador}, Cliente {cliente}, Ubicacion {ubicacion}"
        self.descripcion_edit.setText(desc)
        self.comentario_edit.setText(comm)

    def guardar(self):
        cuenta_id = self.cuenta_cb.currentData()
        operador_id = self.operador_cb.currentData()
        equipo_id = self.equipo_cb.currentData()
        categoria_id = self.db.obtener_o_crear_id('categorias', "PAGO HRS OPERADOR")
        subcategoria_nombre = self.equipo_cb.currentText()
        subcategoria_id = self.db.obtener_o_crear_id('subcategorias', subcategoria_nombre, 'categoria_id', categoria_id)
        descripcion = self.descripcion_edit.text().strip()
        comentario = self.comentario_edit.toPlainText().strip()
        try:
            horas = float(self.horas_edit.text().replace(",", "."))
        except Exception:
            QMessageBox.warning(self, "Error", "Las horas deben ser un número.")
            return
        try:
            monto = float(self.monto_edit.text().replace(",", "").replace(" ", ""))
        except Exception:
            QMessageBox.warning(self, "Error", "El monto debe ser un número.")
            return
        fecha = self.fecha_edit.date().toPyDate()

        datos = {
            'proyecto_id': self.proyecto_id,
            'cuenta_id': cuenta_id,
            'categoria_id': categoria_id,
            'subcategoria_id': subcategoria_id,
            'equipo_id': equipo_id,
            'operador_id': operador_id,
            'tipo': "Gasto",
            'descripcion': descripcion,
            'comentario': comentario,
            'monto': monto,
            'fecha': fecha,
            'horas': horas
        }
        if self.pago and "id" in self.pago:
            datos['id'] = self.pago['id']
            exito = self.db.editar_pago_operador(datos)
        else:
            datos['id'] = uuid.uuid4().hex
            exito = self.db.guardar_pago_operador(datos)
        if exito:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "No se pudo guardar el pago.")