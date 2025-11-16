from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHBoxLayout

class VentanaAnalisis(QDialog):
    def __init__(self, db_manager, proyecto_actual):
        super().__init__()
        self.db = db_manager
        self.proyecto_actual = proyecto_actual
        self.setWindowTitle("Análisis de Ingresos y Horas")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Análisis de Ingresos y Horas por Operador y Equipo"))

        self.tabla_operadores = QTableWidget()
        layout.addWidget(QLabel("Horas por Operador"))
        layout.addWidget(self.tabla_operadores)

        self.tabla_equipos = QTableWidget()
        layout.addWidget(QLabel("Ingresos por Equipo"))
        layout.addWidget(self.tabla_equipos)

        self.refrescar_operadores()
        self.refrescar_equipos()

    def refrescar_operadores(self):
        datos = self.db.analisis_horas_por_operador(self.proyecto_actual['id']) if self.proyecto_actual else []
        self.tabla_operadores.setColumnCount(2)
        self.tabla_operadores.setHorizontalHeaderLabels(["Operador", "Total Horas"])
        self.tabla_operadores.setRowCount(len(datos))
        for i, op in enumerate(datos):
            self.tabla_operadores.setItem(i, 0, QTableWidgetItem(op.get('nombre', '')))
            self.tabla_operadores.setItem(i, 1, QTableWidgetItem(str(op.get('total_horas', 0))))

    def refrescar_equipos(self):
        datos = self.db.analisis_ingresos_por_equipo(self.proyecto_actual['id']) if self.proyecto_actual else []
        self.tabla_equipos.setColumnCount(2)
        self.tabla_equipos.setHorizontalHeaderLabels(["Equipo", "Total Ingresos"])
        self.tabla_equipos.setRowCount(len(datos))
        for i, eq in enumerate(datos):
            self.tabla_equipos.setItem(i, 0, QTableWidgetItem(eq.get('nombre', '')))
            self.tabla_equipos.setItem(i, 1, QTableWidgetItem(str(eq.get('total_ingresos', 0))))
