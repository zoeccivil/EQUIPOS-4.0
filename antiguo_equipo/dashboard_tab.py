import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from datetime import datetime

class DashboardTab(QWidget):
    """
    A widget that displays key business indicators (KPIs) interactively using PyQt6.
    """
    def __init__(self, db_manager, proyecto_actual=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.proyecto_actual = proyecto_actual

        self.meses_mapa = {
            "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
            "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
        }
        self.equipos_mapa = {}

        self._setup_ui()
        # Initial data load will be triggered by the main app after setting the project
        
    def _crear_tarjeta_kpi(self, titulo, style_sheet="color: #333;"):
        """Creates a KPI card using QGroupBox and QLabel."""
        card = QGroupBox(titulo)
        card_layout = QVBoxLayout(card)
        
        lbl_valor = QLabel("N/A")
        font = QFont("Helvetica", 22)
        font.setBold(True)
        lbl_valor.setFont(font)
        lbl_valor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_valor.setStyleSheet(style_sheet)
        
        card_layout.addWidget(lbl_valor)
        return card, lbl_valor

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- Filtros ---
        filtros_group = QGroupBox("Filtros")
        filtros_layout = QHBoxLayout(filtros_group)

        filtros_layout.addWidget(QLabel("Año:"))
        self.combo_anio = QComboBox()
        filtros_layout.addWidget(self.combo_anio)

        filtros_layout.addWidget(QLabel("Mes:"))
        self.combo_mes = QComboBox()
        self.combo_mes.addItems(self.meses_mapa.keys())
        filtros_layout.addWidget(self.combo_mes)

        filtros_layout.addWidget(QLabel("Equipo:"))
        self.combo_equipo = QComboBox()
        filtros_layout.addWidget(self.combo_equipo)
        filtros_layout.addStretch()

        # --- LÍNEA MODIFICADA 1 ---
        # Añadimos el grupo de filtros con un factor de estiramiento de 0.
        # Esto le dice que ocupe solo su espacio mínimo necesario.
        main_layout.addWidget(filtros_group, stretch=0)

        # --- KPI Cards Grid ---
        grid_layout = QGridLayout()

        # Row 1
        card_ingresos, self.lbl_ingresos = self._crear_tarjeta_kpi("Ingresos (Periodo)", "color: green;")
        grid_layout.addWidget(card_ingresos, 0, 0)

        card_gastos, self.lbl_gastos = self._crear_tarjeta_kpi("Gastos (Periodo)", "color: red;")
        grid_layout.addWidget(card_gastos, 0, 1)

        card_beneficio, self.lbl_beneficio = self._crear_tarjeta_kpi("Beneficio (Periodo)", "color: #00529B;")
        grid_layout.addWidget(card_beneficio, 0, 2)

        # Row 2
        card_pendiente, self.lbl_pendiente = self._crear_tarjeta_kpi("Saldo Pendiente Total", "color: #E67E22;")
        grid_layout.addWidget(card_pendiente, 1, 0)

        card_equipo, self.lbl_top_equipo = self._crear_tarjeta_kpi("Equipo Más Rentable (Periodo)")
        grid_layout.addWidget(card_equipo, 1, 1)

        card_operador, self.lbl_top_operador = self._crear_tarjeta_kpi("Operador con Más Horas (Periodo)")
        grid_layout.addWidget(card_operador, 1, 2)

        # --- LÍNEA MODIFICADA 2 ---
        # Añadimos el layout de la cuadrícula con un factor de estiramiento de 1.
        # Esto le dice que tome todo el espacio vertical restante.
        main_layout.addLayout(grid_layout, stretch=1)

        # --- Connections ---
        self.combo_anio.currentIndexChanged.connect(self.refrescar_datos)
        self.combo_mes.currentIndexChanged.connect(self.refrescar_datos)
        self.combo_equipo.currentIndexChanged.connect(self.refrescar_datos)

    def configurar_filtros(self):
        """Populates the filter combo boxes with data from the database."""
        if not self.proyecto_actual:
            return

        # Block signals to prevent multiple refreshes
        self.combo_anio.blockSignals(True)
        self.combo_mes.blockSignals(True)
        self.combo_equipo.blockSignals(True)

        # Populate Years
        self.combo_anio.clear()
        anios = self.db.obtener_anios_transacciones(self.proyecto_actual['id'])
        if anios:
            self.combo_anio.addItems([str(a) for a in anios])
            self.combo_anio.setCurrentText(str(datetime.now().year))
        
        # Populate Teams
        self.combo_equipo.clear()
        equipos = self.db.obtener_todos_los_equipos() or []
        self.equipos_mapa = {e['nombre']: e['id'] for e in equipos}
        self.combo_equipo.addItem("Todos", -1) # Use -1 for "All"
        self.combo_equipo.addItems(sorted(self.equipos_mapa.keys()))

        # Set current month
        nombre_mes_actual = list(self.meses_mapa.keys())[datetime.now().month - 1]
        self.combo_mes.setCurrentText(nombre_mes_actual)

        # Unblock signals and trigger a single refresh
        self.combo_anio.blockSignals(False)
        self.combo_mes.blockSignals(False)
        self.combo_equipo.blockSignals(False)
        
        self.refrescar_datos()

    def refrescar_datos(self):
        """Fetches new KPI data from the database and updates the UI."""
        if not all([self.proyecto_actual, self.combo_anio.currentText(), self.combo_mes.currentText()]):
            return

        anio = int(self.combo_anio.currentText())
        mes = self.meses_mapa[self.combo_mes.currentText()]
        
        equipo_nombre = self.combo_equipo.currentText()
        equipo_id = self.equipos_mapa.get(equipo_nombre) if equipo_nombre != "Todos" else None

        kpis = self.db.obtener_kpis_dashboard(self.proyecto_actual['id'], anio, mes, equipo_id)
        if not kpis:
            # If no data, clear the labels
            moneda = self.proyecto_actual.get('moneda', 'RD$')
            self.lbl_ingresos.setText(f"{moneda} 0.00")
            self.lbl_gastos.setText(f"{moneda} 0.00")
            self.lbl_beneficio.setText(f"{moneda} 0.00")
            self.lbl_pendiente.setText(f"{moneda} 0.00")
            self.lbl_top_equipo.setText("N/A")
            self.lbl_top_operador.setText("N/A")
            return
        
        moneda = self.proyecto_actual.get('moneda', 'RD$')
        ingresos = kpis.get('ingresos_mes', 0.0)
        gastos = kpis.get('gastos_mes', 0.0)
        beneficio = ingresos - gastos

        self.lbl_ingresos.setText(f"{moneda} {ingresos:,.2f}")
        self.lbl_gastos.setText(f"{moneda} {gastos:,.2f}")
        self.lbl_beneficio.setText(f"{moneda} {beneficio:,.2f}")
        self.lbl_pendiente.setText(f"{moneda} {kpis.get('saldo_pendiente', 0.0):,.2f}")
        
        top_equipo_monto = kpis.get('top_equipo_monto', 0.0)
        top_equipo_nombre = kpis.get('top_equipo_nombre', 'N/A')
        self.lbl_top_equipo.setText(f"{top_equipo_nombre}\n({moneda} {top_equipo_monto:,.2f})")
        
        top_operador_horas = kpis.get('top_operador_horas', 0.0)
        top_operador_nombre = kpis.get('top_operador_nombre', 'N/A')
        self.lbl_top_operador.setText(f"{top_operador_nombre}\n({top_operador_horas:.2f} Horas)")