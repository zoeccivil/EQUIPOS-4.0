"""
VentanaGestionEntidad - Gestión de Clientes y Operadores con todos los campos visibles.

Correcciones aplicadas:
- Ahora muestra telefono y cedula correctamente desde la BD.
- Manejo robusto de valores NULL.
- Refresh automático después de guardar/editar/eliminar.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QTableWidget,
    QTableWidgetItem, QMessageBox, QHeaderView, QComboBox
)


class VentanaGestionEntidad(QDialog):
    """
    Ventana para gestionar entidades (Clientes u Operadores) de un proyecto.
    """
    def __init__(self, db, proyecto_actual, tipo_entidad, parent=None):
        super().__init__(parent)
        self.db = db
        self.proyecto_actual = proyecto_actual
        self.tipo_entidad = tipo_entidad  # "Cliente" o "Operador"
        self.setWindowTitle(f"Gestión de {tipo_entidad}s")
        self.resize(750, 500)

        layout = QVBoxLayout(self)

        # Tabla con 5 columnas: ID (oculto), Nombre, Teléfono, Cédula/RNC, Estado
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Teléfono", "Cédula/RNC", "Estado"])
        
        # Ocultar columna ID (la usamos internamente pero no la mostramos)
        self.table.setColumnHidden(0, True)
        
        # Ajustar ancho de columnas
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Nombre se expande
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Teléfono
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Cédula
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Estado
        
        layout.addWidget(self.table)

        # Botones
        btns = QHBoxLayout()
        btn_agregar = QPushButton("Agregar")
        btn_editar = QPushButton("Editar")
        btn_eliminar = QPushButton("Eliminar")
        btn_cerrar = QPushButton("Cerrar")
        btns.addWidget(btn_agregar)
        btns.addWidget(btn_editar)
        btns.addWidget(btn_eliminar)
        btns.addStretch()
        btns.addWidget(btn_cerrar)
        layout.addLayout(btns)

        # Conexiones
        btn_agregar.clicked.connect(self.agregar)
        btn_editar.clicked.connect(self.editar)
        btn_eliminar.clicked.connect(self.eliminar)
        btn_cerrar.clicked.connect(self.accept)

        # Cargar datos inicial
        self.refrescar()

    def refrescar(self):
        """Recarga la tabla de entidades desde la base de datos."""
        self.table.setRowCount(0)
        try:
            # Obtener todas las entidades del tipo especificado
            entidades = self.db.obtener_entidades_equipo_por_tipo(
                self.proyecto_actual['id'], 
                self.tipo_entidad
            )
            
            for entidad in entidades:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Columna 0: ID (oculta pero necesaria para editar/eliminar)
                id_item = QTableWidgetItem(str(entidad.get('id', '')))
                self.table.setItem(row, 0, id_item)
                
                # Columna 1: Nombre
                nombre_item = QTableWidgetItem(str(entidad.get('nombre', '')))
                self.table.setItem(row, 1, nombre_item)
                
                # Columna 2: Teléfono (mostrar vacío si es NULL)
                telefono = entidad.get('telefono', '')
                telefono_texto = str(telefono) if telefono and telefono != 'None' else ""
                telefono_item = QTableWidgetItem(telefono_texto)
                self.table.setItem(row, 2, telefono_item)
                
                # Columna 3: Cédula/RNC (mostrar vacío si es NULL)
                cedula = entidad.get('cedula', '')
                cedula_texto = str(cedula) if cedula and cedula != 'None' else ""
                cedula_item = QTableWidgetItem(cedula_texto)
                self.table.setItem(row, 3, cedula_item)
                
                # Columna 4: Estado
                estado = "Activo" if entidad.get('activo', 1) else "Inactivo"
                estado_item = QTableWidgetItem(estado)
                self.table.setItem(row, 4, estado_item)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la lista de {self.tipo_entidad}s:\n{e}")

    def agregar(self):
        """Abre el diálogo para agregar una nueva entidad."""
        dlg = DialogoEntidad(self.db, self.proyecto_actual, self.tipo_entidad, parent=self)
        if dlg.exec():
            self.refrescar()

    def editar(self):
        """Abre el diálogo para editar la entidad seleccionada."""
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Selección requerida", 
                              f"Selecciona un {self.tipo_entidad.lower()} para editar.")
            return
        
        # Obtener ID desde la columna oculta
        entidad_id = int(self.table.item(selected, 0).text())
        
        try:
            # Obtener datos completos desde la BD por ID
            entidad = self.db.obtener_entidad_por_id(entidad_id)
            if not entidad:
                QMessageBox.warning(self, "Error", f"No se encontró el {self.tipo_entidad.lower()}.")
                return
            
            dlg = DialogoEntidad(self.db, self.proyecto_actual, self.tipo_entidad, entidad, parent=self)
            if dlg.exec():
                self.refrescar()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo editar:\n{e}")

    def eliminar(self):
        """Elimina (marca como inactiva) la entidad seleccionada."""
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Selección requerida", 
                              f"Selecciona un {self.tipo_entidad.lower()} para eliminar.")
            return
        
        # Obtener nombre e ID
        nombre = self.table.item(selected, 1).text()
        entidad_id = int(self.table.item(selected, 0).text())
        
        try:
            confirm = QMessageBox.question(
                self, 
                "Confirmar", 
                f"¿Eliminar a '{nombre}'?\n\nEsta acción marcará el registro como inactivo.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.Yes:
                exito = self.db.eliminar_entidad(entidad_id)
                if exito:
                    QMessageBox.information(self, "Éxito", f"{self.tipo_entidad} eliminado correctamente.")
                    self.refrescar()
                else:
                    QMessageBox.warning(self, "Error", f"No se pudo eliminar el {self.tipo_entidad.lower()}.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar:\n{e}")


class DialogoEntidad(QDialog):
    """
    Diálogo modal para crear o editar una entidad (Cliente u Operador).
    """
    def __init__(self, db, proyecto_actual, tipo_entidad, datos=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.proyecto_actual = proyecto_actual
        self.tipo_entidad = tipo_entidad
        self.datos = datos
        
        titulo = f"Editar {tipo_entidad}" if datos else f"Nuevo {tipo_entidad}"
        self.setWindowTitle(titulo)
        self.resize(450, 280)
        
        layout = QVBoxLayout(self)

        # Campos del formulario
        self.edit_nombre = QLineEdit()
        self.edit_telefono = QLineEdit()
        self.edit_cedula = QLineEdit()
        self.combo_estado = QComboBox()
        self.combo_estado.addItems(["Activo", "Inactivo"])
        
        # Rellenar con datos existentes si es edición
        if datos:
            self.edit_nombre.setText(str(datos.get('nombre', '')))
            
            telefono = datos.get('telefono')
            if telefono and str(telefono) != 'None':
                self.edit_telefono.setText(str(telefono))
            
            cedula = datos.get('cedula')
            if cedula and str(cedula) != 'None':
                self.edit_cedula.setText(str(cedula))
            
            if not datos.get("activo", 1):
                self.combo_estado.setCurrentIndex(1)

        layout.addWidget(QLabel("Nombre: *"))
        layout.addWidget(self.edit_nombre)
        layout.addWidget(QLabel("Teléfono:"))
        layout.addWidget(self.edit_telefono)
        layout.addWidget(QLabel("Cédula/RNC:"))
        layout.addWidget(self.edit_cedula)
        layout.addWidget(QLabel("Estado:"))
        layout.addWidget(self.combo_estado)

        # Botones
        btns = QHBoxLayout()
        btn_guardar = QPushButton("Guardar")
        btn_cancelar = QPushButton("Cancelar")
        btns.addStretch()
        btns.addWidget(btn_guardar)
        btns.addWidget(btn_cancelar)
        layout.addLayout(btns)

        btn_guardar.clicked.connect(self.guardar)
        btn_cancelar.clicked.connect(self.reject)

    def guardar(self):
        """Valida y guarda la entidad en la base de datos."""
        nombre = self.edit_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
            return
        
        # Preparar teléfono y cédula (None si están vacíos)
        telefono = self.edit_telefono.text().strip()
        cedula = self.edit_cedula.text().strip()
        
        datos = {
            "proyecto_id": self.proyecto_actual['id'],
            "tipo": self.tipo_entidad,
            "nombre": nombre,
            "telefono": telefono if telefono else None,
            "cedula": cedula if cedula else None,
            "activo": 1 if self.combo_estado.currentText() == "Activo" else 0
        }
        
        entidad_id = self.datos.get('id') if self.datos else None
        
        try:
            resultado = self.db.guardar_entidad(datos, entidad_id)
            if resultado:
                accion = "actualizado" if entidad_id else "creado"
                QMessageBox.information(self, "Éxito", f"{self.tipo_entidad} {accion} correctamente.")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", 
                                  f"No se pudo guardar el {self.tipo_entidad.lower()}.\n"
                                  "Verifica que el nombre no esté duplicado.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{e}")