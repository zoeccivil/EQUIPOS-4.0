from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit, QPushButton
)
from PyQt6.QtCore import QDate
from typing import Dict, Any


class EstadoCuentaDialog(QDialog):
    """
    Diálogo para seleccionar cliente y rango de fechas para generar estado de cuenta (versión Firebase).
    """
    def __init__(self, firebase_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generar Estado de Cuenta")
        self.setMinimumWidth(420)
        self.firebase_manager = firebase_manager

        layout = QVBoxLayout(self)

        # --- Cliente ---
        cliente_layout = QHBoxLayout()
        cliente_layout.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        self.clientes_mapa = {}

        self.combo_cliente.addItem("Todos", None)  # data None para "Todos"
        try:
            clientes = self.firebase_manager.obtener_entidades(tipo="Cliente", activo=True)
        except Exception:
            clientes = []

        for cli in clientes:
            cid = cli.get("id")
            nombre = cli.get("nombre", f"ID:{cid}")
            self.combo_cliente.addItem(nombre, cid)
            self.clientes_mapa[nombre] = cid

        cliente_layout.addWidget(self.combo_cliente)
        layout.addLayout(cliente_layout)

        # --- Fechas ---
        fechas_layout = QHBoxLayout()
        fechas_layout.addWidget(QLabel("Desde:"))
        self.fecha_inicio = QDateEdit(calendarPopup=True)
        fechas_layout.addWidget(self.fecha_inicio)
        fechas_layout.addWidget(QLabel("Hasta:"))
        self.fecha_fin = QDateEdit(calendarPopup=True)
        fechas_layout.addWidget(self.fecha_fin)
        layout.addLayout(fechas_layout)

        # --- Botones ---
        btn_layout = QHBoxLayout()
        btn_aceptar = QPushButton("Generar Reporte")
        btn_aceptar.clicked.connect(self.accept)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_aceptar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)

        # --- Conexión y llamada inicial a la lógica de fechas ---
        self.combo_cliente.currentIndexChanged.connect(self.actualizar_rango_fechas)
        self.actualizar_rango_fechas()

    def actualizar_rango_fechas(self):
        cliente_id = self.combo_cliente.currentData()

        if not cliente_id:
            # "Todos" seleccionado -> no tenemos método global en FirebaseManager,
            # así que usamos la fecha actual como inicio.
            fecha_str = None
        else:
            fecha_str = self.firebase_manager.obtener_fecha_primera_transaccion_cliente(cliente_id)

        if fecha_str:
            self.fecha_inicio.setDate(QDate.fromString(fecha_str, "yyyy-MM-dd"))
        else:
            self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))  # último mes por defecto

        self.fecha_fin.setDate(QDate.currentDate())

    def get_filtros(self) -> Dict[str, Any]:
        cliente_nombre = self.combo_cliente.currentText()
        cliente_id = self.combo_cliente.currentData()
        # None significa "Todos"
        return {
            "cliente_nombre": cliente_nombre,
            "cliente_id": cliente_id,
            "fecha_inicio": self.fecha_inicio.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.fecha_fin.date().toString("yyyy-MM-dd"),
        }