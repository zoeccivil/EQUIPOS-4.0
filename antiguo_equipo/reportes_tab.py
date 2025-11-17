from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit, QPushButton, QFileDialog, QMessageBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import QDate
from datetime import datetime
from report_generator import ReportGenerator

class ReportesTab(QWidget):
    def __init__(self, db, config, parent=None):
        super().__init__(parent)
        self.db = db
        self.config = config

        self.clientes_mapa = {}

        # ---- Layout principal ----
        layout = QVBoxLayout(self)
        filtros_layout = QHBoxLayout()
        filtros_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # --- Cliente ---
        self.combo_cliente = QComboBox()
        filtros_layout.addWidget(QLabel("Cliente:"))
        filtros_layout.addWidget(self.combo_cliente)

        # --- Fechas ---
        self.fecha_inicio = QDateEdit()
        self.fecha_inicio.setCalendarPopup(True)
        filtros_layout.addWidget(QLabel("Desde:"))
        filtros_layout.addWidget(self.fecha_inicio)

        self.fecha_fin = QDateEdit()
        self.fecha_fin.setCalendarPopup(True)
        self.fecha_fin.setDate(QDate.currentDate())
        filtros_layout.addWidget(QLabel("Hasta:"))
        filtros_layout.addWidget(self.fecha_fin)

        filtros_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addLayout(filtros_layout)

        # ---- Botones de reportes ----
        btns_layout = QHBoxLayout()
        self.btn_detallado_pdf = QPushButton("Reporte Detallado PDF")
        self.btn_detallado_excel = QPushButton("Reporte Detallado Excel")
        self.btn_operadores_pdf = QPushButton("Reporte Operadores PDF")
        self.btn_operadores_excel = QPushButton("Reporte Operadores Excel")
        self.btn_estado_cuenta_pdf = QPushButton("Estado de Cuenta Cliente (PDF)")
        self.btn_estado_cuenta_general_pdf = QPushButton("Estado de Cuenta General (PDF)")

        for btn in [
            self.btn_detallado_pdf, self.btn_detallado_excel, 
            self.btn_operadores_pdf, self.btn_operadores_excel,
            self.btn_estado_cuenta_pdf, self.btn_estado_cuenta_general_pdf
        ]:
            btns_layout.addWidget(btn)
        layout.addLayout(btns_layout)

        # ---- Conexión de botones ----
        self.btn_detallado_pdf.clicked.connect(self.generar_reporte_detallado_pdf)
        self.btn_detallado_excel.clicked.connect(self.generar_reporte_detallado_excel)
        self.btn_operadores_pdf.clicked.connect(self.generar_reporte_operadores_pdf)
        self.btn_operadores_excel.clicked.connect(self.generar_reporte_operadores_excel)
        self.btn_estado_cuenta_pdf.clicked.connect(self.generar_estado_cuenta_cliente_pdf)
        self.btn_estado_cuenta_general_pdf.clicked.connect(self.generar_estado_cuenta_general_pdf)

        # ---- Cargar los filtros iniciales ----
        self.cargar_clientes()
        self.fecha_inicio.setDate(QDate.currentDate())

    def cargar_clientes(self):
        """Carga todos los clientes únicos de la tabla equipos_alquiler_meta."""
        self.combo_cliente.clear()
        self.combo_cliente.addItem("Todos")
        self.clientes_mapa = {}
        try:
            # Este método debe existir en tu db manager.
            clientes = self.db.obtener_clientes_unicos_meta()
            self.clientes_mapa = {c['nombre']: c['id'] for c in clientes}
            self.combo_cliente.addItems(sorted(self.clientes_mapa.keys()))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron cargar los clientes: {e}")

    def _get_current_filters(self):
        filtros = {
            'fecha_inicio': self.fecha_inicio.date().toString("yyyy-MM-dd"),
            'fecha_fin': self.fecha_fin.date().toString("yyyy-MM-dd")
        }
        cliente = self.combo_cliente.currentText()
        if cliente != "Todos" and cliente in self.clientes_mapa:
            filtros['cliente_id'] = self.clientes_mapa[cliente]
        return filtros

    # --- Reporte Detallado de Alquileres ---
    def generar_reporte_detallado_pdf(self):
        self._exportar_reporte_detallado(extension="pdf")

    def generar_reporte_detallado_excel(self):
        self._exportar_reporte_detallado(extension="excel")

    def _exportar_reporte_detallado(self, extension="pdf"):
        filtros = self._get_current_filters()
        data = self.db.obtener_transacciones_por_filtros(filtros)
        if not data:
            QMessageBox.information(self, "Sin datos", "No hay datos para el período/filtros seleccionados.")
            return

        column_map = {
            'fecha': 'Fecha', 'conduce': 'Conduce', 'cliente_nombre': 'Cliente',
            'operador_nombre': 'Operador', 'equipo_nombre': 'Equipo', 'ubicacion': 'Ubicación',
            'horas': 'Horas', 'precio_por_hora': 'Precio/Hora', 'monto': 'Monto', 'pagado': 'Pagado'
        }
        title = "REPORTE DETALLADO DE ALQUILERES"
        date_range = f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"
        rg = ReportGenerator(
            data=data,
            title=title,
            project_name="",
            date_range=date_range,
            currency_symbol=self.config.get('moneda', 'RD$'),
            column_map=column_map
        )
        if extension == "pdf":
            file_path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", "", "PDF (*.pdf)")
            if not file_path:
                return
            ok, error = rg.to_pdf(file_path)
        else:
            file_path, _ = QFileDialog.getSaveFileName(self, "Guardar Excel", "", "Excel (*.xlsx)")
            if not file_path:
                return
            ok, error = rg.to_excel(file_path)

        if ok:
            QMessageBox.information(self, "Éxito", f"Reporte generado en:\n{file_path}")
        else:
            QMessageBox.critical(self, "Error", f"No se pudo generar el reporte:\n{error}")

    # --- Reporte de Operadores ---
    def generar_reporte_operadores_pdf(self):
        self._exportar_reporte_operadores(extension="pdf")

    def generar_reporte_operadores_excel(self):
        self._exportar_reporte_operadores(extension="excel")

    def _exportar_reporte_operadores(self, extension="pdf"):
        filtros = self._get_current_filters()
        data = self.db.analisis_horas_por_operador_global(filtros['fecha_inicio'], filtros['fecha_fin'])
        if not data:
            QMessageBox.information(self, "Sin datos", "No hay datos de operadores para los filtros seleccionados.")
            return

        column_map = {
            'nombre': 'Operador', 'total_horas': 'Total Horas'
        }
        title = "REPORTE DE OPERADORES"
        date_range = f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"
        rg = ReportGenerator(
            data=data,
            title=title,
            project_name="",
            date_range=date_range,
            currency_symbol=self.config.get('moneda', 'RD$'),
            column_map=column_map
        )
        if extension == "pdf":
            file_path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", "", "PDF (*.pdf)")
            if not file_path:
                return
            ok, error = rg.to_pdf(file_path)
        else:
            file_path, _ = QFileDialog.getSaveFileName(self, "Guardar Excel", "", "Excel (*.xlsx)")
            if not file_path:
                return
            ok, error = rg.to_excel(file_path)
        if ok:
            QMessageBox.information(self, "Éxito", f"Reporte generado en:\n{file_path}")
        else:
            QMessageBox.critical(self, "Error", f"No se pudo generar el reporte:\n{error}")

    # --- Estado de Cuenta Cliente Individual ---
    def generar_estado_cuenta_cliente_pdf(self):
        cliente = self.combo_cliente.currentText()
        if cliente == "Todos":
            QMessageBox.warning(self, "Cliente Requerido", "Por favor, seleccione un cliente específico para el estado de cuenta.")
            return
        filtros = self._get_current_filters()
        if cliente in self.clientes_mapa:
            filtros['cliente_id'] = self.clientes_mapa[cliente]
        facturas, abonos = self.db.obtener_datos_estado_cuenta_cliente_global(
            filtros['cliente_id'],
            filtros['fecha_inicio'],
            filtros['fecha_fin']
        )
        if not facturas:
            QMessageBox.information(self, "Sin datos", "No hay facturas para el período/filtros seleccionados.")
            return
        column_map = {
            'fecha': 'Fecha', 'equipo_nombre': 'Equipo', 'horas': 'Horas', 'monto': 'Monto'
        }
        title = f"ESTADO DE CUENTA - {cliente}"
        date_range = f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"
        rg = ReportGenerator(
            data=facturas,
            title=title,
            project_name="",
            date_range=date_range,
            currency_symbol=self.config.get('moneda', 'RD$'),
            column_map=column_map
        )
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", "", "PDF (*.pdf)")
        if not file_path:
            return
        ok, error = rg.to_pdf(file_path)
        if ok:
            QMessageBox.information(self, "Éxito", f"Reporte generado en:\n{file_path}")
        else:
            QMessageBox.critical(self, "Error", f"No se pudo generar el reporte:\n{error}")

    # --- Estado de Cuenta General ---
    def generar_estado_cuenta_general_pdf(self):
        filtros = self._get_current_filters()
        facturas, abonos = self.db.obtener_datos_estado_cuenta_general_global(
            filtros['fecha_inicio'],
            filtros['fecha_fin']
        )
        if not facturas:
            QMessageBox.information(self, "Sin datos", "No hay facturas para el período/filtros seleccionados.")
            return
        column_map = {
            'cliente_nombre': 'Cliente', 'equipo_nombre': 'Equipo', 'horas': 'Horas', 'monto': 'Monto'
        }
        title = f"ESTADO DE CUENTA GENERAL"
        date_range = f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"
        rg = ReportGenerator(
            data=facturas,
            title=title,
            project_name="",
            date_range=date_range,
            currency_symbol=self.config.get('moneda', 'RD$'),
            column_map=column_map
        )
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", "", "PDF (*.pdf)")
        if not file_path:
            return
        ok, error = rg.to_pdf(file_path)
        if ok:
            QMessageBox.information(self, "Éxito", f"Reporte generado en:\n{file_path}")
        else:
            QMessageBox.critical(self, "Error", f"No se pudo generar el reporte:\n{error}")
