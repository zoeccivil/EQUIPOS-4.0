"""
Diálogo para generar estado de cuenta de clientes
Adaptado para trabajar con Firebase/Firestore
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QDateEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import QDate
import logging

logger = logging.getLogger(__name__)


class EstadoCuentaDialog(QDialog):
    """Diálogo para seleccionar cliente y rango de fechas para estado de cuenta"""
    
    def __init__(self, firebase_manager, mapas, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generar Estado de Cuenta")
        self.setMinimumWidth(500)
        self.fm = firebase_manager
        self.mapas = mapas  # Diccionario con clientes_mapa, equipos_mapa, etc.
        
        self._crear_interfaz()
        self._actualizar_rango_fechas()
    
    def _crear_interfaz(self):
        """Crea la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        
        # --- Cliente ---
        cliente_layout = QHBoxLayout()
        cliente_layout.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        
        # Agregar opción "Todos"
        self.combo_cliente.addItem("Todos", None)
        
        # Agregar clientes desde el mapa
        if 'clientes_mapa' in self.mapas:
            for nombre, cliente_id in self.mapas['clientes_mapa'].items():
                self.combo_cliente.addItem(nombre, cliente_id)
        
        cliente_layout.addWidget(self.combo_cliente)
        layout.addLayout(cliente_layout)
        
        # --- Fechas ---
        fechas_layout = QHBoxLayout()
        fechas_layout.addWidget(QLabel("Desde:"))
        self.fecha_inicio = QDateEdit(calendarPopup=True)
        self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
        fechas_layout.addWidget(self.fecha_inicio)
        
        fechas_layout.addWidget(QLabel("Hasta:"))
        self.fecha_fin = QDateEdit(calendarPopup=True)
        self.fecha_fin.setDate(QDate.currentDate())
        fechas_layout.addWidget(self.fecha_fin)
        
        layout.addLayout(fechas_layout)
        
        # --- Botones ---
        btn_layout = QHBoxLayout()
        btn_aceptar = QPushButton("💾 Generar Reporte")
        btn_aceptar.clicked.connect(self.accept)
        btn_cancelar = QPushButton("✖️ Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_aceptar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        # Conectar señal para actualizar fechas al cambiar cliente
        self.combo_cliente.currentIndexChanged.connect(self._actualizar_rango_fechas)
    
    def _actualizar_rango_fechas(self):
        """Actualiza el rango de fechas basado en el cliente seleccionado"""
        cliente_id = self.combo_cliente.currentData()
        
        try:
            if cliente_id is None:
                # "Todos" seleccionado - usar primera transacción general
                fecha_str = self.fm.obtener_fecha_primera_transaccion_alquileres()
            else:
                # Cliente específico
                fecha_str = self.fm.obtener_fecha_primera_transaccion_cliente(cliente_id)
            
            if fecha_str:
                self.fecha_inicio.setDate(QDate.fromString(fecha_str, "yyyy-MM-dd"))
            else:
                # Si no hay datos, usar mes anterior
                self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
            
            # Fecha fin siempre es hoy
            self.fecha_fin.setDate(QDate.currentDate())
            
        except Exception as e:
            logger.error(f"Error al actualizar rango de fechas: {e}", exc_info=True)
            # Fallback a fechas por defecto
            self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
            self.fecha_fin.setDate(QDate.currentDate())
    
    def get_filtros(self):
        """
        Retorna los filtros seleccionados.
        
        Returns:
            dict con 'cliente_nombre', 'cliente_id', 'fecha_inicio', 'fecha_fin'
        """
        return {
            'cliente_nombre': self.combo_cliente.currentText(),
            'cliente_id': self.combo_cliente.currentData(),  # None para "Todos"
            'fecha_inicio': self.fecha_inicio.date().toString("yyyy-MM-dd"),
            'fecha_fin': self.fecha_fin.date().toString("yyyy-MM-dd")
        }
