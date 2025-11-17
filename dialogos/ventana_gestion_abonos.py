"""
Ventana de gestión de abonos de clientes
Adaptado para trabajar con Firebase/Firestore
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QDateEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QLineEdit, QFormLayout, QHeaderView
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DialogoAbono(QDialog):
    """Diálogo para crear/editar un abono"""
    
    def __init__(self, firebase_manager, cliente_id, cliente_nombre, abono_datos=None, parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.cliente_id = cliente_id
        self.cliente_nombre = cliente_nombre
        self.abono_datos = abono_datos
        
        self.setWindowTitle("Editar Abono" if abono_datos else "Nuevo Abono")
        self.setMinimumWidth(400)
        
        self._crear_interfaz()
        
        if abono_datos:
            self._cargar_datos()
    
    def _crear_interfaz(self):
        """Crea la interfaz del diálogo"""
        layout = QFormLayout(self)
        
        # Cliente (solo lectura)
        self.label_cliente = QLabel(self.cliente_nombre)
        self.label_cliente.setStyleSheet("font-weight: bold;")
        layout.addRow("Cliente:", self.label_cliente)
        
        # Fecha
        self.fecha = QDateEdit(calendarPopup=True)
        self.fecha.setDate(QDate.currentDate())
        layout.addRow("Fecha:", self.fecha)
        
        # Monto
        self.monto = QLineEdit()
        self.monto.setPlaceholderText("0.00")
        layout.addRow("Monto:", self.monto)
        
        # Concepto
        self.concepto = QLineEdit()
        self.concepto.setPlaceholderText("Descripción del abono")
        layout.addRow("Concepto:", self.concepto)
        
        # Método de pago
        self.metodo_pago = QComboBox()
        self.metodo_pago.addItems(["Efectivo", "Transferencia", "Cheque", "Tarjeta", "Otro"])
        layout.addRow("Método de Pago:", self.metodo_pago)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_guardar = QPushButton("💾 Guardar")
        btn_guardar.clicked.connect(self.accept)
        btn_cancelar = QPushButton("✖️ Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_guardar)
        btn_layout.addWidget(btn_cancelar)
        layout.addRow(btn_layout)
    
    def _cargar_datos(self):
        """Carga datos de abono existente"""
        if not self.abono_datos:
            return
        
        fecha_str = self.abono_datos.get('fecha', '')
        if fecha_str:
            self.fecha.setDate(QDate.fromString(fecha_str, "yyyy-MM-dd"))
        
        monto = self.abono_datos.get('monto', 0)
        self.monto.setText(str(monto))
        
        concepto = self.abono_datos.get('concepto', '')
        self.concepto.setText(concepto)
        
        metodo = self.abono_datos.get('metodo_pago', 'Efectivo')
        idx = self.metodo_pago.findText(metodo)
        if idx >= 0:
            self.metodo_pago.setCurrentIndex(idx)
    
    def get_datos(self):
        """Retorna los datos del abono"""
        try:
            monto = float(self.monto.text() or 0)
        except ValueError:
            monto = 0.0
        
        return {
            'cliente_id': self.cliente_id,
            'fecha': self.fecha.date().toString("yyyy-MM-dd"),
            'monto': monto,
            'concepto': self.concepto.text().strip() or 'Abono',
            'metodo_pago': self.metodo_pago.currentText()
        }


class VentanaGestionAbonos(QDialog):
    """Ventana principal de gestión de abonos"""
    
    def __init__(self, firebase_manager, mapas, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Abonos")
        self.setMinimumSize(900, 600)
        self.fm = firebase_manager
        self.mapas = mapas
        
        self._crear_interfaz()
        self._actualizar_tabla()
        self._actualizar_deuda()
    
    def _crear_interfaz(self):
        """Crea la interfaz de la ventana"""
        layout = QVBoxLayout(self)
        
        # --- Filtros ---
        filtros_layout = QHBoxLayout()
        
        # Cliente
        filtros_layout.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        self.combo_cliente.addItem("Todos", None)
        if 'clientes_mapa' in self.mapas:
            for nombre, cliente_id in self.mapas['clientes_mapa'].items():
                self.combo_cliente.addItem(nombre, cliente_id)
        self.combo_cliente.currentIndexChanged.connect(self._actualizar_tabla)
        self.combo_cliente.currentIndexChanged.connect(self._actualizar_deuda)
        filtros_layout.addWidget(self.combo_cliente)
        
        # Fechas
        filtros_layout.addWidget(QLabel("Desde:"))
        self.fecha_inicio = QDateEdit(calendarPopup=True)
        self.fecha_inicio.setDate(QDate.currentDate().addMonths(-3))
        self.fecha_inicio.dateChanged.connect(self._actualizar_tabla)
        filtros_layout.addWidget(self.fecha_inicio)
        
        filtros_layout.addWidget(QLabel("Hasta:"))
        self.fecha_fin = QDateEdit(calendarPopup=True)
        self.fecha_fin.setDate(QDate.currentDate())
        self.fecha_fin.dateChanged.connect(self._actualizar_tabla)
        filtros_layout.addWidget(self.fecha_fin)
        
        filtros_layout.addStretch()
        layout.addLayout(filtros_layout)
        
        # --- Resumen de Deuda ---
        self.label_deuda = QLabel()
        self.label_deuda.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background-color: #F0F0F0; border-radius: 5px;")
        layout.addWidget(self.label_deuda)
        
        # --- Tabla de Abonos ---
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels(["ID", "Fecha", "Cliente", "Monto", "Concepto", "Método"])
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.hideColumn(0)  # Ocultar columna ID
        
        # Ajustar anchos
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Fecha
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Cliente
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Monto
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Concepto
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Método
        
        self.tabla.doubleClicked.connect(self._editar_abono)
        layout.addWidget(self.tabla)
        
        # --- Botones ---
        btn_layout = QHBoxLayout()
        
        btn_nuevo = QPushButton("➕ Nuevo Abono")
        btn_nuevo.clicked.connect(self._nuevo_abono)
        btn_layout.addWidget(btn_nuevo)
        
        btn_editar = QPushButton("✏️ Editar")
        btn_editar.clicked.connect(self._editar_abono)
        btn_layout.addWidget(btn_editar)
        
        btn_eliminar = QPushButton("🗑️ Eliminar")
        btn_eliminar.clicked.connect(self._eliminar_abono)
        btn_layout.addWidget(btn_eliminar)
        
        btn_layout.addStretch()
        
        btn_cerrar = QPushButton("✖️ Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cerrar)
        
        layout.addLayout(btn_layout)
    
    def _actualizar_tabla(self):
        """Actualiza la tabla con los abonos filtrados"""
        try:
            cliente_id = self.combo_cliente.currentData()
            fecha_inicio = self.fecha_inicio.date().toString("yyyy-MM-dd")
            fecha_fin = self.fecha_fin.date().toString("yyyy-MM-dd")
            
            abonos = self.fm.obtener_abonos(cliente_id, fecha_inicio, fecha_fin)
            
            self.tabla.setRowCount(0)
            
            for abono in abonos:
                row = self.tabla.rowCount()
                self.tabla.insertRow(row)
                
                # ID (oculto)
                self.tabla.setItem(row, 0, QTableWidgetItem(abono.get('id', '')))
                
                # Fecha
                self.tabla.setItem(row, 1, QTableWidgetItem(abono.get('fecha', '')))
                
                # Cliente
                cliente_nombre = next(
                    (nombre for nombre, cid in self.mapas.get('clientes_mapa', {}).items() 
                     if cid == abono.get('cliente_id')),
                    'Desconocido'
                )
                self.tabla.setItem(row, 2, QTableWidgetItem(cliente_nombre))
                
                # Monto
                monto = float(abono.get('monto', 0))
                monto_item = QTableWidgetItem(f"RD$ {monto:,.2f}")
                monto_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.tabla.setItem(row, 3, monto_item)
                
                # Concepto
                self.tabla.setItem(row, 4, QTableWidgetItem(abono.get('concepto', '')))
                
                # Método
                self.tabla.setItem(row, 5, QTableWidgetItem(abono.get('metodo_pago', '')))
            
            logger.info(f"Tabla actualizada con {len(abonos)} abonos")
            
        except Exception as e:
            logger.error(f"Error al actualizar tabla: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al cargar abonos:\n{str(e)}")
    
    def _actualizar_deuda(self):
        """Actualiza el label de deuda del cliente seleccionado"""
        try:
            cliente_id = self.combo_cliente.currentData()
            
            if cliente_id is None:
                self.label_deuda.setText("Seleccione un cliente para ver su estado de cuenta")
                self.label_deuda.setStyleSheet("font-size: 14px; padding: 10px; background-color: #F0F0F0; border-radius: 5px;")
                return
            
            fecha_inicio = self.fecha_inicio.date().toString("yyyy-MM-dd")
            fecha_fin = self.fecha_fin.date().toString("yyyy-MM-dd")
            
            deuda = self.fm.calcular_deuda_cliente(cliente_id, fecha_inicio, fecha_fin)
            
            facturado = deuda['total_facturado']
            abonado = deuda['total_abonado']
            saldo = deuda['saldo']
            
            cliente_nombre = self.combo_cliente.currentText()
            
            texto = (f"Cliente: {cliente_nombre} | "
                    f"Total Facturado: RD$ {facturado:,.2f} | "
                    f"Total Abonado: RD$ {abonado:,.2f} | "
                    f"Saldo: RD$ {saldo:,.2f}")
            
            # Color según el saldo
            if saldo > 0:
                estilo = "font-size: 14px; font-weight: bold; padding: 10px; background-color: #FFEBEE; color: #C62828; border-radius: 5px;"
            elif saldo < 0:
                estilo = "font-size: 14px; font-weight: bold; padding: 10px; background-color: #E8F5E9; color: #2E7D32; border-radius: 5px;"
            else:
                estilo = "font-size: 14px; font-weight: bold; padding: 10px; background-color: #E3F2FD; color: #1565C0; border-radius: 5px;"
            
            self.label_deuda.setText(texto)
            self.label_deuda.setStyleSheet(estilo)
            
        except Exception as e:
            logger.error(f"Error al actualizar deuda: {e}", exc_info=True)
    
    def _nuevo_abono(self):
        """Crea un nuevo abono"""
        try:
            cliente_id = self.combo_cliente.currentData()
            
            if cliente_id is None:
                QMessageBox.warning(self, "Advertencia", "Debe seleccionar un cliente específico para crear un abono.")
                return
            
            cliente_nombre = self.combo_cliente.currentText()
            
            dialogo = DialogoAbono(self.fm, cliente_id, cliente_nombre, parent=self)
            
            if dialogo.exec():
                datos = dialogo.get_datos()
                
                if datos['monto'] <= 0:
                    QMessageBox.warning(self, "Advertencia", "El monto debe ser mayor a 0")
                    return
                
                abono_id = self.fm.crear_abono(datos)
                
                if abono_id:
                    QMessageBox.information(self, "Éxito", "Abono registrado exitosamente")
                    self._actualizar_tabla()
                    self._actualizar_deuda()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo crear el abono")
        
        except Exception as e:
            logger.error(f"Error al crear abono: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al crear abono:\n{str(e)}")
    
    def _editar_abono(self):
        """Edita el abono seleccionado"""
        try:
            row = self.tabla.currentRow()
            if row < 0:
                QMessageBox.warning(self, "Advertencia", "Debe seleccionar un abono para editar")
                return
            
            abono_id = self.tabla.item(row, 0).text()
            
            # Obtener datos actuales del abono
            cliente_id = None
            for nombre, cid in self.mapas.get('clientes_mapa', {}).items():
                if nombre == self.tabla.item(row, 2).text():
                    cliente_id = cid
                    break
            
            if not cliente_id:
                QMessageBox.critical(self, "Error", "No se pudo identificar el cliente")
                return
            
            abono_datos = {
                'id': abono_id,
                'cliente_id': cliente_id,
                'fecha': self.tabla.item(row, 1).text(),
                'monto': float(self.tabla.item(row, 3).text().replace('RD$', '').replace(',', '').strip()),
                'concepto': self.tabla.item(row, 4).text(),
                'metodo_pago': self.tabla.item(row, 5).text()
            }
            
            cliente_nombre = self.tabla.item(row, 2).text()
            
            dialogo = DialogoAbono(self.fm, cliente_id, cliente_nombre, abono_datos, parent=self)
            
            if dialogo.exec():
                datos = dialogo.get_datos()
                
                if datos['monto'] <= 0:
                    QMessageBox.warning(self, "Advertencia", "El monto debe ser mayor a 0")
                    return
                
                if self.fm.editar_abono(abono_id, datos):
                    QMessageBox.information(self, "Éxito", "Abono actualizado exitosamente")
                    self._actualizar_tabla()
                    self._actualizar_deuda()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo actualizar el abono")
        
        except Exception as e:
            logger.error(f"Error al editar abono: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al editar abono:\n{str(e)}")
    
    def _eliminar_abono(self):
        """Elimina el abono seleccionado"""
        try:
            row = self.tabla.currentRow()
            if row < 0:
                QMessageBox.warning(self, "Advertencia", "Debe seleccionar un abono para eliminar")
                return
            
            abono_id = self.tabla.item(row, 0).text()
            cliente = self.tabla.item(row, 2).text()
            monto = self.tabla.item(row, 3).text()
            
            respuesta = QMessageBox.question(
                self, "Confirmar eliminación",
                f"¿Está seguro de eliminar este abono?\n\n"
                f"Cliente: {cliente}\n"
                f"Monto: {monto}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if respuesta == QMessageBox.StandardButton.Yes:
                if self.fm.eliminar_abono(abono_id):
                    QMessageBox.information(self, "Éxito", "Abono eliminado exitosamente")
                    self._actualizar_tabla()
                    self._actualizar_deuda()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo eliminar el abono")
        
        except Exception as e:
            logger.error(f"Error al eliminar abono: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al eliminar abono:\n{str(e)}")
