from PyQt6.QtWidgets import (
    QDialog, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QComboBox, QDateEdit, QTextEdit,
    QMessageBox, QLineEdit, QAbstractItemView, QFormLayout, QGroupBox
)
from PyQt6.QtCore import Qt, QDate
from datetime import datetime, date
from PyQt6.QtCore import pyqtSignal

class VentanaGestionAbonos(QDialog):
    """
    Ventana principal para gestionar abonos registrados.
    Permite filtrar por cliente y fecha, editar, eliminar y registrar abonos.
    """
    def __init__(self, db, proyecto, parent=None):
        super().__init__(parent)
        self.db = db
        self.proyecto = proyecto  # <--- ES UN sqlite3.Row, acceso con ['id']
        self.setWindowTitle("Gestión de Abonos Registrados")
        self.resize(1050, 650)
        self.clientes_mapa = {}
        self.total_abonos_var = "Monto Total Filtrado: 0.00"

        layout = QVBoxLayout(self)

        # --- Filtros ---
        filtros_box = QGroupBox("Filtros")
        filtros_layout = QHBoxLayout(filtros_box)

        self.combo_cliente = QComboBox()
        self.combo_cliente.addItem("Todos")
        clientes = self.db.obtener_entidades_equipo_por_tipo(self.proyecto['id'], 'Cliente')
        self.clientes_mapa = {c['nombre']: c['id'] for c in clientes}
        for nombre in sorted(self.clientes_mapa.keys()):
            self.combo_cliente.addItem(nombre)
        filtros_layout.addWidget(QLabel("Cliente:"))
        filtros_layout.addWidget(self.combo_cliente)

        self.fecha_inicio = QDateEdit()
        self.fecha_inicio.setCalendarPopup(True)
        self.fecha_fin = QDateEdit()
        self.fecha_fin.setCalendarPopup(True)
        primera_fecha = self.db.obtener_fecha_primera_transaccion(self.proyecto['id'])
        self.fecha_inicio.setDate(QDate.fromString(primera_fecha, "yyyy-MM-dd") if primera_fecha else QDate.currentDate())
        self.fecha_fin.setDate(QDate.currentDate())

        filtros_layout.addWidget(QLabel("Desde:"))
        filtros_layout.addWidget(self.fecha_inicio)
        filtros_layout.addWidget(QLabel("Hasta:"))
        filtros_layout.addWidget(self.fecha_fin)

        layout.addWidget(filtros_box)

        # --- Tabla de abonos ---
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Fecha", "Cliente", "Monto Abono", "Aplicado a Factura", "Comentario"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # --- Total y acciones ---
        acciones_layout = QHBoxLayout()
        self.lbl_total = QLabel(self.total_abonos_var)
        self.lbl_total.setStyleSheet("font-weight:bold;")
        acciones_layout.addWidget(self.lbl_total)

        btn_nuevo = QPushButton("Registrar Abono")
        btn_editar = QPushButton("Editar Abono")
        btn_eliminar = QPushButton("Eliminar Abono(s)")
        btn_cerrar = QPushButton("Cerrar")
        acciones_layout.addWidget(btn_nuevo)
        acciones_layout.addWidget(btn_editar)
        acciones_layout.addWidget(btn_eliminar)
        acciones_layout.addWidget(btn_cerrar)

        layout.addLayout(acciones_layout)

        # --- Conexiones ---
        self.combo_cliente.currentIndexChanged.connect(self.cargar_abonos)
        self.fecha_inicio.dateChanged.connect(self.cargar_abonos)
        self.fecha_fin.dateChanged.connect(self.cargar_abonos)
        btn_nuevo.clicked.connect(self.abrir_dialogo_nuevo_abono)
        btn_editar.clicked.connect(self.abrir_dialogo_editar_abono)
        btn_eliminar.clicked.connect(self.eliminar_abonos)
        btn_cerrar.clicked.connect(self.close)
        self.table.itemDoubleClicked.connect(self.abrir_dialogo_editar_abono)

        self.cargar_abonos()


    def cargar_abonos(self):
        """Carga y muestra los abonos filtrados en la tabla."""
        self.table.setRowCount(0)
        filtros = {
            'fecha_inicio': self.fecha_inicio.date().toString("yyyy-MM-dd"),
            'fecha_fin': self.fecha_fin.date().toString("yyyy-MM-dd")
        }
        cliente_sel = self.combo_cliente.currentText()
        if cliente_sel != "Todos":
            filtros['cliente_id'] = self.clientes_mapa[cliente_sel]

        abonos = self.db.obtener_lista_abonos(self.proyecto['id'], filtros)
        total = 0.0
        for abono in abonos:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(abono['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(str(abono['fecha'])))
            self.table.setItem(row, 2, QTableWidgetItem(str(abono['cliente_nombre'])))
            self.table.setItem(row, 3, QTableWidgetItem(f"{self.proyecto['moneda']} {abono['monto']:,.2f}"))
            # Para campos opcionales, usa acceso con corchetes y .keys()
            trans_desc = abono['transaccion_descripcion'] if 'transaccion_descripcion' in abono.keys() and abono['transaccion_descripcion'] is not None else ''
            comentario = abono['comentario'] if 'comentario' in abono.keys() and abono['comentario'] is not None else ''
            self.table.setItem(row, 4, QTableWidgetItem(str(trans_desc)))
            self.table.setItem(row, 5, QTableWidgetItem(str(comentario)))
            total += abono['monto']
        self.lbl_total.setText(f"Monto Total Filtrado: {self.proyecto['moneda']} {total:,.2f}")

    def abrir_dialogo_nuevo_abono(self):
        dlg = DialogoRegistroAbono(self.db, self.proyecto, parent=self)
        if dlg.exec():
            self.cargar_abonos()

    def abrir_dialogo_editar_abono(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección requerida", "Seleccione un abono para editar.")
            return
        if len(selected_rows) > 1:
            QMessageBox.warning(self, "Selección múltiple", "Seleccione solo un abono para editar.")
            return
        pago_id = int(self.table.item(selected_rows[0].row(), 0).text())
        datos = self.db.obtener_abono_por_id(pago_id)
        if not datos:
            QMessageBox.warning(self, "Error", "No se pudo cargar el abono.")
            return
        dlg = DialogoEditarAbono(self.db, self.proyecto, datos, parent=self)
        if dlg.exec():
            self.cargar_abonos()

    def eliminar_abonos(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección requerida", "Seleccione uno o más abonos para eliminar.")
            return
        pago_ids = [int(self.table.item(row.row(), 0).text()) for row in selected_rows]
        msg = ("¿Está seguro de que desea eliminar el abono seleccionado?" if len(pago_ids) == 1
               else f"¿Está seguro de que desea eliminar los {len(pago_ids)} abonos seleccionados?")
        if QMessageBox.question(self, "Confirmar Eliminación", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self.db.eliminar_abono(pago_ids):
                QMessageBox.information(self, "Éxito", "Abono(s) eliminado(s) correctamente.")
                self.cargar_abonos()
            else:
                QMessageBox.warning(self, "Error", "No se pudieron eliminar los abonos.")

class DialogoEditarAbono(QDialog):
    def __init__(self, db, proyecto, datos, parent=None):
        super().__init__(parent)
        self.db = db
        self.proyecto = proyecto
        self.datos = datos
        self.setWindowTitle("Editar Abono")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.fecha_edit = QDateEdit()
        self.fecha_edit.setCalendarPopup(True)
        self.fecha_edit.setDate(QDate.fromString(datos['fecha'], "yyyy-MM-dd"))
        self.monto_edit = QLineEdit(str(datos['monto']))
        # Para campos opcionales:
        comentario_val = datos['comentario'] if 'comentario' in datos.keys() and datos['comentario'] is not None else ""
        self.comentario_edit = QLineEdit(comentario_val)

        layout.addRow("Fecha:", self.fecha_edit)
        layout.addRow("Monto:", self.monto_edit)
        layout.addRow("Comentario:", self.comentario_edit)

        btns = QHBoxLayout()
        btn_guardar = QPushButton("Guardar Cambios")
        btn_cancelar = QPushButton("Cancelar")
        btns.addWidget(btn_guardar)
        btns.addWidget(btn_cancelar)
        layout.addRow(btns)

        btn_guardar.clicked.connect(self.guardar)
        btn_cancelar.clicked.connect(self.reject)

    def guardar(self):
        try:
            nuevo_monto = float(self.monto_edit.text())
            nueva_fecha = self.fecha_edit.date().toString("yyyy-MM-dd")
            nuevo_comentario = self.comentario_edit.text().strip()
            if self.db.actualizar_abono(self.datos['id'], nueva_fecha, nuevo_monto, nuevo_comentario):
                QMessageBox.information(self, "Éxito", "Abono actualizado correctamente.", parent=self)
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "No se pudo actualizar el abono.", parent=self)
        except ValueError:
            QMessageBox.warning(self, "Dato Inválido", "El monto debe ser un número válido.", parent=self)
        except Exception as ex:
            QMessageBox.critical(self, "Error", f"Ocurrió un error: {ex}", parent=self)

class DialogoRegistroAbono(QDialog):
    """
    Diálogo para registrar un abono general a un cliente, mostrando facturas pendientes y permitiendo aplicar el monto.
    """
    def __init__(self, db, proyecto, parent=None):
        super().__init__(parent)
        self.db = db
        self.proyecto = proyecto
        self.setWindowTitle("Registrar Abono a Cliente")
        self.resize(600, 500)
        self.clientes_mapa = {}
        self.cuentas_mapa = {}

        layout = QVBoxLayout(self)

        form = QFormLayout()
        clientes = self.db.obtener_entidades_equipo_por_tipo(self.proyecto['id'], 'Cliente')
        self.clientes_mapa = {c['nombre']: c['id'] for c in clientes if ('activo' not in c.keys() or c['activo'])}
        self.combo_cliente = QComboBox()
        self.combo_cliente.addItems(sorted(self.clientes_mapa.keys()))
        form.addRow("Cliente:", self.combo_cliente)

        self.fecha_edit = QDateEdit()
        self.fecha_edit.setCalendarPopup(True)
        self.fecha_edit.setDate(QDate.currentDate())
        form.addRow("Fecha del Abono:", self.fecha_edit)

        self.monto_edit = QLineEdit()
        form.addRow("Monto a Abonar:", self.monto_edit)

        cuentas = self.db.listar_cuentas() or []
        self.cuentas_mapa = {c['nombre']: c['id'] for c in cuentas}
        self.combo_cuenta = QComboBox()
        self.combo_cuenta.addItems(sorted(self.cuentas_mapa.keys()))
        form.addRow("Depositar en Cuenta:", self.combo_cuenta)

        self.comentario_edit = QLineEdit()
        form.addRow("Comentario:", self.comentario_edit)

        layout.addLayout(form)

        # Facturas pendientes
        self.tree_pendientes = QTableWidget(0, 3)
        self.tree_pendientes.setHorizontalHeaderLabels(["Fecha", "Descripción", "Monto"])
        self.tree_pendientes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(QLabel("Facturas Pendientes de Pago"))
        layout.addWidget(self.tree_pendientes)
        self.lbl_total_pendiente = QLabel("Total Pendiente: 0.00")
        self.lbl_total_pendiente.setStyleSheet("font-weight:bold;color:red")
        layout.addWidget(self.lbl_total_pendiente)

        # Botones
        btns = QHBoxLayout()
        btn_guardar = QPushButton("Guardar Abono")
        btn_cancelar = QPushButton("Cancelar")
        btns.addWidget(btn_guardar)
        btns.addWidget(btn_cancelar)
        layout.addLayout(btns)

        self.combo_cliente.currentIndexChanged.connect(self.actualizar_facturas_pendientes)
        btn_guardar.clicked.connect(self.guardar_abono)
        btn_cancelar.clicked.connect(self.reject)

        self.actualizar_facturas_pendientes()

    def actualizar_facturas_pendientes(self):
        self.tree_pendientes.setRowCount(0)
        cliente_nombre = self.combo_cliente.currentText()
        cliente_id = self.clientes_mapa.get(cliente_nombre)
        if not cliente_id:
            self.lbl_total_pendiente.setText("Total Pendiente: 0.00")
            return
        pendientes = self.db.obtener_transacciones_pendientes_cliente(self.proyecto['id'], cliente_id)
        total = 0.0
        for trans in pendientes:
            row = self.tree_pendientes.rowCount()
            self.tree_pendientes.insertRow(row)
            self.tree_pendientes.setItem(row, 0, QTableWidgetItem(str(trans['fecha'])))
            self.tree_pendientes.setItem(row, 1, QTableWidgetItem(str(trans['descripcion'])))
            self.tree_pendientes.setItem(row, 2, QTableWidgetItem(f"{self.proyecto['moneda']} {trans['monto']:,.2f}"))
            total += trans['monto']
        self.lbl_total_pendiente.setText(f"Total Pendiente: {self.proyecto['moneda']} {total:,.2f}")


    abono_registrado = pyqtSignal()

    def guardar_abono(self):
        try:
            cliente_nombre = self.combo_cliente.currentText()
            cliente_id = self.clientes_mapa.get(cliente_nombre)
            cuenta_nombre = self.combo_cuenta.currentText()
            cuenta_id = self.cuentas_mapa.get(cuenta_nombre)
            monto = float(self.monto_edit.text())
            if not (cliente_id and cuenta_id and monto > 0):
                raise ValueError("Debe seleccionar un cliente, una cuenta de destino y un monto válido.")
            datos_pago = {
                'proyecto_id': self.proyecto['id'],
                'cliente_id': cliente_id,
                'fecha': self.fecha_edit.date().toString("yyyy-MM-dd"),
                'monto': monto,
                'cuenta_id': cuenta_id,
                'comentario': self.comentario_edit.text().strip()
            }
            resultado = self.db.registrar_abono_general_cliente(datos_pago)
            if resultado is True:
                QMessageBox.information(self, "Éxito", "Abono registrado y aplicado correctamente.")
                self.abono_registrado.emit()  # <--- EMITIR LA SEÑAL
                self.accept()
            else:
                QMessageBox.warning(self, "Aviso", str(resultado))
        except ValueError as e:
            QMessageBox.warning(self, "Error de Validación", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error: {e}")
