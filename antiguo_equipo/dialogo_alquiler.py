"""
DialogoAlquiler - diálogo para crear/editar un alquiler y adjuntar "conduce".

Correcciones:
- Uso de guardar_conduce (importa desde utils.adjuntos o adjuntos).
- Manejo robusto de errores con logging + QMessageBox.
- Soporte para editar imágenes vía MiniEditorImagen y salvar PIL.Image / QImage.
- Update automático del campo conduce_adjunto_path al editar una transacción existente.
- Evita cierres silenciosos; registra en progain.log.
"""
import os
import tempfile
import logging
import uuid
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QFileDialog, QMessageBox, QDateEdit, QSpinBox
)
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QImage

from mini_editor_imagen import MiniEditorImagen  # Debe existir en el proyecto

# Intentar importar guardar_conduce desde utils.adjuntos o desde adjuntos en la raíz
try:
    from adjuntos import guardar_conduce
except Exception:
    try:
        from adjuntos import guardar_conduce
    except Exception:
        guardar_conduce = None  # comprobamos en tiempo de uso

logger = logging.getLogger(__name__)
# No reconfiguramos logging aquí; asumimos que la app principal configura progain.log


class DialogoAlquiler(QDialog):
    def __init__(
        self,
        db,
        proyecto_actual,
        clientes_mapa=None,
        operadores_mapa=None,
        equipos_mapa=None,
        alquiler=None,
        config=None,
        parent=None
    ):
        super().__init__(parent)
        self.db = db
        self.proyecto_actual = proyecto_actual
        self.clientes_mapa = clientes_mapa or {}
        self.operadores_mapa = operadores_mapa or {}
        self.equipos_mapa = equipos_mapa or {}
        self.alquiler = alquiler
        self.config = config or {}
        logger.debug("DialogoAlquiler recibe config: %s", self.config)
        self.adjunto_path: Optional[str] = None
        self.transaccion_id: Optional[str] = None

        self.setWindowTitle("Alquiler de Equipo")
        self._init_ui()
        self._load_choices()
        if self.alquiler:
            self.set_datos(self.alquiler)

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Fecha
        hl_fecha = QHBoxLayout()
        hl_fecha.addWidget(QLabel("Fecha:"))
        self.fecha_edit = QDateEdit(calendarPopup=True)
        self.fecha_edit.setDate(QDate.currentDate())
        hl_fecha.addWidget(self.fecha_edit)
        layout.addLayout(hl_fecha)

        # Cliente, Operador, Equipo
        self.cliente_combo = QComboBox()
        self.operador_combo = QComboBox()
        self.equipo_combo = QComboBox()
        layout.addWidget(QLabel("Cliente:"))
        layout.addWidget(self.cliente_combo)
        layout.addWidget(QLabel("Operador:"))
        layout.addWidget(self.operador_combo)
        layout.addWidget(QLabel("Equipo:"))
        layout.addWidget(self.equipo_combo)

        # Horas y Precio por Hora
        hl_horas = QHBoxLayout()
        hl_horas.addWidget(QLabel("Horas:"))
        self.horas_spin = QSpinBox()
        self.horas_spin.setMaximum(1000)
        hl_horas.addWidget(self.horas_spin)
        hl_horas.addWidget(QLabel("Precio/Hora:"))
        self.precio_hora_edit = QLineEdit()
        hl_horas.addWidget(self.precio_hora_edit)
        layout.addLayout(hl_horas)

        # Conduce y Ubicación
        self.conduce_edit = QLineEdit()
        self.ubicacion_edit = QLineEdit()
        layout.addWidget(QLabel("Conduce:"))
        layout.addWidget(self.conduce_edit)
        layout.addWidget(QLabel("Ubicación:"))
        layout.addWidget(self.ubicacion_edit)

        # Adjunto
        hl_adjunto = QHBoxLayout()
        self.adjunto_label = QLabel("Sin archivo adjunto")
        btn_adjuntar = QPushButton("Adjuntar Conduce")
        btn_adjuntar.clicked.connect(self.seleccionar_conduce_adjunto)
        hl_adjunto.addWidget(QLabel("Archivo Conduce:"))
        hl_adjunto.addWidget(self.adjunto_label)
        hl_adjunto.addWidget(btn_adjuntar)
        layout.addLayout(hl_adjunto)

        # Botón para añadir conduce a un alquiler existente
        self.btn_actualizar_conduce = QPushButton("Actualizar Conduce Adjunto")
        self.btn_actualizar_conduce.clicked.connect(self.actualizar_conduce_existente)
        self.btn_actualizar_conduce.setVisible(False)
        layout.addWidget(self.btn_actualizar_conduce)

        # Botones aceptar/cancelar
        hl_botones = QHBoxLayout()
        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.clicked.connect(self.guardar_alquiler)
        hl_botones.addWidget(self.btn_guardar)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        hl_botones.addWidget(btn_cancelar)
        layout.addLayout(hl_botones)

    def _load_choices(self):
        """
        Llena los combos de cliente, operador y equipo usando los mapas provistos
        (keys = nombres).
        """
        clientes = list(self.clientes_mapa.keys())
        operadores = list(self.operadores_mapa.keys())
        equipos = list(self.equipos_mapa.keys())

        self.cliente_combo.clear()
        self.operador_combo.clear()
        self.equipo_combo.clear()

        if clientes:
            self.cliente_combo.addItems(clientes)
        if operadores:
            self.operador_combo.addItems(operadores)
        if equipos:
            self.equipo_combo.addItems(equipos)

# -- Helper para guardar QImage/PIL.Image a archivo temporal --
    def _save_image_object_to_file(self, image_obj, dst_path):
        """
        image_obj puede ser:
          - una instancia PIL.Image.Image con método save
          - una instancia QImage con método save(filename)
        """
        # 1. Intentar PIL.Image
        try:
            from PIL.Image import Image as PilImage  # type: ignore
            if isinstance(image_obj, PilImage):
                # Usar formato JPEG forzado que es compatible con la mayoría de los visualizadores
                image_obj.save(dst_path, format="JPEG", quality=90) 
                logger.debug("Guardado exitoso con PIL.Image: %s", dst_path)
                return True
        except ImportError:
            # Capturar específicamente si falta Pillow y no registrar como error fatal.
            logger.debug("Pillow (PIL) no disponible para guardar la imagen temporal.")
        except Exception as e:
            # Capturar otros errores (I/O, permisos) y registrarlos.
            logger.exception("Error al guardar con PIL.Image. Posiblemente fallo de I/O o permiso: %s", e)
        
        # 2. QImage fallback (PyQt)
        try:
            if isinstance(image_obj, QImage):
                # Guardar QImage, especificando formato y calidad
                if image_obj.save(dst_path, format="JPEG", quality=90):
                    logger.debug("Guardado exitoso con QImage: %s", dst_path)
                    return True
                else:
                    # Forzar un error si save devuelve False
                    raise IOError("QImage.save falló al guardar el archivo.")
        except Exception as e:
            logger.exception("Error al guardar con QImage: %s", e)
            pass

        # 3. Intentar atributo save genérico (último recurso)
        try:
            save_fn = getattr(image_obj, "save", None)
            if callable(save_fn):
                save_fn(dst_path)
                logger.debug("Guardado exitoso con método genérico: %s", dst_path)
                return True
        except Exception as e:
            logger.exception("Error al guardar con método genérico: %s", e)
            pass
            
        # 4. Fallo total: esto generará el error que queremos ver en la GUI y el log.
        raise RuntimeError("No se pudo guardar el objeto de imagen en disco (PIL o QImage fallaron).")
    
    def seleccionar_conduce_adjunto(self):
            """
            Selecciona un archivo y lo guarda usando guardar_conduce (sin update en BD,
            porque normalmente se usará al crear la transacción).
            """
            file_path = ""
            temp_file = None
            
            try:
                # --- 1. SELECCIÓN DE ARCHIVO Y VALIDACIÓN INICIAL ---
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Seleccionar archivo de Conduce",
                    "",
                    "Imágenes o PDFs (*.png *.jpg *.jpeg *.pdf);;Todos los archivos (*)"
                )
                logger.debug("Archivo seleccionado: %s", file_path)
                if not file_path:
                    return

                numero_conduce = self.conduce_edit.text().strip()
                if not numero_conduce:
                    logger.warning("Número de conduce vacío al intentar adjuntar")
                    QMessageBox.warning(self, "Número de Conduce requerido", "Debe ingresar el número de conduce antes de adjuntar.")
                    return

                ext = os.path.splitext(file_path)[1].lower()

                # --- 2. PROCESAMIENTO/EDICIÓN DE IMAGEN ---
                source_for_save = file_path

                if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
                    # 2a. Abrir el editor
                    editor = MiniEditorImagen(file_path, width=1200, height=800, parent=self)
                    if not editor.exec():
                        return  # Usuario canceló editor
                    
                    # 2b. Obtener la imagen editada
                    final_img = editor.get_final_image()
                    
                    # 2c. Guardar la imagen editada en temporal
                    tmp_dir = tempfile.gettempdir()
                    temp_file = os.path.join(tmp_dir, f"conduce_tmp_{uuid.uuid4().hex}.jpg")
                    self._save_image_object_to_file(final_img, temp_file)
                    source_for_save = temp_file

                # --- 3. GUARDADO FINAL USANDO ADJUNTOS.PY ---
                fecha_str = self.fecha_edit.date().toString("yyyy-MM-dd")
                # Usar 'noid' temporalmente para la transaccion si se está creando una nueva (ID se asigna en guardar_alquiler)
                trans_min = {'fecha': fecha_str, 'conduce': numero_conduce, 'id': 'noid'}

                if guardar_conduce is None:
                    raise RuntimeError("Función guardar_conduce no disponible (no se pudo importar o encontrar)")

                # Guardar en la ruta final del sistema (usando config y fallbacks)
                rel_path = guardar_conduce(
                    self.db, 
                    trans_min, 
                    source_for_save, 
                    self.config, 
                    width=1200, 
                    height=800, 
                    update_db=False # No actualizar BD, es una nueva transacción
                )

                # --- 4. ACTUALIZAR UI ---
                self.adjunto_path = rel_path.replace("\\", "/")
                self.adjunto_label.setText(self.adjunto_path)
                QMessageBox.information(self, "Adjunto OK", "Archivo preparado para guardar con el alquiler.")
                logger.info("Ruta relativa guardada (adjunto): %s", self.adjunto_path)

            except Exception as e:
                # Capturar y registrar CUALQUIER excepción de I/O o lógica
                logger.exception("Error CRÍTICO en seleccionar_conduce_adjunto: %s", e)
                QMessageBox.critical(self, "Error al Adjuntar", f"No se pudo adjuntar el archivo. Causa:\n{e}")

            finally:
                # --- 5. LIMPIEZA DEL ARCHIVO TEMPORAL ---
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        logger.debug("Archivo temporal eliminado: %s", temp_file)
                    except Exception as e:
                        logger.warning("No se pudo eliminar el archivo temporal %s: %s", temp_file, e)

    def guardar_alquiler(self):
        """
        Guarda (INSERT) o actualiza (UPDATE) el alquiler según si self.transaccion_id existe.
        """
        try:
            datos = self.get_datos()
            db = self.db

            # --- MODO EDICIÓN: Solo cerrar el diálogo, registro_alquileres_tab se encarga ---
            if self.transaccion_id:
                logger.info("Modo edición detectado (transaccion_id=%s), cerrando diálogo", self.transaccion_id)
                self.accept()
                return

            # --- MODO CREACIÓN: Insertar nuevo alquiler ---
            
            # 1. Obtener la cuenta principal del proyecto 8
            row = db.fetchone("SELECT cuenta_principal FROM proyectos WHERE id = 8")
            if not row:
                QMessageBox.critical(self, "Error", "No se encontró el proyecto 8 en la base de datos.")
                return
            cuenta_nombre = row['cuenta_principal']
            row_cuenta = db.fetchone("SELECT id FROM cuentas WHERE nombre = ?", (cuenta_nombre,))
            if not row_cuenta:
                QMessageBox.critical(self, "Error", f"No se encontró la cuenta '{cuenta_nombre}'.")
                return
            cuenta_id = row_cuenta['id']

            # 2. Obtener el id de la categoría "ALQUILERES"
            row_cat = db.fetchone("SELECT id FROM categorias WHERE UPPER(nombre) = 'ALQUILERES'")
            if not row_cat:
                QMessageBox.critical(self, "Error", "No se encontró la categoría 'ALQUILERES'.")
                return
            categoria_id = row_cat['id']

            # 3. Obtener/crear subcategoría con el nombre del equipo
            equipo_nombre = self.equipo_combo.currentText()
            row_subcat = db.fetchone("SELECT id FROM subcategorias WHERE nombre = ?", (equipo_nombre,))
            if not row_subcat:
                db.execute(
                    "INSERT INTO subcategorias (nombre, categoria_id) VALUES (?, ?)",
                    (equipo_nombre, categoria_id)
                )
                row_subcat = db.fetchone("SELECT id FROM subcategorias WHERE nombre = ?", (equipo_nombre,))
                if not row_subcat:
                    QMessageBox.critical(self, "Error", f"No se pudo crear la subcategoría para el equipo '{equipo_nombre}'.")
                    return
            subcategoria_id = row_subcat['id']

            # 4. Descripción automática
            horas = datos['horas']
            cliente_nombre = self.cliente_combo.currentText()
            descripcion = f"{horas} horas de equipo {equipo_nombre}, Cliente {cliente_nombre}"

            # 5. Insertar en transacciones
            new_id = uuid.uuid4().hex
            transac = {
                'id': new_id,
                'proyecto_id': datos['proyecto_id'],
                'cuenta_id': cuenta_id,
                'categoria_id': categoria_id,
                'subcategoria_id': subcategoria_id,
                'tipo': 'Ingreso',
                'descripcion': descripcion,
                'comentario': '',
                'monto': datos['monto'],
                'fecha': datos['fecha'],
                'cliente_id': datos['cliente_id'],
                'operador_id': datos['operador_id'],
                'conduce': datos['conduce'],
                'ubicacion': datos['ubicacion'],
                'horas': datos['horas'],
                'precio_por_hora': datos['precio_por_hora'],
                'pagado': 0,
                'kilometros': 0,
                'equipo_id': datos['equipo_id'],
                'conduce_adjunto_path': self.adjunto_path
            }

            db.execute("""
                INSERT INTO transacciones
                (id, proyecto_id, cuenta_id, categoria_id, subcategoria_id, tipo, descripcion, comentario,
                monto, fecha, cliente_id, operador_id, conduce, ubicacion, horas, precio_por_hora,
                pagado, kilometros, equipo_id, conduce_adjunto_path)
                VALUES
                (:id, :proyecto_id, :cuenta_id, :categoria_id, :subcategoria_id, :tipo, :descripcion, :comentario,
                :monto, :fecha, :cliente_id, :operador_id, :conduce, :ubicacion, :horas, :precio_por_hora,
                :pagado, :kilometros, :equipo_id, :conduce_adjunto_path)
            """, transac)

            # 6. Insertar en equipos_alquiler_meta
            db.execute("""
                INSERT INTO equipos_alquiler_meta
                (transaccion_id, proyecto_id, cliente_id, operador_id, horas, precio_por_hora,
                conduce, ubicacion, conduce_adjunto_path, equipo_id)
                VALUES
                (:transaccion_id, :proyecto_id, :cliente_id, :operador_id, :horas, :precio_por_hora,
                :conduce, :ubicacion, :conduce_adjunto_path, :equipo_id)
            """, {
                'transaccion_id': new_id,
                'proyecto_id': datos['proyecto_id'],
                'cliente_id': datos['cliente_id'],
                'operador_id': datos['operador_id'],
                'horas': datos['horas'],
                'precio_por_hora': datos['precio_por_hora'],
                'conduce': datos['conduce'],
                'ubicacion': datos['ubicacion'],
                'conduce_adjunto_path': self.adjunto_path,
                'equipo_id': datos['equipo_id'],
            })

            QMessageBox.information(self, "Éxito", "Alquiler registrado correctamente.")
            self.accept()

        except Exception as e:
            logger.exception("Error guardando alquiler: %s", e)
            QMessageBox.critical(self, "Error", f"No se pudo guardar el alquiler: {e}")

    def set_datos(self, datos):
        """
        Rellenar campos para edición.
        """
        # ⚠️ CRÍTICO: Asignar el ID para que guardar_alquiler() sepa que es edición
        self.transaccion_id = datos.get('id')
        
        if isinstance(datos.get('fecha'), str):
            try:
                self.fecha_edit.setDate(QDate.fromString(datos['fecha'], 'yyyy-MM-dd'))
            except Exception:
                self.fecha_edit.setDate(QDate.currentDate())
        elif datos.get('fecha') is not None:
            self.fecha_edit.setDate(datos['fecha'])

        self.cliente_combo.setCurrentText(datos.get('cliente_nombre', ''))
        self.operador_combo.setCurrentText(datos.get('operador_nombre', ''))
        self.equipo_combo.setCurrentText(datos.get('equipo_nombre', ''))
        try:
            self.horas_spin.setValue(int(datos.get('horas', 0) or 0))
        except Exception:
            self.horas_spin.setValue(0)
        self.precio_hora_edit.setText(str(datos.get('precio_por_hora', '')))
        self.conduce_edit.setText(datos.get('conduce', ''))
        self.ubicacion_edit.setText(datos.get('ubicacion', ''))
        adjunto = datos.get('conduce_adjunto_path', '') or ""
        self.adjunto_label.setText(adjunto if adjunto else "Sin archivo adjunto")
        self.adjunto_path = adjunto
        self.btn_actualizar_conduce.setVisible(True)
        
    def actualizar_conduce_existente(self):
        """
        Actualiza (reemplaza) el archivo conduce para una transacción ya existente.
        Guarda el archivo en disco y actualiza la BD (guardar_conduce intentará actualizar DB si update_db=True).
        """
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Seleccionar archivo de Conduce",
                "",
                "Imágenes o PDFs (*.png *.jpg *.jpeg *.pdf);;Todos los archivos (*)"
            )
            logger.debug("Archivo seleccionado para actualizar: %s", file_path)
            if not file_path:
                return

            if not self.transaccion_id:
                QMessageBox.warning(self, "Transacción no definida", "No hay una transacción cargada para actualizar.")
                return

            numero_conduce = self.conduce_edit.text().strip()
            if not numero_conduce:
                QMessageBox.warning(self, "Número de Conduce requerido", "Debe ingresar el número de conduce antes de adjuntar.")
                return

            ext = os.path.splitext(file_path)[1].lower()
            source_for_save = file_path
            temp_file = None
            try:
                if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
                    editor = MiniEditorImagen(file_path, width=1200, height=800, parent=self)
                    if not editor.exec():
                        return
                    final_img = editor.get_final_image()
                    tmp_dir = tempfile.gettempdir()
                    temp_file = os.path.join(tmp_dir, f"conduce_tmp_{uuid.uuid4().hex}.jpg")
                    self._save_image_object_to_file(final_img, temp_file)
                    source_for_save = temp_file

                if guardar_conduce is None:
                    raise RuntimeError("Función guardar_conduce no disponible (no se pudo importar)")

                # Pedimos a guardar_conduce que intente actualizar la BD automáticamente
                fecha_str = self.fecha_edit.date().toString("yyyy-MM-dd")
                trans_min = {'fecha': fecha_str, 'conduce': numero_conduce, 'id': self.transaccion_id}

                rel_path = guardar_conduce(self.db, trans_min, source_for_save, self.config, width=1200, height=800, update_db=True)
                self.adjunto_path = rel_path.replace("\\", "/")
                self.adjunto_label.setText(self.adjunto_path)

                # Si la BD no fue actualizada por guardar_conduce, forzamos el update manual
                try:
                    ok = True
                    if hasattr(self.db, "actualizar_conduce_adjunto"):
                        ok = self.db.actualizar_conduce_adjunto(self.transaccion_id, self.adjunto_path)
                    else:
                        self.db.execute("UPDATE transacciones SET conduce_adjunto_path = ? WHERE id = ?", (self.adjunto_path, self.transaccion_id))
                        ok = True
                    if ok:
                        QMessageBox.information(self, "Éxito", "Archivo conduce actualizado correctamente en la base de datos.")
                    else:
                        QMessageBox.warning(self, "Aviso", "Archivo guardado en disco, pero no se pudo actualizar la base de datos automáticamente.")
                except Exception as e_upd:
                    logger.exception("Error actualizando DB tras guardar conduce: %s", e_upd)
                    QMessageBox.warning(self, "Aviso", "Archivo guardado en disco, pero hubo un error al actualizar la base de datos.")

            finally:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass

        except Exception as e:
            logger.exception("Error en actualizar_conduce_existente: %s", e)
            QMessageBox.critical(self, "Error", f"No se pudo actualizar el adjunto: {e}")

    def get_datos(self):
        """
        Recupera los datos del formulario y resuelve los ids usando los mapas.
        """
        cliente_nombre = self.cliente_combo.currentText()
        operador_nombre = self.operador_combo.currentText()
        equipo_nombre = self.equipo_combo.currentText()

        cliente_id = self.clientes_mapa.get(cliente_nombre)
        operador_id = self.operadores_mapa.get(operador_nombre)
        equipo_id = self.equipos_mapa.get(equipo_nombre)

        # Calcular el monto
        try:
            horas = float(self.horas_spin.value())
            precio_hora = float(self.precio_hora_edit.text() or 0)
            monto = horas * precio_hora
        except Exception:
            horas = 0.0
            precio_hora = 0.0
            monto = 0.0

        return {
            'proyecto_id': self.proyecto_actual['id'],
            'fecha': self.fecha_edit.date().toString("yyyy-MM-dd"),
            'cliente_id': cliente_id,
            'operador_id': operador_id,
            'equipo_id': equipo_id,
            'horas': horas,
            'precio_por_hora': precio_hora,
            'monto': monto,
            'conduce': self.conduce_edit.text(),
            'ubicacion': self.ubicacion_edit.text(),
            'conduce_adjunto_path': self.adjunto_path,
            'tipo': 'Ingreso'
        }