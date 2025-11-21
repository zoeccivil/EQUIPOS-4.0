from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDateEdit, QPushButton
)
from PyQt6.QtCore import QDate

from firebase_manager import FirebaseManager


class DialogoReporteRendimientosFirebase(QDialog):
    """
    Filtros para el Reporte de Rendimientos:

      - Equipo: Todos / uno.
      - Rango de fechas.
    """

    def __init__(self, fm: FirebaseManager, equipos_mapa: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reporte de Rendimientos - Filtros")
        self.fm = fm
        self.equipos_mapa = equipos_mapa or {}
        self.formato = "pdf"

        layout = QVBoxLayout(self)

        # Equipo
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

        # Inicializar fechas
        self._init_fechas()

    def _init_fechas(self):
        """
        Rango inicial: desde la primera transacción global hasta hoy.
        Usa FirebaseManager.obtener_fecha_primera_transaccion().
        """
        try:
            fecha_str = self.fm.obtener_fecha_primera_transaccion()
        except Exception:
            fecha_str = None

        if fecha_str:
            qd = QDate.fromString(fecha_str, "yyyy-MM-dd")
            if qd.isValid():
                self.fecha_inicio.setDate(qd)
            else:
                self.fecha_inicio.setDate(QDate.currentDate())
        else:
            self.fecha_inicio.setDate(QDate.currentDate())

        self.fecha_fin.setDate(QDate.currentDate())

    def get_filtros(self) -> dict:
        equipo_id = self.combo_equipo.currentData()
        if equipo_id is not None:
            equipo_id = str(equipo_id)

        return {
            "equipo_id": equipo_id,
            "fecha_inicio": self.fecha_inicio.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.fecha_fin.date().toString("yyyy-MM-dd"),
        }

    def exportar_pdf(self):
        self.formato = "pdf"
        self.accept()

    def exportar_excel(self):
        self.formato = "excel"
        self.accept()