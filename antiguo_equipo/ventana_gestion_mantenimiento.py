from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView, QDateEdit, QTextEdit
)
from PyQt6.QtCore import QDate, Qt
from dialogo_mantenimiento import DialogoMantenimiento
from dialogo_intervalo_equipo import DialogoIntervaloEquipo  # Importa el diálogo correcto

class VentanaGestionMantenimientos(QDialog):
    """
    Gestión de Mantenimiento de Equipos por ID real.
    """
    def __init__(self, db, proyecto_actual, parent=None):
        super().__init__(parent)
        self.db = db
        self.proyecto_actual = proyecto_actual
        self.setWindowTitle("Gestión y Estado de Mantenimiento de Equipos")
        self.resize(1100, 700)

        layout = QVBoxLayout(self)

        # Estado equipos: agregamos ID oculto
        self.table_estado = QTableWidget(0, 6)
        self.table_estado.setHorizontalHeaderLabels([
            "Equipo", "Intervalo de Servicio", "Uso desde Servicio",
            "Uso Restante", "Progreso de Uso", "ID"
        ])
        self.table_estado.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_estado.setColumnHidden(5, True)
        layout.addWidget(QLabel("Estado Actual de Equipos (Mantenimiento)"))
        layout.addWidget(self.table_estado)

        # Botones acción
        btns = QHBoxLayout()
        btn_registrar = QPushButton("Registrar Nuevo Mantenimiento")
        btn_editar = QPushButton("Editar Mantenimiento")
        btn_eliminar = QPushButton("Eliminar Mantenimiento")
        btn_configurar_intervalo = QPushButton("Configurar Intervalo")
        btns.addWidget(btn_registrar)
        btns.addWidget(btn_editar)
        btns.addWidget(btn_eliminar)
        btns.addWidget(btn_configurar_intervalo)
        layout.addLayout(btns)

        # Historial mantenimiento
        self.table_historial = QTableWidget(0, 6)
        self.table_historial.setHorizontalHeaderLabels([
            "ID", "Fecha Servicio", "Costo", "Descripción",
            "Horas Totales Equipo", "KM Totales Equipo"
        ])
        self.table_historial.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(QLabel("Historial de Mantenimiento del Equipo Seleccionado"))
        layout.addWidget(self.table_historial)

        btn_registrar.clicked.connect(self.abrir_dialogo_registro)
        btn_editar.clicked.connect(self.editar_mantenimiento_seleccionado)
        btn_eliminar.clicked.connect(self.eliminar_mantenimiento_seleccionado)
        btn_configurar_intervalo.clicked.connect(self.abrir_dialogo_intervalo)
        self.table_estado.itemSelectionChanged.connect(self.cargar_historial_equipo)
        self.table_historial.itemDoubleClicked.connect(self.editar_mantenimiento_seleccionado)

        self.refrescar_estado_equipos()

    def refrescar_estado_equipos(self):
        self.table_estado.setRowCount(0)
        estado_equipos = self.db.obtener_estado_mantenimiento_equipos(self.proyecto_actual['id'])

        print("=== DEBUG: Equipos recibidos en refrescar_estado_equipos ===")
        for eq in estado_equipos:
            print(eq)
        print("============================================================")

        for eq in estado_equipos:
            row = self.table_estado.rowCount()
            self.table_estado.insertRow(row)
            self.table_estado.setItem(row, 0, QTableWidgetItem(eq['nombre']))
            self.table_estado.setItem(row, 1, QTableWidgetItem(eq['intervalo_txt']))
            self.table_estado.setItem(row, 2, QTableWidgetItem(eq['uso_txt']))
            self.table_estado.setItem(row, 3, QTableWidgetItem(eq['restante_txt']))
            progreso_item = QTableWidgetItem(eq['progreso_txt'])
            if eq.get('critico'):
                progreso_item.setBackground(Qt.GlobalColor.red)
            elif eq.get('alerta'):
                progreso_item.setBackground(Qt.GlobalColor.yellow)
            self.table_estado.setItem(row, 4, progreso_item)
            self.table_estado.setItem(row, 5, QTableWidgetItem(str(eq['id'])))

    def cargar_historial_equipo(self):
        selected = self.table_estado.currentRow()
        if selected == -1:
            self.table_historial.setRowCount(0)
            return
        equipo_id = self.table_estado.item(selected, 5).text()
        lista = self.db.obtener_mantenimientos_por_equipo(equipo_id)
        self.table_historial.setRowCount(0)
        for m in lista:
            row = self.table_historial.rowCount()
            self.table_historial.insertRow(row)
            self.table_historial.setItem(row, 0, QTableWidgetItem(str(m.get('id', ''))))
            self.table_historial.setItem(row, 1, QTableWidgetItem(str(m.get('fecha_servicio', ''))))
            self.table_historial.setItem(row, 2, QTableWidgetItem(str(m.get('costo', ''))))
            self.table_historial.setItem(row, 3, QTableWidgetItem(str(m.get('descripcion', ''))))
            self.table_historial.setItem(row, 4, QTableWidgetItem(str(m.get('horas_totales_equipo', ''))))
            self.table_historial.setItem(row, 5, QTableWidgetItem(str(m.get('km_totales_equipo', ''))))

    def abrir_dialogo_registro(self):
        selected = self.table_estado.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Selección requerida", "Seleccione un equipo primero.")
            return
        equipo_id = self.table_estado.item(selected, 5).text()
        dlg = DialogoMantenimiento(self.db, self.proyecto_actual, equipo_id=equipo_id, datos=None, parent=self)
        if dlg.exec():
            self.refrescar_estado_equipos()
            self.cargar_historial_equipo()

    def editar_mantenimiento_seleccionado(self):
        selected_hist = self.table_historial.currentRow()
        selected_estado = self.table_estado.currentRow()
        if selected_hist == -1 or selected_estado == -1:
            return
        mid = self.table_historial.item(selected_hist, 0).text()
        equipo_id = self.table_estado.item(selected_estado, 5).text()
        lista = self.db.obtener_mantenimientos_por_equipo(equipo_id)
        mantenimiento = next((m for m in lista if str(m.get('id')) == str(mid)), None)
        if not mantenimiento:
            return
        dlg = DialogoMantenimiento(self.db, self.proyecto_actual, equipo_id=equipo_id, datos=mantenimiento, parent=self)
        if dlg.exec():
            self.refrescar_estado_equipos()
            self.cargar_historial_equipo()

    def eliminar_mantenimiento_seleccionado(self):
        selected_hist = self.table_historial.currentRow()
        if selected_hist == -1:
            QMessageBox.warning(self, "Selección requerida", "Seleccione un mantenimiento a eliminar.")
            return
        mid = self.table_historial.item(selected_hist, 0).text()
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            "¿Eliminar este mantenimiento?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            exito = self.db.eliminar_mantenimiento(mid)
            if exito:
                QMessageBox.information(self, "Éxito", "Mantenimiento eliminado.")
                self.refrescar_estado_equipos()
                self.cargar_historial_equipo()
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el mantenimiento.")

    def abrir_dialogo_intervalo(self):
        dlg = DialogoIntervaloEquipo(self.db, self.proyecto_actual['id'], parent=self)
        if dlg.exec():
            self.refrescar_estado_equipos()
            self.cargar_historial_equipo()