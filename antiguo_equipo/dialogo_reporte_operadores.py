from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit, QPushButton
)
from PyQt6.QtCore import QDate

class DialogoReporteOperadores(QDialog):
    def __init__(self, db, proyecto, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reporte de Operadores - Filtros")
        self.db = db
        self.proyecto = proyecto
        self.formato = None

        layout = QVBoxLayout(self)

        # Operador selector
        hlayout_op = QHBoxLayout()
        hlayout_op.addWidget(QLabel("Operador:"))
        self.combo_operador = QComboBox()
        self.combo_operador.addItem("Todos", None)
        for op in self.db.obtener_operadores_por_proyecto(self.proyecto['id']):
            self.combo_operador.addItem(op['nombre'], op['id'])
        hlayout_op.addWidget(self.combo_operador)
        layout.addLayout(hlayout_op)

        # Equipo selector
        hlayout_eq = QHBoxLayout()
        hlayout_eq.addWidget(QLabel("Equipo:"))
        self.combo_equipo = QComboBox()
        self.combo_equipo.addItem("Todos", None)
        
        # --- LÍNEA CORREGIDA (Carga Inicial) ---
        # Usamos la función correcta para obtener la lista global de equipos
        for eq in self.db.obtener_todos_los_equipos():
            self.combo_equipo.addItem(eq['nombre'], eq['id'])
            
        hlayout_eq.addWidget(self.combo_equipo)
        layout.addLayout(hlayout_eq)

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

        # ---- Enlaces y lógica de filtrado dinámica ----
        self.combo_operador.currentIndexChanged.connect(self.actualizar_combo_equipos)
        self.combo_operador.currentIndexChanged.connect(self.actualizar_rango_fechas)
        self.actualizar_rango_fechas() # Llamada inicial

    def get_filtros(self):
        op_idx = self.combo_operador.currentIndex()
        equipo_idx = self.combo_equipo.currentIndex()
        return {
            "operador_id": self.combo_operador.itemData(op_idx) if op_idx != 0 else None,
            "equipo_id": self.combo_equipo.itemData(equipo_idx) if equipo_idx != 0 else None,
            "fecha_inicio": self.fecha_inicio.date().toPyDate(),
            "fecha_fin": self.fecha_fin.date().toPyDate(),
        }

    def exportar_pdf(self):
        self.formato = "pdf"
        self.accept()

    def exportar_excel(self):
        self.formato = "excel"
        self.accept()

    def actualizar_combo_equipos(self):
        self.combo_equipo.blockSignals(True)
        self.combo_equipo.clear()
        self.combo_equipo.addItem("Todos", None)
        
        # --- LÍNEA CORREGIDA (Actualización) ---
        # Usamos la función correcta para obtener la lista global de equipos
        for eq in self.db.obtener_todos_los_equipos():
            self.combo_equipo.addItem(eq['nombre'], eq['id'])
            
        self.combo_equipo.blockSignals(False)

    def actualizar_rango_fechas(self):
        operador_idx = self.combo_operador.currentIndex()
        operador_id = self.combo_operador.itemData(operador_idx)

        if operador_id is None:
            fecha_inicio_str = self.db.obtener_fecha_primera_transaccion(self.proyecto['id'])
        else:
            fecha_inicio_str = self.db.obtener_fecha_primera_transaccion_operador(self.proyecto['id'], operador_id)

        if fecha_inicio_str:
            self.fecha_inicio.setDate(QDate.fromString(fecha_inicio_str, "yyyy-MM-dd"))
        else:
            self.fecha_inicio.setDate(QDate.currentDate())
        
        # --- LÍNEA AÑADIDA ---
        # La fecha final es siempre la de hoy
        self.fecha_fin.setDate(QDate.currentDate())