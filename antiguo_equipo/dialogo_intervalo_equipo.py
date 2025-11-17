from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QMessageBox
)

class DialogoIntervaloEquipo(QDialog):
    """
    Diálogo para configurar el intervalo de servicio de cualquier equipo del proyecto.
    Selecciona equipo, tipo de intervalo y valor. Guarda y refresca la tabla principal.
    """
    def __init__(self, db, proyecto_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.proyecto_id = proyecto_id
        self.setWindowTitle("Configurar Intervalo de Servicio de Equipo")
        layout = QVBoxLayout(self)

        # Leer los equipos del proyecto
        self.equipos = self.db.obtener_equipos(self.proyecto_id)
        self.combo_equipo = QComboBox()
        self.equipos_map = {}
        for eq in self.equipos:
            self.combo_equipo.addItem(eq['nombre'])
            self.equipos_map[eq['nombre']] = eq['id']
        layout.addWidget(QLabel("Equipo:"))
        layout.addWidget(self.combo_equipo)

        # Tipo y valor de intervalo
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["HORAS", "KM", "DIAS"])
        self.edit_valor = QLineEdit("")

        layout.addWidget(QLabel("Tipo de intervalo (HORAS/KM/DIAS):"))
        layout.addWidget(self.combo_tipo)
        layout.addWidget(QLabel("Valor del intervalo:"))
        layout.addWidget(self.edit_valor)

        # Al cambiar equipo, cargar su intervalo actual
        self.combo_equipo.currentIndexChanged.connect(self.cargar_datos_equipo)
        self.cargar_datos_equipo()  # Inicializa con el primer equipo

        btns = QHBoxLayout()
        btn_guardar = QPushButton("Guardar")
        btn_cancelar = QPushButton("Cancelar")
        btns.addWidget(btn_guardar)
        btns.addWidget(btn_cancelar)
        layout.addLayout(btns)

        btn_guardar.clicked.connect(self.guardar)
        btn_cancelar.clicked.connect(self.reject)

    def cargar_datos_equipo(self):
        nombre = self.combo_equipo.currentText()
        if not nombre:
            return
        equipo_id = self.equipos_map[nombre]
        equipo = self.db.obtener_equipo_por_id(equipo_id)
        tipo = (equipo.get("mantenimiento_trigger_tipo") or "HORAS").upper()
        valor = str(equipo.get("mantenimiento_trigger_valor") or "")
        idx = self.combo_tipo.findText(tipo)
        if idx >= 0:
            self.combo_tipo.setCurrentIndex(idx)
        self.edit_valor.setText(valor)

    def guardar(self):
        nombre = self.combo_equipo.currentText()
        equipo_id = self.equipos_map.get(nombre)
        tipo = self.combo_tipo.currentText()
        valor = self.edit_valor.text()
        try:
            valorf = float(valor.replace(",", ".")) if valor.strip() else None
        except Exception:
            QMessageBox.warning(self, "Error", "El valor debe ser numérico.")
            return

        self.db.actualizar_intervalo_equipo(equipo_id, tipo, valorf)
        QMessageBox.information(self, "Éxito", f"Intervalo actualizado para '{nombre}'.")
        self.accept()