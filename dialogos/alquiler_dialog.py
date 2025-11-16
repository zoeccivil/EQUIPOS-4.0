"""
DialogoAlquiler - Diálogo para crear/editar alquileres en EQUIPOS 4.0
Adaptado para usar Firebase en lugar de SQLite
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QMessageBox, QDateEdit, QDoubleSpinBox, QCheckBox, QFormLayout
)
from PyQt6.QtCore import QDate

from firebase_manager import FirebaseManager

logger = logging.getLogger(__name__)


class AlquilerDialog(QDialog):
    """
    Diálogo para crear o editar un alquiler.
    Adaptado para Firebase (sin proyecto_id, sin cuentas/categorías/subcategorías).
    """
    
    def __init__(
        self,
        firebase_manager: FirebaseManager,
        equipos_mapa: Dict[str, str],
        clientes_mapa: Dict[str, str],
        operadores_mapa: Dict[str, str],
        alquiler_data: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        super().__init__(parent)
        
        self.fm = firebase_manager
        self.equipos_mapa = equipos_mapa  # {id: nombre}
        self.clientes_mapa = clientes_mapa  # {id: nombre}
        self.operadores_mapa = operadores_mapa  # {id: nombre}
        self.alquiler_data = alquiler_data
        self.alquiler_id = alquiler_data.get('id') if alquiler_data else None
        
        self.setWindowTitle("Nuevo Alquiler" if not self.alquiler_id else "Editar Alquiler")
        self.setMinimumWidth(500)
        
        self._init_ui()
        self._cargar_combos()
        
        if self.alquiler_data:
            self._cargar_datos(self.alquiler_data)
    
    def _init_ui(self):
        """Inicializa la interfaz del diálogo."""
        layout = QVBoxLayout(self)
        
        # Formulario principal
        form_layout = QFormLayout()
        
        # Fecha
        self.date_fecha = QDateEdit(calendarPopup=True)
        self.date_fecha.setDisplayFormat("yyyy-MM-dd")
        self.date_fecha.setDate(QDate.currentDate())
        form_layout.addRow("Fecha:", self.date_fecha)
        
        # Cliente
        self.combo_cliente = QComboBox()
        self.combo_cliente.setMinimumWidth(250)
        form_layout.addRow("Cliente:", self.combo_cliente)
        
        # Operador
        self.combo_operador = QComboBox()
        self.combo_operador.setMinimumWidth(250)
        form_layout.addRow("Operador:", self.combo_operador)
        
        # Equipo
        self.combo_equipo = QComboBox()
        self.combo_equipo.setMinimumWidth(250)
        form_layout.addRow("Equipo:", self.combo_equipo)
        
        # Conduce
        self.txt_conduce = QLineEdit()
        form_layout.addRow("Conduce:", self.txt_conduce)
        
        # Ubicación
        self.txt_ubicacion = QLineEdit()
        form_layout.addRow("Ubicación:", self.txt_ubicacion)
        
        # Horas
        self.spin_horas = QDoubleSpinBox()
        self.spin_horas.setRange(0, 1000)
        self.spin_horas.setDecimals(2)
        self.spin_horas.setValue(0)
        self.spin_horas.valueChanged.connect(self._calcular_monto)
        form_layout.addRow("Horas:", self.spin_horas)
        
        # Precio por Hora
        self.spin_precio_hora = QDoubleSpinBox()
        self.spin_precio_hora.setRange(0, 999999)
        self.spin_precio_hora.setDecimals(2)
        self.spin_precio_hora.setValue(0)
        self.spin_precio_hora.valueChanged.connect(self._calcular_monto)
        form_layout.addRow("Precio/Hora:", self.spin_precio_hora)
        
        # Monto (calculado automáticamente)
        self.lbl_monto = QLabel("0.00")
        form_layout.addRow("Monto Total:", self.lbl_monto)
        
        # Estado de pago
        self.chk_pagado = QCheckBox("Pagado")
        form_layout.addRow("", self.chk_pagado)
        
        layout.addLayout(form_layout)
        
        # Botones
        botones_layout = QHBoxLayout()
        
        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.clicked.connect(self._guardar)
        botones_layout.addWidget(self.btn_guardar)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botones_layout.addWidget(btn_cancelar)
        
        layout.addLayout(botones_layout)
    
    def _cargar_combos(self):
        """Carga los datos en los combos desde los mapas."""
        # Cargar Equipos
        self.combo_equipo.clear()
        for eq_id, nombre in sorted(self.equipos_mapa.items(), key=lambda x: x[1]):
            self.combo_equipo.addItem(nombre, eq_id)
        
        # Cargar Clientes
        self.combo_cliente.clear()
        for cl_id, nombre in sorted(self.clientes_mapa.items(), key=lambda x: x[1]):
            self.combo_cliente.addItem(nombre, cl_id)
        
        # Cargar Operadores
        self.combo_operador.clear()
        for op_id, nombre in sorted(self.operadores_mapa.items(), key=lambda x: x[1]):
            self.combo_operador.addItem(nombre, op_id)
    
    def _cargar_datos(self, datos: Dict[str, Any]):
        """Carga los datos del alquiler existente en el formulario."""
        try:
            # Fecha
            fecha_str = datos.get('fecha', '')
            if fecha_str:
                self.date_fecha.setDate(QDate.fromString(fecha_str, "yyyy-MM-dd"))
            
            # Cliente
            cliente_id = str(int(datos.get('cliente_id', 0)))
            idx = self.combo_cliente.findData(cliente_id)
            if idx >= 0:
                self.combo_cliente.setCurrentIndex(idx)
            
            # Operador
            operador_id = str(int(datos.get('operador_id', 0)))
            idx = self.combo_operador.findData(operador_id)
            if idx >= 0:
                self.combo_operador.setCurrentIndex(idx)
            
            # Equipo
            equipo_id = str(int(datos.get('equipo_id', 0)))
            idx = self.combo_equipo.findData(equipo_id)
            if idx >= 0:
                self.combo_equipo.setCurrentIndex(idx)
            
            # Conduce
            self.txt_conduce.setText(datos.get('conduce', ''))
            
            # Ubicación
            self.txt_ubicacion.setText(datos.get('ubicacion', ''))
            
            # Horas
            horas = float(datos.get('horas', 0))
            self.spin_horas.setValue(horas)
            
            # Precio por Hora
            precio_hora = float(datos.get('precio_por_hora', 0))
            self.spin_precio_hora.setValue(precio_hora)
            
            # Pagado
            pagado = datos.get('pagado', False)
            self.chk_pagado.setChecked(pagado)
            
            # Calcular monto
            self._calcular_monto()
            
        except Exception as e:
            logger.error(f"Error al cargar datos del alquiler: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Error al cargar datos: {e}")
    
    def _calcular_monto(self):
        """Calcula el monto total basado en horas y precio por hora."""
        try:
            horas = self.spin_horas.value()
            precio_hora = self.spin_precio_hora.value()
            monto = horas * precio_hora
            self.lbl_monto.setText(f"{monto:,.2f}")
        except Exception as e:
            logger.error(f"Error al calcular monto: {e}")
            self.lbl_monto.setText("0.00")
    
    def _validar_datos(self) -> bool:
        """Valida los datos del formulario."""
        # Validar que se haya seleccionado un cliente
        if self.combo_cliente.currentIndex() < 0:
            QMessageBox.warning(self, "Error de Validación", "Debe seleccionar un cliente.")
            self.combo_cliente.setFocus()
            return False
        
        # Validar que se haya seleccionado un operador
        if self.combo_operador.currentIndex() < 0:
            QMessageBox.warning(self, "Error de Validación", "Debe seleccionar un operador.")
            self.combo_operador.setFocus()
            return False
        
        # Validar que se haya seleccionado un equipo
        if self.combo_equipo.currentIndex() < 0:
            QMessageBox.warning(self, "Error de Validación", "Debe seleccionar un equipo.")
            self.combo_equipo.setFocus()
            return False
        
        # Validar horas > 0
        if self.spin_horas.value() <= 0:
            QMessageBox.warning(self, "Error de Validación", "Las horas deben ser mayores a 0.")
            self.spin_horas.setFocus()
            return False
        
        # Validar precio por hora > 0
        if self.spin_precio_hora.value() <= 0:
            QMessageBox.warning(self, "Error de Validación", "El precio por hora debe ser mayor a 0.")
            self.spin_precio_hora.setFocus()
            return False
        
        return True
    
    def _obtener_datos(self) -> Dict[str, Any]:
        """Obtiene los datos del formulario."""
        # Calcular monto
        horas = self.spin_horas.value()
        precio_hora = self.spin_precio_hora.value()
        monto = horas * precio_hora
        
        datos = {
            'fecha': self.date_fecha.date().toString("yyyy-MM-dd"),
            'cliente_id': self.combo_cliente.currentData(),
            'operador_id': self.combo_operador.currentData(),
            'equipo_id': self.combo_equipo.currentData(),
            'conduce': self.txt_conduce.text().strip(),
            'ubicacion': self.txt_ubicacion.text().strip(),
            'horas': horas,
            'precio_por_hora': precio_hora,
            'monto': monto,
            'pagado': self.chk_pagado.isChecked()
        }
        
        return datos
    
    def _guardar(self):
        """Guarda el alquiler en Firebase."""
        if not self._validar_datos():
            return
        
        try:
            datos = self._obtener_datos()
            
            # Modo creación
            if not self.alquiler_id:
                alquiler_id = self.fm.registrar_alquiler(datos)
                if alquiler_id:
                    QMessageBox.information(self, "Éxito", "Alquiler registrado correctamente.")
                    logger.info(f"Alquiler creado con ID: {alquiler_id}")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo registrar el alquiler.")
            
            # Modo edición
            else:
                if self.fm.editar_alquiler(self.alquiler_id, datos):
                    QMessageBox.information(self, "Éxito", "Alquiler actualizado correctamente.")
                    logger.info(f"Alquiler {self.alquiler_id} actualizado")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo actualizar el alquiler.")
        
        except Exception as e:
            logger.error(f"Error al guardar alquiler: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al guardar el alquiler:\n{e}")
