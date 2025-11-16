import sys
import sqlite3
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QListWidget, QFileDialog, QMessageBox, QListWidgetItem
)
from PyQt6.QtCore import Qt

class CorrectorOperadoresApp(QWidget):
    def __init__(self):
        super().__init__()
        self.db_path = None
        self.setWindowTitle("Herramienta de Corrección de Operador ID")
        self.setMinimumSize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. Selección de Base de Datos
        db_layout = QHBoxLayout()
        self.db_label = QLabel("Base de Datos: (Ninguna seleccionada)")
        db_button = QPushButton("Seleccionar DB")
        db_button.clicked.connect(self.seleccionar_db)
        db_layout.addWidget(self.db_label)
        db_layout.addStretch()
        db_layout.addWidget(db_button)
        layout.addLayout(db_layout)

        # 2. ID Incorrecto
        incorrecto_layout = QHBoxLayout()
        incorrecto_layout.addWidget(QLabel("ID de Operador INCORRECTO:"))
        self.id_incorrecto_input = QLineEdit()
        self.id_incorrecto_input.setPlaceholderText("Ej: 26")
        incorrecto_layout.addWidget(self.id_incorrecto_input)
        layout.addLayout(incorrecto_layout)
        
        # Separador
        layout.addWidget(QLabel("-" * 80))

        # 3. Lista de Operadores Correctos
        layout.addWidget(QLabel("Selecciona el Operador CORRECTO de la lista:"))
        self.operadores_list = QListWidget()
        layout.addWidget(self.operadores_list)

        # 4. Botón de Corrección
        self.corregir_button = QPushButton("Analizar y Corregir IDs")
        self.corregir_button.clicked.connect(self.iniciar_correccion)
        self.corregir_button.setEnabled(False) # Deshabilitado hasta que se seleccione una DB
        layout.addWidget(self.corregir_button)

    def seleccionar_db(self):
        """Abre un diálogo para seleccionar el archivo de la base de datos."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Selecciona tu Base de Datos", "", "Archivos DB (*.db *.sqlite *.sqlite3)"
        )
        if filepath:
            self.db_path = filepath
            self.db_label.setText(f"Base de Datos: ...{self.db_path[-30:]}")
            self.cargar_operadores()
            self.corregir_button.setEnabled(True)

    def cargar_operadores(self):
        """Carga la lista de operadores desde la base de datos."""
        if not self.db_path:
            return
            
        self.operadores_list.clear()
        try:
            conn = sqlite3.connect(self.db_path)
            query = "SELECT id, nombre FROM equipos_entidades WHERE tipo = 'Operador' ORDER BY nombre"
            df_operadores = pd.read_sql_query(query, conn)
            conn.close()

            for _, row in df_operadores.iterrows():
                item_text = f"ID: {row['id']}  |  Nombre: {row['nombre']}"
                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.ItemDataRole.UserRole, row['id']) # Guardamos el ID en el item
                self.operadores_list.addItem(list_item)

        except Exception as e:
            QMessageBox.critical(self, "Error al Cargar", f"No se pudieron cargar los operadores:\n{e}")

    def iniciar_correccion(self):
        """Verifica los datos y comienza el proceso de corrección."""
        id_incorrecto_str = self.id_incorrecto_input.text().strip()
        item_seleccionado = self.operadores_list.currentItem()

        if not id_incorrecto_str:
            QMessageBox.warning(self, "Dato Faltante", "Por favor, introduce el ID incorrecto que deseas cambiar.")
            return
        
        try:
            id_incorrecto = int(id_incorrecto_str)
        except ValueError:
            QMessageBox.warning(self, "Dato Inválido", "El ID incorrecto debe ser un número.")
            return

        if not item_seleccionado:
            QMessageBox.warning(self, "Dato Faltante", "Por favor, selecciona el operador correcto de la lista.")
            return
            
        id_correcto = item_seleccionado.data(Qt.ItemDataRole.UserRole)
        nombre_correcto = item_seleccionado.text().split('|  Nombre: ')[1]

        self.corregir_en_db(id_incorrecto, id_correcto, nombre_correcto)

    def corregir_en_db(self, id_incorrecto, id_correcto, nombre_correcto):
        """Busca, muestra y ejecuta la actualización en la base de datos."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Buscar las transacciones afectadas
            cursor.execute(
                "SELECT id, fecha, descripcion, monto FROM transacciones WHERE operador_id = ?",
                (id_incorrecto,)
            )
            transacciones_afectadas = [dict(row) for row in cursor.fetchall()]

            if not transacciones_afectadas:
                QMessageBox.information(self, "Sin Coincidencias", f"No se encontraron transacciones con el ID de operador '{id_incorrecto}'.")
                conn.close()
                return

            # Mostrar un resumen de los cambios
            mensaje_confirmacion = (
                f"Se encontraron {len(transacciones_afectadas)} transacciones con el ID incorrecto '{id_incorrecto}'.\n\n"
                f"Se actualizarán para que tengan el ID correcto '{id_correcto}' ({nombre_correcto}).\n\n"
                "¿Deseas continuar? Esta acción es irreversible."
            )

            reply = QMessageBox.question(self, 'Confirmar Cambios', mensaje_confirmacion,
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                cursor.execute(
                    "UPDATE transacciones SET operador_id = ? WHERE operador_id = ?",
                    (id_correcto, id_incorrecto)
                )
                conn.commit()
                QMessageBox.information(self, "Éxito", f"¡Se han actualizado {cursor.rowcount} registros correctamente!")

            else:
                QMessageBox.information(self, "Cancelado", "La operación fue cancelada. No se realizó ningún cambio.")
            
            conn.close()

        except Exception as e:
            QMessageBox.critical(self, "Error en Base de Datos", f"Ocurrió un error al actualizar:\n{e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CorrectorOperadoresApp()
    window.show()
    sys.exit(app.exec())