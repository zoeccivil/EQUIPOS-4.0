"""
Diálogo para gestión de equipos en Firebase
Permite crear, editar y eliminar equipos
"""
import logging
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox,
    QLineEdit, QFormLayout, QCheckBox, QLabel, QStyle
)
from PyQt6.QtCore import Qt

from firebase_manager import FirebaseManager

logger = logging.getLogger(__name__)


class GestionEquiposDialog(QDialog):
    """Diálogo para gestionar equipos."""
    
    def __init__(self, firebase_manager: FirebaseManager, parent=None):
        super().__init__(parent)
        
        self.fm = firebase_manager
        self.equipos = []
        
        self.setWindowTitle("Gestión de Equipos")
        self.setMinimumSize(900, 600)
        
        self._init_ui()
        self._cargar_equipos()
    
    def _init_ui(self):
        """Inicializa la interfaz."""
        layout = QVBoxLayout(self)
        
        # Título
        titulo = QLabel("<h2>Gestión de Equipos</h2>")
        layout.addWidget(titulo)
        
        # Botones de acción
        botones_layout = QHBoxLayout()
        
        self.btn_nuevo = QPushButton("➕ Nuevo Equipo")
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
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre", "Modelo", "Activo"])
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
    
    def _cargar_equipos(self):
        """Carga los equipos desde Firebase."""
        try:
            self.equipos = self.fm.obtener_equipos(activo=None)
            self._actualizar_tabla()
        except Exception as e:
            logger.error(f"Error al cargar equipos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al cargar equipos:\n{e}")
    
    def _actualizar_tabla(self):
        """Actualiza la tabla con los equipos."""
        self.tabla.setRowCount(0)
        
        for equipo in self.equipos:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            
            self.tabla.setItem(row, 0, QTableWidgetItem(str(equipo.get('id', ''))))
            self.tabla.setItem(row, 1, QTableWidgetItem(equipo.get('nombre', '')))
            self.tabla.setItem(row, 2, QTableWidgetItem(equipo.get('modelo', '')))
            
            activo = "✅ Activo" if equipo.get('activo', True) else "❌ Inactivo"
            self.tabla.setItem(row, 3, QTableWidgetItem(activo))
    
    def _obtener_seleccionado(self) -> Optional[Dict[str, Any]]:
        """Obtiene el equipo seleccionado."""
        current_row = self.tabla.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Sin Selección", "Debe seleccionar un equipo.")
            return None
        
        equipo_id = self.tabla.item(current_row, 0).text()
        for equipo in self.equipos:
            if str(equipo.get('id')) == equipo_id:
                return equipo
        return None
    
    def _nuevo(self):
        """Crea un nuevo equipo."""
        dialog = FormularioEquipoDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            datos = dialog.get_datos()
            datos['activo'] = True
            
            try:
                nuevo_id = self.fm.agregar_equipo(datos)
                if nuevo_id:
                    QMessageBox.information(self, "Éxito", "Equipo creado correctamente.")
                    self._cargar_equipos()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo crear el equipo.")
            except Exception as e:
                logger.error(f"Error al crear equipo: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Error al crear equipo:\n{e}")
    
    def _editar(self):
        """Edita el equipo seleccionado."""
        equipo = self._obtener_seleccionado()
        if not equipo:
            return
        
        dialog = FormularioEquipoDialog(equipo=equipo, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            datos = dialog.get_datos()
            
            try:
                if self.fm.editar_equipo(equipo['id'], datos):
                    QMessageBox.information(self, "Éxito", "Equipo actualizado correctamente.")
                    self._cargar_equipos()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo actualizar el equipo.")
            except Exception as e:
                logger.error(f"Error al editar equipo: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Error al editar equipo:\n{e}")
    
    def _eliminar(self):
        """Elimina el equipo seleccionado."""
        equipo = self._obtener_seleccionado()
        if not equipo:
            return
        
        respuesta = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar '{equipo.get('nombre')}'?\n\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                if self.fm.eliminar_equipo(equipo['id']):
                    QMessageBox.information(self, "Éxito", "Equipo eliminado correctamente.")
                    self._cargar_equipos()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo eliminar el equipo.")
            except Exception as e:
                logger.error(f"Error al eliminar equipo: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Error al eliminar equipo:\n{e}")
    
    def _toggle_activo(self):
        """Activa o desactiva el equipo seleccionado."""
        equipo = self._obtener_seleccionado()
        if not equipo:
            return
        
        nuevo_estado = not equipo.get('activo', True)
        estado_texto = "activar" if nuevo_estado else "desactivar"
        
        try:
            if self.fm.editar_equipo(equipo['id'], {'activo': nuevo_estado}):
                QMessageBox.information(self, "Éxito", 
                                      f"Equipo {estado_texto}do correctamente.")
                self._cargar_equipos()
            else:
                QMessageBox.critical(self, "Error", 
                                   f"No se pudo {estado_texto} el equipo.")
        except Exception as e:
            logger.error(f"Error al cambiar estado del equipo: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error:\n{e}")


class FormularioEquipoDialog(QDialog):
    """Formulario para crear/editar un equipo."""
    
    def __init__(self, equipo: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        
        self.equipo = equipo
        
        titulo = "Editar Equipo" if equipo else "Nuevo Equipo"
        self.setWindowTitle(titulo)
        self.setMinimumWidth(400)
        
        self._init_ui()
        if equipo:
            self._cargar_datos()
    
    def _init_ui(self):
        """Inicializa la interfaz."""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre del equipo...")
        form_layout.addRow("Nombre:", self.txt_nombre)
        
        self.txt_modelo = QLineEdit()
        self.txt_modelo.setPlaceholderText("Modelo del equipo...")
        form_layout.addRow("Modelo:", self.txt_modelo)
        
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
        """Carga los datos del equipo."""
        if self.equipo:
            self.txt_nombre.setText(self.equipo.get('nombre', ''))
            self.txt_modelo.setText(self.equipo.get('modelo', ''))
    
    def get_datos(self) -> Dict[str, Any]:
        """Obtiene los datos del formulario."""
        return {
            'nombre': self.txt_nombre.text().strip(),
            'modelo': self.txt_modelo.text().strip()
        }
