from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDateEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog
)
from PyQt6.QtCore import QDate
from firebase_manager import FirebaseManager
from report_generator import ReportGenerator
import logging

logger = logging.getLogger(__name__)


class DialogoPreviewRendimientos(QDialog):
    """
    Vista previa del Reporte de Rendimientos por equipo.

    Funcionalidades básicas (se mantienen intactas):
      - Seleccionar equipo (o todos) y rango de fechas
      - Ver datos agregados por equipo en una tabla
      - Exportar a PDF / Excel usando ReportGenerator
      - Formatos de moneda, cálculos de precio por hora y margen existentes

    Extensiones (MODALIDADES):
      - Se agrega soporte a modalidades (horas / volumen / fijo) que ya tu FirebaseManager
        calcula en obtener_rendimiento_por_equipo.
      - Nuevas columnas sin alterar las originales (las primeras 9 columnas siguen igual):
          1. Equipo
          2. Horas Fact.
          3. Facturado
          4. Horas Pag.
          5. Pagado Op.
          6. Precio/h Fact.
          7. Precio/h Pag.
          8. Margen
          9. % Margen
        Columnas nuevas añadidas al final:
          10. Volumen Fact.      (solo si modalidad volumen > 0, si no 0.00)
          11. Precio/u Fact.     (monto_facturado / volumen_facturado si volumen > 0)
          12. Modalidad(s)       (lista de modalidades presentes para ese equipo en el rango)
    - Exportación: se amplía column_map para incluir las nuevas columnas en PDF/Excel.

    NOTA:
      - Si un equipo mezcla horas y volumen en el rango seleccionado, se mostrarán ambas
        métricas (Horas Fact. y Volumen Fact.). Modalidad(s) = "Horas, Volumen".
      - Si no tiene horas ni volumen pero facturado > 0 => se asume modalidad FIJO.

    """

    def __init__(self, fm: FirebaseManager, equipos_mapa: dict, config: dict, storage_manager, parent=None):
        super().__init__(parent)
        self.fm = fm
        self.equipos_mapa = equipos_mapa or {}
        self.config = config or {}
        self.sm = storage_manager
        self.setWindowTitle("Preview - Reporte de Rendimientos por Equipo")
        self.resize(1250, 650)

        self.moneda = self.config.get("app", {}).get("moneda", "RD$")

        layout = QVBoxLayout(self)

        # --- Filtros arriba ---
        filtros_layout = QHBoxLayout()

        # Equipo
        filtros_layout.addWidget(QLabel("Equipo:"))
        self.combo_equipo = QComboBox()
        self.combo_equipo.addItem("Todos", None)
        for eid, nombre in sorted(self.equipos_mapa.items(), key=lambda x: x[1]):
            self.combo_equipo.addItem(nombre, str(eid))
        filtros_layout.addWidget(self.combo_equipo)

        # Fechas
        filtros_layout.addWidget(QLabel("Desde:"))
        self.fecha_inicio = QDateEdit(calendarPopup=True)
        self.fecha_inicio.setDisplayFormat("yyyy-MM-dd")
        filtros_layout.addWidget(self.fecha_inicio)

        filtros_layout.addWidget(QLabel("Hasta:"))
        self.fecha_fin = QDateEdit(calendarPopup=True)
        self.fecha_fin.setDisplayFormat("yyyy-MM-dd")
        filtros_layout.addWidget(self.fecha_fin)

        # Botón actualizar
        self.btn_actualizar = QPushButton("Actualizar")
        filtros_layout.addWidget(self.btn_actualizar)

        layout.addLayout(filtros_layout)

        # --- Tabla preview ---
        # Original tenía 9 columnas. Añadimos 3 más al final (Volumen, Precio/u, Modalidad(s))
        self.table = QTableWidget(0, 12)
        self.table.setHorizontalHeaderLabels(
            [
                "Equipo",            # 0 (igual)
                "Horas Fact.",       # 1 (igual)
                "Facturado",         # 2 (igual)
                "Horas Pag.",        # 3 (igual)
                "Pagado Op.",        # 4 (igual)
                "Precio/h Fact.",    # 5 (igual)
                "Precio/h Pag.",     # 6 (igual)
                "Margen",            # 7 (igual)
                "% Margen",          # 8 (igual)
                "Volumen Fact.",     # 9 (nuevo)
                "Precio/u Fact.",    # 10 (nuevo)
                "Modalidad(s)",      # 11 (nuevo)
            ]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # --- Botones de exportación ---
        botones_layout = QHBoxLayout()
        self.btn_pdf = QPushButton("Exportar PDF")
        self.btn_excel = QPushButton("Exportar Excel")
        self.btn_cerrar = QPushButton("Cerrar")

        botones_layout.addWidget(self.btn_pdf)
        botones_layout.addWidget(self.btn_excel)
        botones_layout.addStretch()
        botones_layout.addWidget(self.btn_cerrar)

        layout.addLayout(botones_layout)

        # Conexiones
        self.btn_actualizar.clicked.connect(self.cargar_datos)
        self.btn_pdf.clicked.connect(lambda: self.exportar("pdf"))
        self.btn_excel.clicked.connect(lambda: self.exportar("excel"))
        self.btn_cerrar.clicked.connect(self.reject)

        # Filtro dinámico: recargar cada vez que cambien filtros
        self.combo_equipo.currentIndexChanged.connect(self.cargar_datos)
        self.fecha_inicio.dateChanged.connect(lambda _d: self.cargar_datos())
        self.fecha_fin.dateChanged.connect(lambda _d: self.cargar_datos())

        # Inicializar fechas y cargar datos
        self._init_fechas()
        self.cargar_datos()

    # ------------------------------------------------------------

    def _init_fechas(self):
        """Rango inicial: desde primera transacción de alquileres hasta hoy."""
        try:
            fecha_str = self.fm.obtener_fecha_primera_transaccion()  # más antigua entre alquileres
        except Exception:
            fecha_str = None

        if fecha_str:
            qd = QDate.fromString(fecha_str, "yyyy-MM-dd")
            if qd.isValid():
                self.fecha_inicio.setDate(qd)
            else:
                self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
        else:
            self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))

        self.fecha_fin.setDate(QDate.currentDate())

    def _obtener_filtros(self) -> dict:
        """Obtiene filtros seguros (sin claves inexistentes)."""
        equipo_id = self.combo_equipo.currentData()
        if equipo_id is not None:
            equipo_id = str(equipo_id)

        fi = self.fecha_inicio.date()
        ff = self.fecha_fin.date()
        # Normalizar si el usuario invierte fechas
        if fi > ff:
            fi, ff = ff, fi
            self.fecha_inicio.setDate(fi)
            self.fecha_fin.setDate(ff)

        return {
            "equipo_id": equipo_id,
            "fecha_inicio": fi.toString("yyyy-MM-dd"),
            "fecha_fin": ff.toString("yyyy-MM-dd"),
        }

    # ------------------------------------------------------------ Datos

    def cargar_datos(self):
        """Carga los rendimientos agregados por equipo y los muestra en la tabla."""
        try:
            datos_formateados, _ = self._construir_dataset()
        except Exception as e:
            logger.error(f"Error construyendo dataset de rendimientos: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar los rendimientos:\n{e}",
            )
            return

        self.table.setRowCount(0)

        if not datos_formateados:
            return

        # Cargar filas acorde a los encabezados (respetando las 12 columnas ahora)
        for fila_dato in datos_formateados:
            fila = self.table.rowCount()
            self.table.insertRow(fila)
            valores = [
                fila_dato.get("equipo", ""),                 # 0
                fila_dato.get("horas_facturadas", ""),       # 1
                fila_dato.get("monto_facturado", ""),        # 2
                fila_dato.get("horas_pagadas_operador", ""), # 3
                fila_dato.get("monto_pagado_operador", ""),  # 4
                fila_dato.get("precio_hora_facturado", ""),  # 5
                fila_dato.get("precio_hora_pagado", ""),     # 6
                fila_dato.get("margen_bruto_simple", ""),    # 7
                fila_dato.get("margen_porcentaje", ""),      # 8
                fila_dato.get("volumen_facturado", ""),      # 9 (nuevo)
                fila_dato.get("precio_unidad_facturado", ""),# 10 (nuevo)
                fila_dato.get("modalidades", ""),            # 11 (nuevo)
            ]
            for col, val in enumerate(valores):
                self.table.setItem(fila, col, QTableWidgetItem(str(val)))

    # ------------------------------------------------------------ Exportar

    def _construir_dataset(self):
        """
        Reconstruye el dataset formateado que usan la tabla y el ReportGenerator.

        NUEVO:
        - volumen_facturado
        - precio_unidad_facturado
        - modalidades
        """
        filtros = self._obtener_filtros()
        rendimiento = self.fm.obtener_rendimiento_por_equipo(
            fecha_inicio=filtros.get("fecha_inicio"),
            fecha_fin=filtros.get("fecha_fin"),
            equipo_id=filtros.get("equipo_id"),
        )

        datos = []
        for r in rendimiento or []:
            eid = str(r.get("equipo_id", "") or "")
            nombre = self.equipos_mapa.get(eid, r.get("equipo_nombre") or f"ID:{eid}")

            horas_fact = float(r.get("horas_facturadas", 0) or 0)
            vol_fact = float(r.get("volumen_facturado", 0) or 0)
            monto_fact = float(r.get("monto_facturado", 0) or 0)
            horas_pag = float(r.get("horas_pagadas_operador", 0) or 0)
            monto_pag = float(r.get("monto_pagado_operador", 0) or 0)

            # Precios
            precio_hora_fact = (monto_fact / horas_fact) if horas_fact > 0 else 0.0
            precio_hora_pag = (monto_pag / horas_pag) if horas_pag > 0 else 0.0
            precio_unidad_fact = (monto_fact / vol_fact) if vol_fact > 0 else 0.0

            # Margen
            margen = monto_fact - monto_pag
            margen_pct = (margen / monto_fact * 100.0) if monto_fact > 0 else 0.0

            # Modalidades presentes
            modalidades = []
            if horas_fact > 0:
                modalidades.append("Horas")
            if vol_fact > 0:
                modalidades.append("Volumen")
            if horas_fact == 0 and vol_fact == 0 and monto_fact > 0:
                modalidades.append("Fijo")
            modalidades_txt = ", ".join(modalidades) if modalidades else "-"

            # Formato visual
            horas_fact_fmt = f"{round(horas_fact, 2):,.2f}"
            horas_pag_fmt = f"{round(horas_pag, 2):,.2f}"
            vol_fact_fmt = f"{round(vol_fact, 2):,.2f}"

            monto_fact_fmt = f"{self.moneda} {round(monto_fact, 2):,.2f}"
            monto_pag_fmt = f"{self.moneda} {round(monto_pag, 2):,.2f}"
            precio_fact_fmt = f"{self.moneda} {round(precio_hora_fact, 2):,.2f}"
            precio_pag_fmt = f"{self.moneda} {round(precio_hora_pag, 2):,.2f}"
            precio_unidad_fmt = f"{self.moneda} {round(precio_unidad_fact, 2):,.2f}"
            margen_fmt = f"{self.moneda} {round(margen, 2):,.2f}"
            margen_pct_fmt = f"{round(margen_pct, 2):,.2f}%"

            datos.append(
                {
                    "equipo": nombre,
                    "horas_facturadas": horas_fact_fmt,
                    "monto_facturado": monto_fact_fmt,
                    "horas_pagadas_operador": horas_pag_fmt,
                    "monto_pagado_operador": monto_pag_fmt,
                    "precio_hora_facturado": precio_fact_fmt,
                    "precio_hora_pagado": precio_pag_fmt,
                    "margen_bruto_simple": margen_fmt,
                    "margen_porcentaje": margen_pct_fmt,
                    # Nuevos
                    "volumen_facturado": vol_fact_fmt,
                    "precio_unidad_facturado": precio_unidad_fmt,
                    "modalidades": modalidades_txt,
                }
            )

        return datos, filtros

    def exportar(self, formato: str):
        """Exporta usando ReportGenerator (PDF / Excel) incluyendo columnas nuevas."""
        try:
            datos, filtros = self._construir_dataset()
            if not datos:
                QMessageBox.information(
                    self,
                    "Sin datos",
                    "No hay datos para exportar en el rango seleccionado.",
                )
                return

            ext = "PDF (*.pdf)" if formato == "pdf" else "Excel (*.xlsx)"
            sugerido = (
                f"Reporte_Rendimientos_{filtros.get('fecha_inicio')}_a_{filtros.get('fecha_fin')}"
            ).replace(" ", "_")
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte de Rendimientos",
                sugerido,
                ext,
            )
            if not file_path:
                return

            # Map de columnas (incluye las nuevas)
            column_map = {
                "equipo": "Equipo",
                "horas_facturadas": "Horas Fact.",
                "monto_facturado": "Facturado",
                "horas_pagadas_operador": "Horas Pag.",
                "monto_pagado_operador": "Pagado Op.",
                "precio_hora_facturado": "Precio/h Fact.",
                "precio_hora_pagado": "Precio/h Pag.",
                "margen_bruto_simple": "Margen",
                "margen_porcentaje": "% Margen",
                "volumen_facturado": "Volumen Fact.",
                "precio_unidad_facturado": "Precio/u Fact.",
                "modalidades": "Modalidad(s)",
            }

            title = "REPORTE DE RENDIMIENTOS POR EQUIPO"
            date_range = f"{filtros.get('fecha_inicio')} a {filtros.get('fecha_fin')}"

            rg = ReportGenerator(
                data=datos,
                title=title,
                cliente="",
                date_range=date_range,
                currency_symbol=self.moneda,
                storage_manager=self.sm,
                column_map=column_map,
            )

            if formato == "pdf":
                ok, error = rg.to_pdf(file_path)
            else:
                ok, error = rg.to_excel(file_path)

            if ok:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Reporte de rendimientos generado exitosamente:\n{file_path}",
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo generar el reporte de rendimientos:\n{error}",
                )

        except Exception as e:
            logger.error(f"Error exportando reporte de rendimientos: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Ocurrió un error al exportar el reporte:\n{e}",
            )