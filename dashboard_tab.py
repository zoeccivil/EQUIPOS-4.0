"""
Dashboard Tab para EQUIPOS 4.0
Adaptado para trabajar con Firebase en lugar de SQLite
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from datetime import datetime
from firebase_manager import FirebaseManager


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
        self.equipos_mapa = {}

        self._setup_ui()
        
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

    def configurar_filtros(self):
        """Pobla los combos de filtros con datos de Firebase."""
        # Bloquear señales para evitar múltiples refrescos
        self.combo_anio.blockSignals(True)
        self.combo_mes.blockSignals(True)
        self.combo_equipo.blockSignals(True)

        # Poblar años (últimos 5 años)
        self.combo_anio.clear()
        anio_actual = datetime.now().year
        anios = [str(anio_actual - i) for i in range(5)]
        self.combo_anio.addItems(anios)
        self.combo_anio.setCurrentText(str(anio_actual))
        
        # Poblar equipos
        self.combo_equipo.clear()
        try:
            equipos = self.fm.obtener_equipos(activo=True) or []
            self.equipos_mapa = {e['nombre']: e['id'] for e in equipos}
            self.combo_equipo.addItem("Todos", -1)
            self.combo_equipo.addItems(sorted(self.equipos_mapa.keys()))
        except Exception as e:
            print(f"Error cargando equipos: {e}")

        # Establecer mes actual
        nombre_mes_actual = list(self.meses_mapa.keys())[datetime.now().month - 1]
        self.combo_mes.setCurrentText(nombre_mes_actual)

        # Desbloquear señales y refrescar
        self.combo_anio.blockSignals(False)
        self.combo_mes.blockSignals(False)
        self.combo_equipo.blockSignals(False)
        
        self.refrescar_datos()

    def refrescar_datos(self):
        """Obtiene nuevos datos KPI desde Firebase y actualiza la UI."""
        if not all([self.combo_anio.currentText(), self.combo_mes.currentText()]):
            return

        anio = int(self.combo_anio.currentText())
        mes = self.meses_mapa[self.combo_mes.currentText()]
        
        equipo_nombre = self.combo_equipo.currentText()
        equipo_id = self.equipos_mapa.get(equipo_nombre) if equipo_nombre != "Todos" else None

        try:
            # Calcular KPIs desde Firebase
            kpis = self._calcular_kpis(anio, mes, equipo_id)
            
            # Actualizar labels
            moneda = "RD$"
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
            
        except Exception as e:
            print(f"Error refrescando datos: {e}")
            self._limpiar_labels()

    def _calcular_kpis(self, anio: int, mes: int, equipo_id: str = None):
        """Calcula los KPIs desde Firebase para el periodo especificado."""
        # Calcular fechas del periodo
        fecha_inicio = f"{anio}-{mes:02d}-01"
        # Último día del mes
        if mes == 12:
            fecha_fin = f"{anio}-12-31"
        else:
            import calendar
            ultimo_dia = calendar.monthrange(anio, mes)[1]
            fecha_fin = f"{anio}-{mes:02d}-{ultimo_dia}"
        
        # Filtros base
        filtros_base = {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        }
        
        if equipo_id:
            filtros_base['equipo_id'] = equipo_id
        
        # Obtener transacciones del periodo
        filtros_ingresos = {**filtros_base, 'tipo': 'Ingreso'}
        filtros_gastos = {**filtros_base, 'tipo': 'Gasto'}
        
        ingresos = self.fm.obtener_transacciones(filtros_ingresos)
        gastos = self.fm.obtener_transacciones(filtros_gastos)
        
        # Calcular totales
        total_ingresos = sum(t.get('monto', 0) for t in ingresos)
        total_gastos = sum(t.get('monto', 0) for t in gastos)
        
        # Saldo pendiente (transacciones no pagadas)
        pendientes = self.fm.obtener_transacciones({'pagado': False, 'tipo': 'Ingreso'})
        saldo_pendiente = sum(t.get('monto', 0) for t in pendientes)
        
        # Top equipo por ingresos en el periodo
        equipos_ingresos = {}
        for ingreso in ingresos:
            eq_id = ingreso.get('equipo_id')
            if eq_id:
                equipos_ingresos[eq_id] = equipos_ingresos.get(eq_id, 0) + ingreso.get('monto', 0)
        
        top_equipo_id = max(equipos_ingresos, key=equipos_ingresos.get) if equipos_ingresos else None
        top_equipo_nombre = "N/A"
        top_equipo_monto = 0.0
        
        if top_equipo_id:
            try:
                equipo = self.fm.obtener_equipo(top_equipo_id)
                if equipo:
                    top_equipo_nombre = equipo.get('nombre', 'N/A')
                    top_equipo_monto = equipos_ingresos[top_equipo_id]
            except:
                pass
        
        # Top operador por horas en el periodo
        operadores_horas = {}
        for ingreso in ingresos:
            op_id = ingreso.get('operador_id')
            horas = ingreso.get('horas', 0)
            if op_id and horas:
                operadores_horas[op_id] = operadores_horas.get(op_id, 0) + horas
        
        top_operador_id = max(operadores_horas, key=operadores_horas.get) if operadores_horas else None
        top_operador_nombre = "N/A"
        top_operador_horas = 0.0
        
        if top_operador_id:
            try:
                operador = self.fm.obtener_entidad(top_operador_id)
                if operador:
                    top_operador_nombre = operador.get('nombre', 'N/A')
                    top_operador_horas = operadores_horas[top_operador_id]
            except:
                pass
        
        return {
            'ingresos_mes': total_ingresos,
            'gastos_mes': total_gastos,
            'saldo_pendiente': saldo_pendiente,
            'top_equipo_nombre': top_equipo_nombre,
            'top_equipo_monto': top_equipo_monto,
            'top_operador_nombre': top_operador_nombre,
            'top_operador_horas': top_operador_horas
        }
    
    def _limpiar_labels(self):
        """Limpia los labels de KPI."""
        moneda = "RD$"
        self.lbl_ingresos.setText(f"{moneda} 0.00")
        self.lbl_gastos.setText(f"{moneda} 0.00")
        self.lbl_beneficio.setText(f"{moneda} 0.00")
        self.lbl_pendiente.setText(f"{moneda} 0.00")
        self.lbl_top_equipo.setText("N/A")
        self.lbl_top_operador.setText("N/A")
