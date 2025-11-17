# Reemplaza todo el archivo estado_cuenta_dialog.py con esto

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit, QPushButton
)
from PyQt6.QtCore import QDate

class EstadoCuentaDialog(QDialog):
    def __init__(self, db, proyecto_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generar Estado de Cuenta")
        self.setMinimumWidth(420)
        self.db = db
        self.proyecto_actual = proyecto_actual

        layout = QVBoxLayout(self)

        # --- Cliente ---
        cliente_layout = QHBoxLayout()
        cliente_layout.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        self.clientes_mapa = {}
        
        self.combo_cliente.addItem("Todos", -1) # Usar -1 o None como data para "Todos"
        clientes = self.db.obtener_clientes_por_proyecto(self.proyecto_actual['id'])
        for cli in clientes:
            if 'activo' not in cli or cli['activo']:
                self.combo_cliente.addItem(cli['nombre'], cli['id'])
                self.clientes_mapa[cli['nombre']] = cli['id']
                
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

        if cliente_id is None or cliente_id == -1: # "Todos" seleccionado
            fecha_str = self.db.obtener_fecha_primera_transaccion(self.proyecto_actual['id'])
        else:
            fecha_str = self.db.obtener_fecha_primera_transaccion_cliente(self.proyecto_actual['id'], cliente_id)
        
        if fecha_str:
            self.fecha_inicio.setDate(QDate.fromString(fecha_str, "yyyy-MM-dd"))
        else:
            self.fecha_inicio.setDate(QDate.currentDate())
        
        self.fecha_fin.setDate(QDate.currentDate())

    def get_filtros(self):
        cliente_nombre = self.combo_cliente.currentText()
        cliente_id = self.combo_cliente.currentData()
        if cliente_id == -1:
            cliente_id = None
        
        return {
            'cliente_nombre': cliente_nombre,
            'cliente_id': cliente_id,
            'fecha_inicio': self.fecha_inicio.date().toString("yyyy-MM-dd"),
            'fecha_fin': self.fecha_fin.date().toString("yyyy-MM-dd")
        }