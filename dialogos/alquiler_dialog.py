"""
DialogoAlquiler - Diálogo para crear/editar alquileres en EQUIPOS 4.0
Adaptado para usar Firebase en lugar de SQLite
Incluye funcionalidad de adjuntar conduces con Firebase Storage
Integra MiniEditorImagen para editar conduces antes de subir
"""
import logging
import os
import uuid
import tempfile
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QMessageBox, QDateEdit, QDoubleSpinBox, QCheckBox, QFormLayout,
    QFileDialog, QGroupBox, QStyle
)
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QIcon

from firebase_manager import FirebaseManager
from storage_manager import StorageManager
from mini_editor_imagen import MiniEditorImagen

logger = logging.getLogger(__name__)


def crear_archivo_temporal_conduce(prefijo: str = "conduce_editado", sufijo: str = ".jpeg") -> str:
    """
    Crea un archivo temporal multiplataforma para guardar un conduce editado.
    
    Args:
        prefijo: Prefijo del nombre del archivo temporal
        sufijo: Extensión del archivo (debe incluir el punto, ej: ".jpeg")
    
    Returns:
        Ruta completa al archivo temporal creado
        
    Nota:
        Esta función encapsula la lógica de creación de archivos temporales,
        asegurando compatibilidad entre Windows, Linux y macOS.
    """
    try:
        # Crear archivo temporal con nombre único
        temp_fd, temp_path = tempfile.mkstemp(suffix=sufijo, prefix=f"{prefijo}_")
        # Cerrar el descriptor de archivo (solo necesitamos la ruta)
        os.close(temp_fd)
        logger.info(f"Archivo temporal creado: {temp_path}")
        return temp_path
    except Exception as e:
        logger.error(f"Error al crear archivo temporal: {e}", exc_info=True)
        raise


class AlquilerDialog(QDialog):
    """
    Diálogo para crear o editar un alquiler.
    Adaptado para Firebase (sin proyecto_id, sin cuentas/categorías/subcategorías).
    Incluye adjuntar conduces mediante Firebase Storage.
    """
    
    def __init__(
        self,
        firebase_manager: FirebaseManager,
        storage_manager: Optional[StorageManager],
        equipos_mapa: Dict[str, str],
        clientes_mapa: Dict[str, str],
        operadores_mapa: Dict[str, str],
        alquiler_data: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        super().__init__(parent)
        
        self.fm = firebase_manager
        self.sm = storage_manager  # Puede ser None si Storage no está configurado
        self.equipos_mapa = equipos_mapa  # {id: nombre}
        self.clientes_mapa = clientes_mapa  # {id: nombre}
        self.operadores_mapa = operadores_mapa  # {id: nombre}
        self.alquiler_data = alquiler_data
        self.alquiler_id = alquiler_data.get('id') if alquiler_data else None
        
        # Variables para manejo de conduce
        self.conduce_archivo_seleccionado = None
        self.conduce_url = None
        self.conduce_storage_path = None
        
        self.setWindowTitle("Nuevo Alquiler" if not self.alquiler_id else "Editar Alquiler")
        self.setMinimumWidth(600)
        
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
        
        # Sección de conduce (si Storage está disponible)
        if self.sm:
            conduce_group = QGroupBox("Conduce")
            conduce_layout = QVBoxLayout()
            
            # Label de estado
            self.lbl_conduce_estado = QLabel("Sin archivo adjunto")
            conduce_layout.addWidget(self.lbl_conduce_estado)
            
            # Botones
            btns_conduce_layout = QHBoxLayout()
            
            self.btn_seleccionar_conduce = QPushButton("📎 Adjuntar Conduce")
            icon_open = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
            self.btn_seleccionar_conduce.setIcon(icon_open)
            self.btn_seleccionar_conduce.clicked.connect(self._seleccionar_conduce)
            btns_conduce_layout.addWidget(self.btn_seleccionar_conduce)
            
            self.btn_ver_conduce = QPushButton("👁️ Ver Conduce")
            icon_view = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
            self.btn_ver_conduce.setIcon(icon_view)
            self.btn_ver_conduce.clicked.connect(self._ver_conduce)
            self.btn_ver_conduce.setEnabled(False)
            btns_conduce_layout.addWidget(self.btn_ver_conduce)
            
            self.btn_eliminar_conduce = QPushButton("🗑️ Eliminar")
            icon_delete = self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
            self.btn_eliminar_conduce.setIcon(icon_delete)
            self.btn_eliminar_conduce.clicked.connect(self._eliminar_conduce)
            self.btn_eliminar_conduce.setEnabled(False)
            btns_conduce_layout.addWidget(self.btn_eliminar_conduce)
            
            btns_conduce_layout.addStretch()
            conduce_layout.addLayout(btns_conduce_layout)
            
            conduce_group.setLayout(conduce_layout)
            layout.addWidget(conduce_group)
        
        # Botones principales
        botones_layout = QHBoxLayout()
        
        self.btn_guardar = QPushButton("💾 Guardar")
        icon_save = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        self.btn_guardar.setIcon(icon_save)
        self.btn_guardar.clicked.connect(self._guardar)
        botones_layout.addWidget(self.btn_guardar)
        
        btn_cancelar = QPushButton("✖️ Cancelar")
        icon_cancel = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
        btn_cancelar.setIcon(icon_cancel)
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
            
            # Conduce (Storage)
            if self.sm:
                self.conduce_url = datos.get('conduce_url')
                self.conduce_storage_path = datos.get('conduce_storage_path')
                if self.conduce_url:
                    self.lbl_conduce_estado.setText(f"Archivo adjunto: {os.path.basename(self.conduce_storage_path or 'conduce')}")
                    self.btn_ver_conduce.setEnabled(True)
                    self.btn_eliminar_conduce.setEnabled(True)
            
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
        
        # Agregar datos del conduce si existen
        if self.conduce_url:
            datos['conduce_url'] = self.conduce_url
        if self.conduce_storage_path:
            datos['conduce_storage_path'] = self.conduce_storage_path
        
        return datos
    
    def _guardar(self):
        """Guarda el alquiler en Firebase."""
        if not self._validar_datos():
            return
        
        try:
            datos = self._obtener_datos()
            
            # Subir conduce si hay uno seleccionado
            if self.conduce_archivo_seleccionado and self.sm:
                logger.info(f"Iniciando subida de conduce: {self.conduce_archivo_seleccionado}")
                
                # Validar que el archivo existe antes de intentar subirlo
                if not os.path.exists(self.conduce_archivo_seleccionado):
                    logger.error(f"Archivo de conduce no existe: {self.conduce_archivo_seleccionado}")
                    QMessageBox.warning(
                        self,
                        "Advertencia",
                        "El archivo de conduce seleccionado no existe o no es accesible.\n"
                        "El alquiler se guardará sin conduce adjunto."
                    )
                else:
                    # Preparar datos temporales para el storage
                    temp_alquiler = {
                        'fecha': datos['fecha'],
                        'conduce': datos['conduce'],
                        'id': self.alquiler_id or 'temp'
                    }
                    
                    exito, url, storage_path, error_msg = self.sm.guardar_conduce(
                        self.conduce_archivo_seleccionado,
                        temp_alquiler,
                        procesar_imagen=True
                    )
                    
                    if exito:
                        datos['conduce_url'] = url
                        datos['conduce_storage_path'] = storage_path
                        logger.info(f"Conduce subido exitosamente: {storage_path} -> {url}")
                    else:
                        base_msg = "No se pudo subir el conduce. El alquiler se guardará sin conduce adjunto."
                        logger.error(base_msg)
                        logger.error(f"Detalles del error: {error_msg}")
                        
                        # Mostrar el error específico al usuario
                        detailed_msg = f"{base_msg}\n\n"
                        
                        if error_msg:
                            detailed_msg += f"Error específico:\n{error_msg}\n\n"
                        
                        detailed_msg += (
                            "Posibles causas:\n"
                            "• Permisos de Firebase Storage no configurados (error 403)\n"
                            "• Credenciales sin permisos suficientes\n"
                            "• Bucket no existe o nombre incorrecto (error 404)\n"
                            "• Problema de conexión a Internet\n\n"
                            "Ver docs/solucion_error_subida_conduce.md para más ayuda."
                        )
                        
                        QMessageBox.warning(
                            self,
                            "Advertencia",
                            detailed_msg
                        )
            
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
    
    def _seleccionar_conduce(self):
        """Permite seleccionar un archivo de conduce y editarlo."""
        if not self.sm:
            QMessageBox.warning(self, "No disponible", "Firebase Storage no está configurado.")
            return
        
        archivo, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Conduce",
            "",
            "Imágenes y PDFs (*.jpg *.jpeg *.png *.pdf);;Todos los archivos (*)"
        )
        
        if not archivo:
            return
        
        nombre_archivo = os.path.basename(archivo)
        
        # Si es imagen, verificar tamaño y abrir editor
        if archivo.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
            try:
                # Verificar tamaño del archivo
                file_size_mb = os.path.getsize(archivo) / (1024 * 1024)
                logger.info(f"Abriendo editor de imagen para: {archivo} ({file_size_mb:.2f} MB)")
                
                # Si el archivo es muy grande (>5MB), mostrar advertencia
                if file_size_mb > 5:
                    reply = QMessageBox.question(
                        self,
                        "Archivo Grande",
                        f"El archivo seleccionado es grande ({file_size_mb:.1f} MB).\n\n"
                        "El editor lo optimizará automáticamente para reducir el tamaño.\n"
                        "Esto puede tardar unos segundos.\n\n"
                        "¿Desea continuar?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return
                
                editor = MiniEditorImagen(archivo, width=1200, height=800, parent=self)
                
                if editor.exec() != QDialog.DialogCode.Accepted:
                    logger.info("Usuario canceló el editor de imagen")
                    return
                
                # Obtener imagen editada
                img_editada = editor.get_final_image()
                
                if img_editada is None:
                    logger.warning("El editor no retornó imagen válida, usando archivo original")
                    self.conduce_archivo_seleccionado = archivo
                    self.lbl_conduce_estado.setText(f"Seleccionado: {nombre_archivo}")
                    return
                
                # Crear archivo temporal multiplataforma
                try:
                    temp_path = crear_archivo_temporal_conduce(prefijo="conduce_editado", sufijo=".jpeg")
                    
                    # Determinar calidad basada en el tamaño de la imagen
                    # Para imágenes grandes, usar calidad más baja para reducir tamaño
                    if hasattr(img_editada, 'size'):
                        width, height = img_editada.size
                        pixels = width * height
                        # Más de 1 megapixel -> calidad 75, más de 2 -> calidad 70, etc.
                        if pixels > 2000000:
                            quality = 65
                        elif pixels > 1000000:
                            quality = 75
                        else:
                            quality = 85
                        logger.info(f"Guardando imagen editada ({width}x{height}) con calidad {quality}")
                    else:
                        quality = 85
                    
                    img_editada.save(temp_path, "JPEG", quality=quality, optimize=True)
                    
                    # Verificar tamaño final
                    final_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
                    logger.info(f"Imagen editada guardada correctamente en: {temp_path} ({final_size_mb:.2f} MB)")
                    
                    self.conduce_archivo_seleccionado = temp_path
                    self.lbl_conduce_estado.setText(f"Seleccionado y editado: {nombre_archivo} ({final_size_mb:.1f}MB)")
                    
                except Exception as save_error:
                    logger.error(f"Error al guardar imagen editada: {save_error}", exc_info=True)
                    QMessageBox.warning(
                        self,
                        "Error",
                        f"No se pudo guardar la imagen editada: {save_error}\n\nSe usará el archivo original."
                    )
                    self.conduce_archivo_seleccionado = archivo
                    self.lbl_conduce_estado.setText(f"Seleccionado: {nombre_archivo}")
                
            except Exception as e:
                logger.error(f"Error al editar imagen: {e}", exc_info=True)
                QMessageBox.warning(
                    self,
                    "Error",
                    f"No se pudo abrir el editor de imagen: {e}\n\nSe usará el archivo original."
                )
                self.conduce_archivo_seleccionado = archivo
                self.lbl_conduce_estado.setText(f"Seleccionado: {nombre_archivo}")
        else:
            # PDFs u otros archivos: usar directamente
            self.conduce_archivo_seleccionado = archivo
            self.lbl_conduce_estado.setText(f"Seleccionado: {nombre_archivo}")
            logger.info(f"Archivo seleccionado (sin edición): {archivo}")
    
    def _ver_conduce(self):
        """Abre el conduce adjunto."""
        if not self.conduce_url:
            QMessageBox.information(self, "Info", "No hay conduce adjunto.")
            return
        
        # Abrir URL en navegador
        import webbrowser
        webbrowser.open(self.conduce_url)
        logger.info(f"Abriendo conduce: {self.conduce_url}")
    
    def _eliminar_conduce(self):
        """Elimina el conduce adjunto."""
        if not self.conduce_storage_path or not self.sm:
            return
        
        respuesta = QMessageBox.question(
            self,
            "Confirmar eliminación",
            "¿Está seguro de eliminar el conduce adjunto?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            if self.sm.eliminar_conduce(self.conduce_storage_path):
                self.conduce_url = None
                self.conduce_storage_path = None
                self.lbl_conduce_estado.setText("Sin archivo adjunto")
                self.btn_ver_conduce.setEnabled(False)
                self.btn_eliminar_conduce.setEnabled(False)
                QMessageBox.information(self, "Éxito", "Conduce eliminado correctamente.")
                logger.info(f"Conduce eliminado: {self.conduce_storage_path}")
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar el conduce.")
