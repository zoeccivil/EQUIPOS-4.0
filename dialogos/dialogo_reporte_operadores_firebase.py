from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit, QPushButton
)
from PyQt6.QtCore import QDate

from firebase_manager import FirebaseManager


class DialogoReporteOperadoresFirebase(QDialog):
    """
    Diálogo de filtros para Reporte de Operadores (versión Firebase).

    Filtros:
      - Operador (Todos / uno)
      - Equipo (Todos / uno)
      - Rango de fechas (desde primera transacción global u operador hasta hoy)
    """

    def __init__(
        self,
        fm: FirebaseManager,
        operadores_mapa: dict,
        equipos_mapa: dict,
        proyecto_id=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Reporte de Operadores - Filtros")
        self.fm = fm
        self.proyecto_id = proyecto_id
        self.formato = None

        self.operadores_mapa = operadores_mapa or {}  # {id_str: nombre}
        self.equipos_mapa = equipos_mapa or {}        # {id_str: nombre}

        layout = QVBoxLayout(self)

        # Operador selector
        hlayout_op = QHBoxLayout()
        hlayout_op.addWidget(QLabel("Operador:"))
        self.combo_operador = QComboBox()
        self.combo_operador.addItem("Todos", None)
        for oid, nom in sorted(self.operadores_mapa.items(), key=lambda x: x[1]):
            self.combo_operador.addItem(nom, str(oid))
        hlayout_op.addWidget(self.combo_operador)
        layout.addLayout(hlayout_op)

        # Equipo selector
        hlayout_eq = QHBoxLayout()
        hlayout_eq.addWidget(QLabel("Equipo:"))
        self.combo_equipo = QComboBox()
        self.combo_equipo.addItem("Todos", None)
        for eid, nom in sorted(self.equipos_mapa.items(), key=lambda x: x[1]):
            self.combo_equipo.addItem(nom, str(eid))
        hlayout_eq.addWidget(self.combo_equipo)
        layout.addLayout(hlayout_eq)

        # Fechas
        hlayout_fechas = QHBoxLayout()
        hlayout_fechas.addWidget(QLabel("Desde:"))
        self.fecha_inicio = QDateEdit(calendarPopup=True)
        self.fecha_inicio.setDisplayFormat("yyyy-MM-dd")
        hlayout_fechas.addWidget(self.fecha_inicio)
        hlayout_fechas.addWidget(QLabel("Hasta:"))
        self.fecha_fin = QDateEdit(calendarPopup=True)
        self.fecha_fin.setDisplayFormat("yyyy-MM-dd")
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

        # Enlaces y lógica
        self.combo_operador.currentIndexChanged.connect(self.actualizar_rango_fechas)

        # Llamada inicial
        self.actualizar_rango_fechas()

    # ------------------------------------------------------------------ Lógica

    def get_filtros(self) -> dict:
        op_idx = self.combo_operador.currentIndex()
        eq_idx = self.combo_equipo.currentIndex()

        operador_id = self.combo_operador.itemData(op_idx)
        equipo_id = self.combo_equipo.itemData(eq_idx)

        return {
            "operador_id": str(operador_id) if operador_id else None,
            "equipo_id": str(equipo_id) if equipo_id else None,
            "fecha_inicio": self.fecha_inicio.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.fecha_fin.date().toString("yyyy-MM-dd"),
        }

    def exportar_pdf(self):
        self.formato = "pdf"
        self.accept()

    def exportar_excel(self):
        self.formato = "excel"
        self.accept()

    def actualizar_rango_fechas(self):
        """
        Usa FirebaseManager para obtener la primera fecha de transacciones:
          - Global si operador=None
          - Por operador si operador_id != None

        Debes implementar en FirebaseManager:
          - obtener_fecha_primera_transaccion()
          - obtener_fecha_primera_transaccion_operador(operador_id)
        """
        operador_id = self.combo_operador.currentData()
        try:
            if operador_id:
                fecha_inicio_str = self.fm.obtener_fecha_primera_transaccion_operador(str(operador_id))
            else:
                fecha_inicio_str = self.fm.obtener_fecha_primera_transaccion()
        except Exception:
            fecha_inicio_str = None

        if fecha_inicio_str:
            qd = QDate.fromString(fecha_inicio_str, "yyyy-MM-dd")
            if qd.isValid():
                self.fecha_inicio.setDate(qd)
            else:
                self.fecha_inicio.setDate(QDate.currentDate())
        else:
            self.fecha_inicio.setDate(QDate.currentDate())

        self.fecha_fin.setDate(QDate.currentDate())