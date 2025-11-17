# Reemplaza todo el archivo dialogo_reporte_detallado.py con esto

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit,
    QPushButton, QMessageBox
)
from PyQt6.QtCore import QDate

class DialogoReporteDetallado(QDialog):
    def __init__(self, db, proyecto, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filtros Reporte Detallado de Equipos")
        self.db = db
        self.proyecto = proyecto
        self.formato = 'pdf'

        layout = QVBoxLayout(self)

        # Cliente
        hlayout_cliente = QHBoxLayout()
        hlayout_cliente.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        self.combo_cliente.addItem("Todos", -1) # Usar -1 o None como data para "Todos"
        self.clientes_mapa = {}
        clientes = self.db.obtener_clientes_por_proyecto(self.proyecto['id'])
        for cli in clientes:
            self.combo_cliente.addItem(cli['nombre'], cli['id'])
            self.clientes_mapa[cli['nombre']] = cli['id']
        hlayout_cliente.addWidget(self.combo_cliente)
        layout.addLayout(hlayout_cliente)

        # Fechas
        hlayout_fechas = QHBoxLayout()
        hlayout_fechas.addWidget(QLabel("Desde:"))
        self.fecha_inicio = QDateEdit(calendarPopup=True)
        hlayout_fechas.addWidget(self.fecha_inicio)
        hlayout_fechas.addWidget(QLabel("Hasta:"))
        self.fecha_fin = QDateEdit(calendarPopup=True)
        hlayout_fechas.addWidget(self.fecha_fin)
        layout.addLayout(hlayout_fechas)

        # Botones
        btns = QHBoxLayout()
        self.btn_pdf = QPushButton("Exportar PDF")
        self.btn_pdf.clicked.connect(self.exportar_pdf)
        btns.addWidget(self.btn_pdf)
        self.btn_excel = QPushButton("Exportar Excel")
        self.btn_excel.clicked.connect(self.exportar_excel)
        btns.addWidget(self.btn_excel)
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

        # Conectar señal y actualizar fechas al inicio
        self.combo_cliente.currentIndexChanged.connect(self.actualizar_rango_fechas)
        self.actualizar_rango_fechas()

    def actualizar_rango_fechas(self):
        cliente_id = self.combo_cliente.currentData()
        
        if cliente_id is None or cliente_id == -1: # "Todos" seleccionado
            fecha_str = self.db.obtener_fecha_primera_transaccion(self.proyecto['id'])
        else:
            fecha_str = self.db.obtener_fecha_primera_transaccion_cliente(self.proyecto['id'], cliente_id)
        
        if fecha_str:
            self.fecha_inicio.setDate(QDate.fromString(fecha_str, "yyyy-MM-dd"))
        else:
            self.fecha_inicio.setDate(QDate.currentDate())
        self.fecha_fin.setDate(QDate.currentDate())

    def get_filtros(self):
        """Devuelve un dict con los filtros seleccionados."""
        cliente_id = self.combo_cliente.currentData()
        if cliente_id == -1:
            cliente_id = None
            
        return {
            "cliente_id": cliente_id,
            "fecha_inicio": self.fecha_inicio.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.fecha_fin.date().toString("yyyy-MM-dd"),
        }

    def exportar_pdf(self):
        self.formato = "pdf"
        self.accept()

    def exportar_excel(self):
        self.formato = "excel"
        self.accept()