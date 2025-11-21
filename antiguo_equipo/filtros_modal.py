from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit, QPushButton, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import QDate

class FiltrosReporteDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Filtros de Reporte")
        self.setMinimumWidth(450)
        self.db = db
        self.selected_filters = {}

        layout = QVBoxLayout(self)

        # Cliente
        cliente_layout = QHBoxLayout()
        cliente_layout.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        self.combo_cliente.addItem("Todos")
        self.clientes_mapa = {}
        try:
            clientes = self.db.obtener_clientes_unicos_meta()
            self.clientes_mapa = {c['nombre']: c['id'] for c in clientes}
            self.combo_cliente.addItems(sorted(self.clientes_mapa.keys()))
        except Exception:
            pass
        cliente_layout.addWidget(self.combo_cliente)
        layout.addLayout(cliente_layout)

        # Fechas
        fechas_layout = QHBoxLayout()
        fechas_layout.addWidget(QLabel("Desde:"))
        self.fecha_inicio = QDateEdit()
        self.fecha_inicio.setCalendarPopup(True)
        self.fecha_inicio.setDate(QDate.currentDate())
        fechas_layout.addWidget(self.fecha_inicio)

        fechas_layout.addWidget(QLabel("Hasta:"))
        self.fecha_fin = QDateEdit()
        self.fecha_fin.setCalendarPopup(True)
        self.fecha_fin.setDate(QDate.currentDate())
        fechas_layout.addWidget(self.fecha_fin)
        layout.addLayout(fechas_layout)

        # Espaciador
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Botones
        btn_layout = QHBoxLayout()
        btn_aceptar = QPushButton("Aceptar")
        btn_aceptar.clicked.connect(self.accept)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_aceptar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)

    def get_filters(self):
        filtros = {
            'cliente': self.combo_cliente.currentText(),
            'cliente_id': self.clientes_mapa.get(self.combo_cliente.currentText()),
            'fecha_inicio': self.fecha_inicio.date().toString("yyyy-MM-dd"),
            'fecha_fin': self.fecha_fin.date().toString("yyyy-MM-dd"),
        }
        return filtros
