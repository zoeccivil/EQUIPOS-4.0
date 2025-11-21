"""
Diálogo genérico para gestión de entidades (Clientes, Operadores, Equipos)
Permite crear, editar y eliminar entidades en Firebase
"""
import logging
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox,
    QLineEdit, QFormLayout, QCheckBox, QLabel, QStyle, QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from firebase_manager import FirebaseManager

logger = logging.getLogger(__name__)


class GestionEntidadDialog(QDialog):
    """
    Diálogo para gestionar entidades (Clientes, Operadores) en Firebase.
    """
    
    def __init__(self, firebase_manager: FirebaseManager, tipo_entidad: str, parent=None):
        """
        Args:
            firebase_manager: Instancia de FirebaseManager
            tipo_entidad: 'Cliente' u 'Operador'
        """
        super().__init__(parent)
        
        self.fm = firebase_manager
        self.tipo = tipo_entidad  # 'Cliente' u 'Operador'
        self.entidades = []
        
        self.setWindowTitle(f"Gestión de {self.tipo}s")
        self.setMinimumSize(800, 600)
        
        self._init_ui()
        self._cargar_entidades()
    
    def _init_ui(self):
        """Inicializa la interfaz del diálogo."""
        layout = QVBoxLayout(self)
        
        # Título
        titulo = QLabel(f"<h2>Gestión de {self.tipo}s</h2>")
        layout.addWidget(titulo)
        
        # Botones de acción
        botones_layout = QHBoxLayout()
        
        self.btn_nuevo = QPushButton(f"➕ Nuevo {self.tipo}")
        icon_new = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder)
        self.btn_nuevo.setIcon(icon_new)
        self.btn_nuevo.clicked.connect(self._nuevo)
        botones_layout.addWidget(self.btn_nuevo)
        
        self.btn_editar = QPushButton("✏️ Editar")
        icon_edit = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        self.btn_editar.setIcon(icon_edit)
        self.btn_editar.clicked.connect(self._editar)
        botones_layout.addWidget(self.btn_editar)
        
        self.btn_eliminar = QPushButton("🗑️ Eliminar")
        icon_delete = self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        self.btn_eliminar.setIcon(icon_delete)
        self.btn_eliminar.clicked.connect(self._eliminar)
        botones_layout.addWidget(self.btn_eliminar)
        
        self.btn_activar_desactivar = QPushButton("🔄 Activar/Desactivar")
        self.btn_activar_desactivar.clicked.connect(self._toggle_activo)
        botones_layout.addWidget(self.btn_activar_desactivar)
        
        botones_layout.addStretch()
        layout.addLayout(botones_layout)
        
        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre", "Contacto", "Activo"])
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.itemDoubleClicked.connect(self._editar)
        layout.addWidget(self.tabla)
        
        # Botón cerrar
        btn_cerrar = QPushButton("✖️ Cerrar")
        icon_close = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton)
        btn_cerrar.setIcon(icon_close)
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)
    
    def _cargar_entidades(self):
        """Carga las entidades desde Firebase."""
        try:
            self.entidades = self.fm.obtener_entidades(tipo=self.tipo, activo=None)
            self._actualizar_tabla()
        except Exception as e:
            logger.error(f"Error al cargar {self.tipo}s: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al cargar {self.tipo}s:\n{e}")
    
    def _actualizar_tabla(self):
        """Actualiza la tabla con las entidades."""
        self.tabla.setRowCount(0)
        
        for entidad in self.entidades:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            
            self.tabla.setItem(row, 0, QTableWidgetItem(str(entidad.get('id', ''))))
            self.tabla.setItem(row, 1, QTableWidgetItem(entidad.get('nombre', '')))
            self.tabla.setItem(row, 2, QTableWidgetItem(entidad.get('contacto', '')))
            
            activo = "✅ Activo" if entidad.get('activo', True) else "❌ Inactivo"
            self.tabla.setItem(row, 3, QTableWidgetItem(activo))
    
    def _obtener_seleccionado(self) -> Optional[Dict[str, Any]]:
        """Obtiene la entidad seleccionada."""
        current_row = self.tabla.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Sin Selección", f"Debe seleccionar un {self.tipo}.")
            return None
        
        entidad_id = self.tabla.item(current_row, 0).text()
        for entidad in self.entidades:
            if str(entidad.get('id')) == entidad_id:
                return entidad
        return None
    
    def _nuevo(self):
        """Crea una nueva entidad."""
        dialog = FormularioEntidadDialog(self.tipo, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            datos = dialog.get_datos()
            datos['tipo'] = self.tipo
            datos['activo'] = True
            
            try:
                nuevo_id = self.fm.agregar_entidad(datos)
                if nuevo_id:
                    QMessageBox.information(self, "Éxito", f"{self.tipo} creado correctamente.")
                    self._cargar_entidades()
                else:
                    QMessageBox.critical(self, "Error", f"No se pudo crear el {self.tipo}.")
            except Exception as e:
                logger.error(f"Error al crear {self.tipo}: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Error al crear {self.tipo}:\n{e}")
    
    def _editar(self):
        """Edita la entidad seleccionada."""
        entidad = self._obtener_seleccionado()
        if not entidad:
            return
        
        dialog = FormularioEntidadDialog(self.tipo, entidad=entidad, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            datos = dialog.get_datos()
            
            try:
                if self.fm.editar_entidad(entidad['id'], datos):
                    QMessageBox.information(self, "Éxito", f"{self.tipo} actualizado correctamente.")
                    self._cargar_entidades()
                else:
                    QMessageBox.critical(self, "Error", f"No se pudo actualizar el {self.tipo}.")
            except Exception as e:
                logger.error(f"Error al editar {self.tipo}: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Error al editar {self.tipo}:\n{e}")
    
    def _eliminar(self):
        """Elimina la entidad seleccionada."""
        entidad = self._obtener_seleccionado()
        if not entidad:
            return
        
        respuesta = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar '{entidad.get('nombre')}'?\n\n"
            f"Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                if self.fm.eliminar_entidad(entidad['id']):
                    QMessageBox.information(self, "Éxito", f"{self.tipo} eliminado correctamente.")
                    self._cargar_entidades()
                else:
                    QMessageBox.critical(self, "Error", f"No se pudo eliminar el {self.tipo}.")
            except Exception as e:
                logger.error(f"Error al eliminar {self.tipo}: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Error al eliminar {self.tipo}:\n{e}")
    
    def _toggle_activo(self):
        """Activa o desactiva la entidad seleccionada."""
        entidad = self._obtener_seleccionado()
        if not entidad:
            return
        
        nuevo_estado = not entidad.get('activo', True)
        estado_texto = "activar" if nuevo_estado else "desactivar"
        
        try:
            if self.fm.editar_entidad(entidad['id'], {'activo': nuevo_estado}):
                QMessageBox.information(self, "Éxito", 
                                      f"{self.tipo} {estado_texto}do correctamente.")
                self._cargar_entidades()
            else:
                QMessageBox.critical(self, "Error", 
                                   f"No se pudo {estado_texto} el {self.tipo}.")
        except Exception as e:
            logger.error(f"Error al cambiar estado de {self.tipo}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error:\n{e}")


class FormularioEntidadDialog(QDialog):
    """Formulario para crear/editar una entidad."""
    
    def __init__(self, tipo: str, entidad: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        
        self.tipo = tipo
        self.entidad = entidad
        
        titulo = "Editar" if entidad else "Nuevo"
        self.setWindowTitle(f"{titulo} {tipo}")
        self.setMinimumWidth(400)
        
        self._init_ui()
        if entidad:
            self._cargar_datos()
    
    def _init_ui(self):
        """Inicializa la interfaz."""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText(f"Nombre del {self.tipo}...")
        form_layout.addRow("Nombre:", self.txt_nombre)
        
        self.txt_contacto = QLineEdit()
        self.txt_contacto.setPlaceholderText("Teléfono, email, etc...")
        form_layout.addRow("Contacto:", self.txt_contacto)
        
        layout.addLayout(form_layout)
        
        # Botones
        botones_layout = QHBoxLayout()
        
        btn_guardar = QPushButton("💾 Guardar")
        btn_guardar.clicked.connect(self.accept)
        botones_layout.addWidget(btn_guardar)
        
        btn_cancelar = QPushButton("✖️ Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botones_layout.addWidget(btn_cancelar)
        
        layout.addLayout(botones_layout)
    
    def _cargar_datos(self):
        """Carga los datos de la entidad."""
        if self.entidad:
            self.txt_nombre.setText(self.entidad.get('nombre', ''))
            self.txt_contacto.setText(self.entidad.get('contacto', ''))
    
    def get_datos(self) -> Dict[str, Any]:
        """Obtiene los datos del formulario."""
        return {
            'nombre': self.txt_nombre.text().strip(),
            'contacto': self.txt_contacto.text().strip()
        }
