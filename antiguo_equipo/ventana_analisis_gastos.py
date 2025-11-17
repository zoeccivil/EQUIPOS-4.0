from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHBoxLayout

class VentanaAnalisisGastos(QDialog):
    def __init__(self, db_manager, proyecto_actual):
        super().__init__()
        self.db = db_manager
        self.proyecto_actual = proyecto_actual
        self.setWindowTitle("Análisis de Gastos")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Análisis de Gastos por Categoría y Subcategoría"))

        self.tabla_categorias = QTableWidget()
        layout.addWidget(QLabel("Gastos por Categoría"))
        layout.addWidget(self.tabla_categorias)

        self.tabla_equipos = QTableWidget()
        layout.addWidget(QLabel("Gastos por Subcategoría"))
        layout.addWidget(self.tabla_equipos)

        self.refrescar_categorias()
        self.refrescar_equipos()

    def refrescar_categorias(self):
        datos = self.db.analisis_gastos_por_categoria(self.proyecto_actual['id']) if self.proyecto_actual else []
        self.tabla_categorias.setColumnCount(2)
        self.tabla_categorias.setHorizontalHeaderLabels(["Categoría", "Total Gastos"])
        self.tabla_categorias.setRowCount(len(datos))
        for i, cat in enumerate(datos):
            self.tabla_categorias.setItem(i, 0, QTableWidgetItem(cat.get('categoria', '')))
            self.tabla_categorias.setItem(i, 1, QTableWidgetItem(str(cat.get('total_gastos', 0))))

    def refrescar_equipos(self):
        datos = self.db.analisis_gastos_por_equipo(self.proyecto_actual['id']) if self.proyecto_actual else []
        self.tabla_equipos.setColumnCount(2)
        self.tabla_equipos.setHorizontalHeaderLabels(["Subcategoría", "Total Gastos"])
        self.tabla_equipos.setRowCount(len(datos))
        for i, sub in enumerate(datos):
            self.tabla_equipos.setItem(i, 0, QTableWidgetItem(EQ.get('equipo', '')))
            self.tabla_equipos.setItem(i, 1, QTableWidgetItem(str(EQ.get('total_gastos', 0))))
