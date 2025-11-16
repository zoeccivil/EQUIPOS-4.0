"""
Registro de Alquileres Tab para EQUIPOS 4.0
Adaptado para trabajar con Firebase en lugar de SQLite
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox, QDateEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)
from PyQt6.QtCore import QDate, Qt
from datetime import datetime, date
from firebase_manager import FirebaseManager


class RegistroAlquileresTab(QWidget):
    def __init__(self, firebase_manager: FirebaseManager, parent=None):
        super().__init__(parent)
        self.fm = firebase_manager

        self.cliente_filtro = "Todos"
        self.equipo_filtro = "Todos"
        self.operador_filtro = "Todos"
        self.clientes_mapa = {}
        self.equipos_mapa = {}
        self.operadores_mapa = {}
        self.transacciones_actuales = []

        self._setup_ui()
        self.poblar_filtros()
        self.refrescar_tabla()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # === Filtros ===
        filtros_group = QGroupBox("Filtros")
        filtros_layout = QHBoxLayout()
        filtros_group.setLayout(filtros_layout)

        self.combo_operador = QComboBox()
        self.combo_operador.addItem("Todos")
        filtros_layout.addWidget(QLabel("Operador:"))
        filtros_layout.addWidget(self.combo_operador)

        self.fecha_inicio = QDateEdit()
        self.fecha_inicio.setCalendarPopup(True)
        self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
        filtros_layout.addWidget(QLabel("Desde:"))
        filtros_layout.addWidget(self.fecha_inicio)

        self.fecha_fin = QDateEdit()
        self.fecha_fin.setCalendarPopup(True)
        self.fecha_fin.setDate(QDate.currentDate())
        filtros_layout.addWidget(QLabel("Hasta:"))
        filtros_layout.addWidget(self.fecha_fin)

        self.combo_cliente = QComboBox()
        self.combo_cliente.addItem("Todos")
        filtros_layout.addWidget(QLabel("Cliente:"))
        filtros_layout.addWidget(self.combo_cliente)

        self.combo_equipo = QComboBox()
        self.combo_equipo.addItem("Todos")
        filtros_layout.addWidget(QLabel("Equipo:"))
        filtros_layout.addWidget(self.combo_equipo)

        main_layout.addWidget(filtros_group)

        # === Botones de acción ===
        btn_layout = QHBoxLayout()
        self.btn_registrar = QPushButton("Registrar Alquiler")
        self.btn_editar = QPushButton("Editar Alquiler")
        self.btn_eliminar = QPushButton("Eliminar Alquiler")
        self.btn_marcar_pagado = QPushButton("Marcar como Pagado")
        btn_layout.addWidget(self.btn_registrar)
        btn_layout.addWidget(self.btn_editar)
        btn_layout.addWidget(self.btn_eliminar)
        btn_layout.addWidget(self.btn_marcar_pagado)
        btn_layout.addStretch(1)
        main_layout.addLayout(btn_layout)

        # Conexiones de botones
        self.btn_registrar.clicked.connect(self.registrar_alquiler)
        self.btn_editar.clicked.connect(self.editar_alquiler)
        self.btn_eliminar.clicked.connect(self.eliminar_alquiler)
        self.btn_marcar_pagado.clicked.connect(self.marcar_pagado)

        # === Tabla principal ===
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            'Fecha', 'Cliente', 'Operador', 'Equipo', 'Ubicación',
            'Horas', 'Precio/hora', 'Monto', 'Estado'
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.table)

        # === Indicadores inferiores ===
        indicadores_layout = QHBoxLayout()
        self.lbl_total_facturado = QLabel("Facturado: RD$ 0.00")
        self.lbl_total_abonado = QLabel("Pagado: RD$ 0.00")
        self.lbl_total_pendiente = QLabel("Pendiente: RD$ 0.00")
        self.lbl_total_horas = QLabel("Horas Totales: 0.00")
        indicadores_layout.addWidget(self.lbl_total_facturado)
        indicadores_layout.addWidget(self.lbl_total_abonado)
        indicadores_layout.addWidget(self.lbl_total_pendiente)
        indicadores_layout.addWidget(self.lbl_total_horas)
        main_layout.addLayout(indicadores_layout)

        # === Señales para refrescar los datos al cambiar filtros ===
        self.combo_cliente.currentIndexChanged.connect(self.refrescar_tabla)
        self.combo_operador.currentIndexChanged.connect(self.refrescar_tabla)
        self.combo_equipo.currentIndexChanged.connect(self.refrescar_tabla)
        self.fecha_inicio.dateChanged.connect(self.refrescar_tabla)
        self.fecha_fin.dateChanged.connect(self.refrescar_tabla)

    def refrescar_tabla(self):
        """Recarga la tabla con los filtros actuales"""
        self.table.setRowCount(0)
        filtros = self.get_current_filters()
        
        try:
            # Obtener transacciones desde Firebase
            self.transacciones_actuales = self.fm.obtener_transacciones(filtros)
            
            total_facturado = 0
            total_abonado = 0
            total_horas = 0.0
            
            for row, trans in enumerate(self.transacciones_actuales):
                self.table.insertRow(row)
                
                # Guardar ID en la primera celda
                item_fecha = QTableWidgetItem(str(trans.get('fecha', '')))
                item_fecha.setData(Qt.ItemDataRole.UserRole, trans.get('id'))
                self.table.setItem(row, 0, item_fecha)
                
                # Cliente
                cliente_id = trans.get('cliente_id')
                cliente_nombre = self._get_nombre_entidad(cliente_id) if cliente_id else ''
                self.table.setItem(row, 1, QTableWidgetItem(cliente_nombre))
                
                # Operador
                operador_id = trans.get('operador_id')
                operador_nombre = self._get_nombre_entidad(operador_id) if operador_id else ''
                self.table.setItem(row, 2, QTableWidgetItem(operador_nombre))
                
                # Equipo
                equipo_id = trans.get('equipo_id')
                equipo_nombre = self._get_nombre_equipo(equipo_id) if equipo_id else ''
                self.table.setItem(row, 3, QTableWidgetItem(equipo_nombre))
                
                # Otros campos
                self.table.setItem(row, 4, QTableWidgetItem(str(trans.get('ubicacion', ''))))
                self.table.setItem(row, 5, QTableWidgetItem(str(trans.get('horas', ''))))
                self.table.setItem(row, 6, QTableWidgetItem(f"RD$ {trans.get('precio_por_hora', 0):,.2f}"))
                
                monto = trans.get('monto', 0)
                self.table.setItem(row, 7, QTableWidgetItem(f"RD$ {monto:,.2f}"))
                
                pagado = trans.get('pagado', False)
                estado = "Pagado" if pagado else "Pendiente"
                self.table.setItem(row, 8, QTableWidgetItem(estado))
                
                # Acumular totales
                total_facturado += monto
                total_horas += trans.get('horas', 0)
                if pagado:
                    total_abonado += monto
            
            # Actualizar indicadores
            self.lbl_total_facturado.setText(f"Facturado: RD$ {total_facturado:,.2f}")
            self.lbl_total_abonado.setText(f"Pagado: RD$ {total_abonado:,.2f}")
            self.lbl_total_pendiente.setText(f"Pendiente: RD$ {total_facturado-total_abonado:,.2f}")
            self.lbl_total_horas.setText(f"Horas Totales: {total_horas:.2f}")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error cargando transacciones: {e}")

    def get_current_filters(self):
        """Obtiene los filtros actuales de la UI"""
        filtros = {
            'tipo': 'Ingreso',  # Solo alquileres (ingresos)
            'fecha_inicio': self.fecha_inicio.date().toString("yyyy-MM-dd"),
            'fecha_fin': self.fecha_fin.date().toString("yyyy-MM-dd")
        }
        
        cliente = self.combo_cliente.currentText()
        if cliente != "Todos" and cliente in self.clientes_mapa:
            filtros['cliente_id'] = self.clientes_mapa[cliente]
        
        operador = self.combo_operador.currentText()
        if operador != "Todos" and operador in self.operadores_mapa:
            filtros['operador_id'] = self.operadores_mapa[operador]
        
        equipo = self.combo_equipo.currentText()
        if equipo != "Todos" and equipo in self.equipos_mapa:
            filtros['equipo_id'] = self.equipos_mapa[equipo]
        
        return filtros

    def registrar_alquiler(self):
        """Abre diálogo para registrar un nuevo alquiler (simplificado)"""
        QMessageBox.information(self, "Info", 
                               "Función de registro completa pendiente de implementar.\n"
                               "Use la consola de Firebase temporalmente.")

    def editar_alquiler(self):
        """Edita el alquiler seleccionado"""
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Advertencia", "Selecciona una fila para editar.")
            return
        
        QMessageBox.information(self, "Info", 
                               "Función de edición completa pendiente de implementar.\n"
                               "Use la consola de Firebase temporalmente.")

    def eliminar_alquiler(self):
        """Elimina el alquiler seleccionado"""
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Advertencia", "Selecciona una fila para eliminar.")
            return
        
        item = self.table.item(selected, 0)
        alquiler_id = item.data(Qt.ItemDataRole.UserRole)
        if not alquiler_id:
            QMessageBox.warning(self, "Error", "No se pudo encontrar el ID del alquiler.")
            return
        
        confirm = QMessageBox.question(
            self, "Confirmar", "¿Eliminar el alquiler seleccionado?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.fm.eliminar_transaccion(alquiler_id)
                QMessageBox.information(self, "Éxito", "Alquiler eliminado.")
                self.refrescar_tabla()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo eliminar: {e}")

    def marcar_pagado(self):
        """Marca el alquiler seleccionado como pagado"""
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Advertencia", "Selecciona una fila.")
            return
        
        item = self.table.item(selected, 0)
        alquiler_id = item.data(Qt.ItemDataRole.UserRole)
        if not alquiler_id:
            return
        
        try:
            self.fm.editar_transaccion(alquiler_id, {'pagado': True})
            QMessageBox.information(self, "Éxito", "Marcado como pagado.")
            self.refrescar_tabla()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error: {e}")

    def poblar_filtros(self):
        """Pobla los combos de filtros con datos de Firebase"""
        try:
            # Cargar clientes
            clientes = self.fm.obtener_entidades(tipo='Cliente', activo=True) or []
            self.clientes_mapa = {c['nombre']: c['id'] for c in clientes}
            self.combo_cliente.blockSignals(True)
            self.combo_cliente.clear()
            self.combo_cliente.addItem("Todos")
            self.combo_cliente.addItems(sorted([c['nombre'] for c in clientes]))
            self.combo_cliente.blockSignals(False)
            
            # Cargar operadores
            operadores = self.fm.obtener_entidades(tipo='Operador', activo=True) or []
            self.operadores_mapa = {o['nombre']: o['id'] for o in operadores}
            self.combo_operador.blockSignals(True)
            self.combo_operador.clear()
            self.combo_operador.addItem("Todos")
            self.combo_operador.addItems(sorted([o['nombre'] for o in operadores]))
            self.combo_operador.blockSignals(False)
            
            # Cargar equipos
            equipos = self.fm.obtener_equipos(activo=True) or []
            self.equipos_mapa = {e['nombre']: e['id'] for e in equipos}
            self.combo_equipo.blockSignals(True)
            self.combo_equipo.clear()
            self.combo_equipo.addItem("Todos")
            self.combo_equipo.addItems(sorted([e['nombre'] for e in equipos]))
            self.combo_equipo.blockSignals(False)
            
        except Exception as e:
            print(f"Error poblando filtros: {e}")

    def _get_nombre_entidad(self, entidad_id):
        """Obtiene el nombre de una entidad por ID (con caché)"""
        # Buscar en clientes
        for nombre, id_val in self.clientes_mapa.items():
            if id_val == entidad_id:
                return nombre
        # Buscar en operadores
        for nombre, id_val in self.operadores_mapa.items():
            if id_val == entidad_id:
                return nombre
        return ''

    def _get_nombre_equipo(self, equipo_id):
        """Obtiene el nombre de un equipo por ID (con caché)"""
        for nombre, id_val in self.equipos_mapa.items():
            if id_val == equipo_id:
                return nombre
        return ''
