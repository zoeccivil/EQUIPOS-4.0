"""
Dashboard Tab para EQUIPOS 4.0
¡MODIFICADO (V6)!
- Corregido el 'ID Desconocido'
- Corregida la carga inicial (race condition)
- Lee de 'alquileres' y 'gastos'
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from datetime import datetime
from firebase_manager import FirebaseManager
import logging
import calendar

logger = logging.getLogger(__name__)

class DashboardTab(QWidget):
    """
    Widget que muestra indicadores clave de negocio (KPIs) usando PyQt6 y Firebase.
    """
    def __init__(self, firebase_manager: FirebaseManager, parent=None):
        super().__init__(parent)
        self.fm = firebase_manager

        self.meses_mapa = {
            "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
            "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
        }
        
        # Mapas (se llenarán desde app_gui)
        self.equipos_mapa_nombre_id = {} # nombre -> id
        self.equipos_mapa_id_nombre = {} # id -> nombre
        self.operadores_mapa_id_nombre = {} # id -> nombre

        self._setup_ui()
        self._configurar_filtros_inicial()
        
    def _crear_tarjeta_kpi(self, titulo, style_sheet="color: #333;"):
        """Crea una tarjeta KPI usando QGroupBox y QLabel."""
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
        
        # === Filtros ===
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

        main_layout.addWidget(filtros_group, stretch=0)

        # === Grid de Tarjetas KPI ===
        grid_layout = QGridLayout()

        # Fila 1
        card_ingresos, self.lbl_ingresos = self._crear_tarjeta_kpi("Ingresos (Periodo)", "color: green;")
        grid_layout.addWidget(card_ingresos, 0, 0)
        card_gastos, self.lbl_gastos = self._crear_tarjeta_kpi("Gastos (Periodo)", "color: red;")
        grid_layout.addWidget(card_gastos, 0, 1)
        card_beneficio, self.lbl_beneficio = self._crear_tarjeta_kpi("Beneficio (Periodo)", "color: #00529B;")
        grid_layout.addWidget(card_beneficio, 0, 2)

        # Fila 2
        card_pendiente, self.lbl_pendiente = self._crear_tarjeta_kpi("Saldo Pendiente Total", "color: #E67E22;")
        grid_layout.addWidget(card_pendiente, 1, 0)
        card_equipo, self.lbl_top_equipo = self._crear_tarjeta_kpi("Equipo Más Rentable (Periodo)")
        grid_layout.addWidget(card_equipo, 1, 1)
        card_operador, self.lbl_top_operador = self._crear_tarjeta_kpi("Operador con Más Horas (Periodo)")
        grid_layout.addWidget(card_operador, 1, 2)

        main_layout.addLayout(grid_layout, stretch=1)

        # === Conexiones ===
        self.combo_anio.currentIndexChanged.connect(self.refrescar_datos)
        self.combo_mes.currentIndexChanged.connect(self.refrescar_datos)
        self.combo_equipo.currentIndexChanged.connect(self.refrescar_datos)

    def _configurar_filtros_inicial(self):
        """Pobla los filtros de fecha (sin datos de DB)."""
        self.combo_anio.blockSignals(True)
        self.combo_mes.blockSignals(True)

        # Poblar años (últimos 5 años)
        self.combo_anio.clear()
        anio_actual = datetime.now().year
        anios = [str(anio_actual - i) for i in range(5)]
        self.combo_anio.addItems(anios)
        self.combo_anio.setCurrentText(str(anio_actual))
        
        # Establecer mes actual
        nombre_mes_actual = list(self.meses_mapa.keys())[datetime.now().month - 1]
        self.combo_mes.setCurrentText(nombre_mes_actual)

        self.combo_anio.blockSignals(False)
        self.combo_mes.blockSignals(False)

    def actualizar_mapas(self, mapas: dict):
        """Recibe los mapas desde la ventana principal y puebla los combos."""
        logger.info("Dashboard: Mapas recibidos. Poblando filtros...")
        self.equipos_mapa_id_nombre = mapas.get("equipos", {})
        self.operadores_mapa_id_nombre = mapas.get("operadores", {})
        
        # Invertir mapa de equipos para el combo
        self.equipos_mapa_nombre_id = {nombre: id for id, nombre in self.equipos_mapa_id_nombre.items()}

        self.combo_equipo.blockSignals(True)
        self.combo_equipo.clear()
        self.combo_equipo.addItem("Todos", None)
        self.combo_equipo.addItems(sorted(self.equipos_mapa_nombre_id.keys()))
        self.combo_equipo.blockSignals(False)
        
    def refrescar_datos(self):
        """Obtiene nuevos datos KPI desde Firebase y actualiza la UI."""
        if not all([self.combo_anio.currentText(), self.combo_mes.currentText()]):
            return
        
        # Esperar a que los mapas estén cargados
        if not self.equipos_mapa_id_nombre or not self.operadores_mapa_id_nombre:
            logger.warning("Dashboard: Mapas aún no cargados, saltando refresco.")
            return

        anio = int(self.combo_anio.currentText())
        mes = self.meses_mapa[self.combo_mes.currentText()]
        
        equipo_id = self.combo_equipo.currentData() # Usa currentData()

        try:
            # Calcular KPIs desde Firebase
            kpis = self.fm.obtener_estadisticas_dashboard({'ano': anio, 'mes': mes, 'equipo_id': equipo_id})
            
            # Actualizar labels
            moneda = "RD$"
            ingresos = kpis.get('ingresos_mes', 0.0)
            gastos = kpis.get('gastos_mes', 0.0)
            beneficio = ingresos - gastos

            self.lbl_ingresos.setText(f"{moneda} {ingresos:,.2f}")
            self.lbl_gastos.setText(f"{moneda} {gastos:,.2f}")
            self.lbl_beneficio.setText(f"{moneda} {beneficio:,.2f}")
            self.lbl_pendiente.setText(f"{moneda} {kpis.get('saldo_pendiente', 0.0):,.2f}")
            
            # Calcular Tops (ahora se hace aquí, no en el manager)
            ingresos_data = kpis.get('ingresos_data', [])
            
            # Top Equipo
            equipos_ingresos = {}
            for ingreso in ingresos_data:
                eq_id = str(ingreso.get('equipo_id'))
                if eq_id:
                    equipos_ingresos[eq_id] = equipos_ingresos.get(eq_id, 0) + ingreso.get('monto', 0)
            
            top_equipo_id = max(equipos_ingresos, key=equipos_ingresos.get) if equipos_ingresos else None
            top_equipo_nombre = "N/A"
            top_equipo_monto = 0.0
            if top_equipo_id:
                top_equipo_nombre = self.equipos_mapa_id_nombre.get(top_equipo_id, f"ID: {top_equipo_id}")
                top_equipo_monto = equipos_ingresos[top_equipo_id]

            self.lbl_top_equipo.setText(f"{top_equipo_nombre}\n({moneda} {top_equipo_monto:,.2f})")
            
            # Top Operador
            operadores_horas = {}
            for ingreso in ingresos_data:
                op_id = str(ingreso.get('operador_id'))
                horas = float(ingreso.get('horas', 0))
                if op_id and horas:
                    operadores_horas[op_id] = operadores_horas.get(op_id, 0) + horas
            
            top_operador_id = max(operadores_horas, key=operadores_horas.get) if operadores_horas else None
            top_operador_nombre = "N/A"
            top_operador_horas = 0.0
            if top_operador_id:
                top_operador_nombre = self.operadores_mapa_id_nombre.get(top_operador_id, f"ID: {top_operador_id}")
                top_operador_horas = operadores_horas[top_operador_id]

            self.lbl_top_operador.setText(f"{top_operador_nombre}\n({top_operador_horas:.2f} Horas)")
            
        except Exception as e:
            logger.error(f"Error refrescando datos: {e}", exc_info=True)
            # No limpiar labels, podría ser un error de índice
            # self._limpiar_labels()

    def _limpiar_labels(self):
        """Limpia los labels de KPI."""
        moneda = "RD$"
        self.lbl_ingresos.setText(f"{moneda} 0.00")
        self.lbl_gastos.setText(f"{moneda} 0.00")
        self.lbl_beneficio.setText(f"{moneda} 0.00")
        self.lbl_pendiente.setText(f"{moneda} 0.00")
        self.lbl_top_equipo.setText("N/A")
        self.lbl_top_operador.setText("N/A")