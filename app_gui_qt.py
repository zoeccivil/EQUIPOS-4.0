"""
Interfaz gráfica principal para EQUIPOS 4.0
Adaptada para trabajar con Firebase en lugar de SQLite
"""

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QFileDialog,
    QMessageBox,
    QMenuBar,
    QMenu,
    QWidget,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QHBoxLayout,
    QPushButton,
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QTimer, Qt
import shutil
from datetime import datetime
import sys
import os
import logging

from firebase_manager import FirebaseManager
from backup_manager import BackupManager
from storage_manager import StorageManager  # Importar StorageManager
from config_manager import cargar_configuracion, guardar_configuracion
from theme_manager import ThemeManager

# Importar tabs
from dashboard_tab import DashboardTab
from registro_alquileres_tab import RegistroAlquileresTab
from gastos_equipos_tab import TabGastosEquipos
from pagos_operadores_tab import TabPagosOperadores
from dialogos.ventana_gestion_abono import VentanaGestionAbonos
from dialogos.estado_cuenta_dialog import EstadoCuentaDialog

logger = logging.getLogger(__name__)


class AppGUI(QMainWindow):
    """
    Ventana principal de la aplicación EQUIPOS 4.0.
    Gestiona tabs, menús y configuración general.
    """

    def __init__(
        self,
        firebase_manager: FirebaseManager,
        storage_manager: StorageManager | None,
        backup_manager: BackupManager | None,
        config: dict,
        parent=None,
    ):
        super().__init__(parent)

        # Gestores inyectados
        self.fm: FirebaseManager = firebase_manager
        self.sm: StorageManager | None = storage_manager
        self.bm: BackupManager | None = backup_manager
        self.config: dict = config or {}

        # Mapas de nombres
        self.clientes_mapa: dict[str, str] = {}
        self.equipos_mapa: dict[str, str] = {}
        self.operadores_mapa: dict[str, str] = {}
        self.cuentas_mapa: dict[str, str] = {}
        self.categorias_mapa: dict[str, str] = {}
        self.subcategorias_mapa: dict[str, str] = {}

        # Configuración de ventana
        self.setWindowTitle("EQUIPOS 4.0 - Cargando...")
        self.resize(1366, 768)

        # Crear interfaz
        self._crear_tabs()
        self._crear_menu()

        # Cargar datos iniciales
        QTimer.singleShot(100, self._cargar_datos_iniciales)

    # ------------------------------------------------------------------ Tabs

    def _crear_tabs(self):
        """Crea los tabs principales de la aplicación"""
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        try:
            # Dashboard
            self.dashboard_tab = DashboardTab(self.fm)
            self.tabs.addTab(self.dashboard_tab, "Dashboard")

            # Registro de Alquileres
            self.registro_tab = RegistroAlquileresTab(
                self.fm, storage_manager=self.sm
            )
            self.tabs.addTab(self.registro_tab, "Registro de Alquileres")

            # Gastos de Equipos
            self.gastos_tab = TabGastosEquipos(self.fm, storage_manager=self.sm)
            self.tabs.addTab(self.gastos_tab, "Gastos de Equipos")

            # Pagos a Operadores
            self.pagos_tab = TabPagosOperadores(self.fm, storage_manager=self.sm)
            self.tabs.addTab(self.pagos_tab, "Pagos a Operadores")

            # Tab inicial
            self.tabs.setCurrentIndex(1)

        except Exception as e:
            logger.exception("Error creando tabs")
            QMessageBox.critical(
                self,
                "Error al iniciar",
                f"No se pudo iniciar la interfaz gráfica:\n{e}",
            )
            raise

    # ------------------------------------------------------------------ Placeholders (no usados, pero mantenidos)

    def _crear_registro_placeholder(self):
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel("Registro de Alquileres")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            "font-size: 24px; font-weight: bold; padding: 20px;"
        )
        info_label = QLabel("Aquí se gestionarán los alquileres de equipos")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(label)
        layout.addWidget(info_label)
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _crear_gastos_placeholder(self):
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel("Gastos de Equipos")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            "font-size: 24px; font-weight: bold; padding: 20px;"
        )
        info_label = QLabel(
            "Aquí se registrarán los gastos asociados a los equipos"
        )
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(label)
        layout.addWidget(info_label)
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _crear_pagos_placeholder(self):
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel("Pagos a Operadores")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            "font-size: 24px; font-weight: bold; padding: 20px;"
        )
        info_label = QLabel(
            "Aquí se gestionarán los pagos a los operadores de equipos"
        )
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(label)
        layout.addWidget(info_label)
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    # ------------------------------------------------------------------ Menús

    def _crear_menu(self):
        """Crea el menú principal de la aplicación"""
        menubar = self.menuBar()

        # Menú Archivo
        archivo_menu = menubar.addMenu("Archivo")
        archivo_menu.addAction(
            "Crear Backup Manual...", self._crear_backup_manual
        )
        archivo_menu.addAction(
            "Información del Último Backup", self._info_ultimo_backup
        )
        archivo_menu.addSeparator()
        archivo_menu.addAction("Salir", self.close)

        # Menú Gestión
        gestion_menu = menubar.addMenu("Gestión")
        gestion_menu.addAction("🏗️ Equipos", self._gestionar_equipos)
        gestion_menu.addAction("👥 Clientes", self._gestionar_clientes)
        gestion_menu.addAction("👷 Operadores", self._gestionar_operadores)
        gestion_menu.addSeparator()
        gestion_menu.addAction(
            "🔧 Mantenimientos", self._gestionar_mantenimientos
        )
        gestion_menu.addAction("💵 Gestionar Abonos", self._gestionar_abonos)

        # Menú Reportes
        reportes_menu = menubar.addMenu("Reportes")

        act_det = reportes_menu.addAction(
            "📄 Detallado Equipos (Preview)",
            self._abrir_preview_reporte_detallado,
        )
        act_det.setShortcut("Ctrl+D")

        reportes_menu.addAction(
            "👷 Reporte Operadores", self._generar_reporte_operadores
        )
        reportes_menu.addAction(
            "📊 Estado de Cuenta Cliente",
            self._generar_estado_cuenta_cliente_pdf,
        )
        reportes_menu.addAction(
            "📊 Estado de Cuenta General",
            self._generar_estado_cuenta_general_pdf,
        )

        act_rend = reportes_menu.addAction(
            "📈 Rendimientos (Preview)", self._abrir_preview_rendimientos
        )
        act_rend.setShortcut("Ctrl+R")

        # Menú Configuración
        config_menu = menubar.addMenu("Configuración")

        # Submenú de temas
        temas_menu = QMenu("Tema", self)
        for tema in ThemeManager.get_available_themes():
            action = QAction(tema, self)
            action.triggered.connect(
                lambda checked, t=tema: self._cambiar_tema(t)
            )
            temas_menu.addAction(action)
        config_menu.addMenu(temas_menu)

        config_menu.addSeparator()
        config_menu.addAction(
            "🔑 Configurar Credenciales Firebase", self._configurar_firebase
        )
        config_menu.addAction(
            "📋 Configurar Backups", self._configurar_backups
        )
        config_menu.addAction("⚙️ Ver Configuración", self._ver_configuracion)

        # Menú Ayuda
        ayuda_menu = menubar.addMenu("Ayuda")
        ayuda_menu.addAction("Acerca de", self._acerca_de)
        ayuda_menu.addAction("Documentación", self._abrir_documentacion)

    # ------------------------------------------------------------------ Carga inicial

    def _cargar_datos_iniciales(self):
        """
        Carga mapas y datos iniciales delegando en _cargar_mapas_y_poblar_tabs.
        """
        try:
            self._cargar_mapas_y_poblar_tabs()
        except Exception as e:
            logger.critical(
                f"Error CRÍTICO al cargar datos iniciales: {e}", exc_info=True
            )
            error_msg = str(e)
            if (
                "429" in error_msg
                or "Quota exceeded" in error_msg
                or "ResourceExhausted" in error_msg
            ):
                QMessageBox.critical(
                    self,
                    "Error: Cuota de Firebase Excedida",
                    "Se ha excedido la cuota de Firebase/Firestore.\n\n"
                    "Posibles soluciones:\n"
                    "1. Espere unos minutos e intente nuevamente\n"
                    "2. Verifique su plan de Firebase (¿Free tier?)\n"
                    "3. Revise el uso en Firebase Console\n"
                    "4. Considere actualizar a un plan de pago\n\n"
                    "La aplicación se cerrará. Por favor, espere e intente nuevamente.",
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error Crítico de Carga",
                    "No se pudieron cargar los datos iniciales.\n\n"
                    f"Error: {e}\n\n"
                    "Posibles causas:\n"
                    "- Faltan índices en Firebase/Firestore\n"
                    "- Problemas de conexión a Internet\n"
                    "- Credenciales incorrectas\n\n"
                    "Por favor, revise los logs y reinicie la aplicación.",
                )
            self.setWindowTitle("EQUIPOS 4.0 - ERROR DE CARGA")
            QTimer.singleShot(1000, self.close)

    # ==================== Menú Archivo ====================

    def _crear_backup_manual(self):
        """Crea un backup manual de los datos de Firebase"""
        if not self.bm:
            QMessageBox.warning(
                self,
                "Backup no disponible",
                "El sistema de backups no está configurado.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Crear Backup",
            "¿Desea crear un backup manual ahora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.bm.crear_backup():
                    # Actualizar configuración
                    self.config["backup"]["ultimo_backup"] = datetime.now().isoformat()
                    guardar_configuracion(self.config)

                    QMessageBox.information(
                        self,
                        "Éxito",
                        "Backup creado exitosamente en:\n"
                        f"{self.config['backup']['ruta_backup_sqlite']}",
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        "No se pudo crear el backup. Revise los logs.",
                    )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Error al crear backup:\n{e}"
                )

    def _info_ultimo_backup(self):
        """Muestra información del último backup"""
        if not self.bm:
            QMessageBox.information(
                self,
                "Backup no disponible",
                "El sistema de backups no está configurado.",
            )
            return

        try:
            info = self.bm.obtener_info_backup()
            if info:
                mensaje = "Información del último backup:\n\n"
                mensaje += f"Fecha: {info['fecha_backup']}\n"
                mensaje += f"Versión: {info['version']}\n"
                mensaje += (
                    f"Tamaño: "
                    f"{info.get('tamanio_archivo', 0) / 1024:.2f} KB"
                )

                QMessageBox.information(
                    self, "Información de Backup", mensaje
                )
            else:
                QMessageBox.information(
                    self, "Sin Backup", "No se ha creado ningún backup aún."
                )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudo obtener información del backup:\n{e}",
            )

    # ==================== Menú Gestión ====================

    def _gestionar_equipos(self):
        """Abre ventana de gestión de equipos"""
        from dialogos.gestion_equipos_dialog import GestionEquiposDialog

        try:
            dialog = GestionEquiposDialog(self.fm, parent=self)
            dialog.exec()
            # Recargar mapas después de la gestión
            self._cargar_datos_iniciales()
        except Exception as e:
            logger.error(
                f"Error al abrir gestión de equipos: {e}", exc_info=True
            )
            QMessageBox.critical(
                self, "Error", f"Error al abrir gestión de equipos:\n{e}"
            )

    def _gestionar_clientes(self):
        """Abre ventana de gestión de clientes"""
        from dialogos.gestion_entidad_dialog import GestionEntidadDialog

        try:
            dialog = GestionEntidadDialog(
                self.fm, tipo_entidad="Cliente", parent=self
            )
            dialog.exec()
            # Recargar mapas después de la gestión
            self._cargar_datos_iniciales()
        except Exception as e:
            logger.error(
                f"Error al abrir gestión de clientes: {e}", exc_info=True
            )
            QMessageBox.critical(
                self, "Error", f"Error al abrir gestión de clientes:\n{e}"
            )

    def _gestionar_operadores(self):
        """Abre ventana de gestión de operadores"""
        from dialogos.gestion_entidad_dialog import GestionEntidadDialog

        try:
            dialog = GestionEntidadDialog(
                self.fm, tipo_entidad="Operador", parent=self
            )
            dialog.exec()
            # Recargar mapas después de la gestión
            self._cargar_datos_iniciales()
        except Exception as e:
            logger.error(
                f"Error al abrir gestión de operadores: {e}", exc_info=True
            )
            QMessageBox.critical(
                self,
                "Error",
                f"Error al abrir gestión de operadores:\n{e}",
            )

    def _gestionar_mantenimientos(self):
        """Abre ventana de gestión de mantenimientos (Firebase)"""
        try:
            from ventana_gestion_mantenimiento_firebase import (
                VentanaGestionMantenimientosFirebase,
            )

            proyecto_actual = {
                "id": self.config.get("app", {}).get("proyecto_id", 8)
            }

            dlg = VentanaGestionMantenimientosFirebase(
                firebase_manager=self.fm,
                proyecto_actual=proyecto_actual,
                parent=self,
            )
            dlg.exec()

            if hasattr(self.dashboard_tab, "refrescar_datos"):
                self.dashboard_tab.refrescar_datos()

        except Exception as e:
            logger.error(
                f"Error al abrir gestión de mantenimientos: {e}", exc_info=True
            )
            QMessageBox.critical(
                self,
                "Error",
                f"Error al abrir gestión de mantenimientos:\n{e}",
            )

    def _gestionar_abonos(self):
        """Abre ventana de gestión de abonos (Firebase)"""
        try:
            from dialogos.ventana_gestion_abono import VentanaGestionAbonos

            moneda = self.config.get("app", {}).get("moneda", "RD$")

            dialogo = VentanaGestionAbonos(
                self.fm,
                moneda=moneda,
                clientes_mapa=self.clientes_mapa,
                parent=self,
            )
            dialogo.exec()

        except Exception as e:
            logger.error(
                f"Error al abrir gestión de abonos: {e}", exc_info=True
            )
            QMessageBox.critical(
                self,
                "Error",
                f"Error al abrir gestión de abonos:\n{str(e)}",
            )

    # ==================== Menú Configuración ====================

    def _cambiar_tema(self, tema: str):
        """Cambia el tema de la aplicación"""
        try:
            app = QApplication.instance()
            ThemeManager.apply_theme(app, tema)

            if "app" not in self.config:
                self.config["app"] = {}
            self.config["app"]["tema"] = tema
            guardar_configuracion(self.config)

            QMessageBox.information(
                self,
                "Tema Cambiado",
                f"El tema '{tema}' se ha aplicado correctamente.\n\n"
                "Nota: Algunos cambios pueden requerir reiniciar la aplicación.",
            )
        except Exception as e:
            QMessageBox.warning(
                self, "Error", f"No se pudo cambiar el tema:\n{e}"
            )

    def _configurar_firebase(self):
        """
        Permite configurar las credenciales de Firebase desde la interfaz.
        El usuario puede seleccionar un archivo de credenciales y configurar el bucket de Storage.
        """
        from PyQt6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QLabel,
            QPushButton,
            QLineEdit,
            QFormLayout,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Configurar Firebase")
        dialog.setMinimumWidth(500)

        layout = QVBoxLayout(dialog)

        # Información actual
        info_label = QLabel("<b>Configuración Actual de Firebase:</b>")
        layout.addWidget(info_label)

        form_layout = QFormLayout()

        # Credenciales actuales
        creds_actual = (
            self.config.get("firebase", {}).get(
                "credentials_path", "No configurado"
            )
        )
        lbl_creds = QLabel(creds_actual)
        form_layout.addRow("Credenciales:", lbl_creds)

        # Project ID actual
        project_actual = (
            self.config.get("firebase", {}).get(
                "project_id", "No configurado"
            )
        )
        lbl_project = QLabel(project_actual)
        form_layout.addRow("Project ID:", lbl_project)

        # Storage Bucket actual
        bucket_actual = (
            self.config.get("firebase", {}).get(
                "storage_bucket", "No configurado"
            )
        )
        lbl_bucket = QLabel(bucket_actual)
        form_layout.addRow("Storage Bucket:", lbl_bucket)

        layout.addLayout(form_layout)

        # Sección para nueva configuración
        layout.addWidget(QLabel("\n<b>Nueva Configuración:</b>"))

        new_form = QFormLayout()

        # Campo para archivo de credenciales
        creds_layout = QHBoxLayout()
        self.txt_creds_path = QLineEdit()
        self.txt_creds_path.setPlaceholderText(
            "Ruta al archivo de credenciales..."
        )
        self.txt_creds_path.setText(
            creds_actual if creds_actual != "No configurado" else ""
        )
        creds_layout.addWidget(self.txt_creds_path)

        btn_browse_creds = QPushButton("📁 Buscar")
        btn_browse_creds.clicked.connect(
            lambda: self._browse_credentials_file(self.txt_creds_path)
        )
        creds_layout.addWidget(btn_browse_creds)
        new_form.addRow("Credenciales:", creds_layout)

        # Campo para Project ID
        self.txt_project_id = QLineEdit()
        self.txt_project_id.setPlaceholderText(
            "ID del proyecto Firebase..."
        )
        self.txt_project_id.setText(
            project_actual if project_actual != "No configurado" else ""
        )
        new_form.addRow("Project ID:", self.txt_project_id)

        # Campo para Storage Bucket
        self.txt_storage_bucket = QLineEdit()
        self.txt_storage_bucket.setPlaceholderText("nombre-proyecto.appspot.com")
        self.txt_storage_bucket.setText(
            bucket_actual if bucket_actual != "No configurado" else ""
        )
        new_form.addRow("Storage Bucket:", self.txt_storage_bucket)

        layout.addLayout(new_form)

        # Nota informativa
        note_label = QLabel(
            "\n<i>Nota: Después de guardar los cambios, la aplicación se "
            "reiniciará automáticamente para aplicar la nueva configuración "
            "de Firebase.</i>"
        )
        note_label.setWordWrap(True)
        layout.addWidget(note_label)

        # Botones
        buttons_layout = QHBoxLayout()

        btn_save = QPushButton("💾 Guardar y Reiniciar")
        btn_save.clicked.connect(lambda: self._save_firebase_config(dialog))
        buttons_layout.addWidget(btn_save)

        btn_cancel = QPushButton("✖️ Cancelar")
        btn_cancel.clicked.connect(dialog.reject)
        buttons_layout.addWidget(btn_cancel)

        layout.addLayout(buttons_layout)

        dialog.exec()

    def _browse_credentials_file(self, line_edit):
        """Abre un diálogo para seleccionar el archivo de credenciales."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Archivo de Credenciales Firebase",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            line_edit.setText(file_path)

    def _save_firebase_config(self, dialog):
        """Guarda la nueva configuración de Firebase y reinicia la aplicación."""
        try:
            creds_path = self.txt_creds_path.text().strip()
            project_id = self.txt_project_id.text().strip()
            storage_bucket = self.txt_storage_bucket.text().strip()

            if not creds_path or not project_id:
                QMessageBox.warning(
                    self,
                    "Datos Incompletos",
                    "Debe proporcionar al menos la ruta de credenciales y el Project ID.",
                )
                return

            if not os.path.exists(creds_path):
                QMessageBox.warning(
                    self,
                    "Archivo No Encontrado",
                    "No se encontró el archivo de credenciales:\n"
                    f"{creds_path}",
                )
                return

            if "firebase" not in self.config:
                self.config["firebase"] = {}

            self.config["firebase"]["credentials_path"] = creds_path
            self.config["firebase"]["project_id"] = project_id

            if storage_bucket:
                self.config["firebase"]["storage_bucket"] = storage_bucket

            guardar_configuracion(self.config)

            respuesta = QMessageBox.question(
                self,
                "Configuración Guardada",
                "La configuración de Firebase se guardó correctamente.\n\n"
                "¿Desea reiniciar la aplicación ahora para aplicar los cambios?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            dialog.accept()

            if respuesta == QMessageBox.StandardButton.Yes:
                logger.info(
                    "Reiniciando aplicación para aplicar nueva configuración "
                    "Firebase..."
                )
                QApplication.quit()
                os.execl(sys.executable, sys.executable, *sys.argv)

        except Exception as e:
            logger.error(
                f"Error al guardar configuración Firebase: {e}", exc_info=True
            )
            QMessageBox.critical(
                self, "Error", f"Error al guardar la configuración:\n{e}"
            )

    def _configurar_backups(self):
        """Abre ventana de configuración de backups"""
        QMessageBox.information(
            self,
            "En desarrollo",
            "La configuración de backups estará disponible próximamente.",
        )

    def _ver_configuracion(self):
        """Muestra la configuración actual"""
        import json

        config_str = json.dumps(self.config, indent=2, ensure_ascii=False)

        dialog = QMessageBox(self)
        dialog.setWindowTitle("Configuración Actual")
        dialog.setText("Configuración de la aplicación:")
        dialog.setDetailedText(config_str)
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.exec()

    # ==================== Menú Ayuda ====================

    def _acerca_de(self):
        """Muestra información sobre la aplicación"""
        mensaje = """
        <h2>EQUIPOS 4.0</h2>
        <p><b>Sistema de Gestión de Alquiler de Equipos Pesados</b></p>
        <p>Versión: 4.0.0</p>
        <p>Desarrollado por: ZOEC Civil</p>
        <p>Tecnologías:</p>
        <ul>
            <li>PyQt6 - Interfaz Gráfica</li>
            <li>Firebase (Firestore) - Base de Datos en la Nube</li>
            <li>SQLite - Backups Locales</li>
        </ul>
        <p><i>© 2025 ZOEC Civil. Todos los derechos reservados.</i></p>
        """

        QMessageBox.about(self, "Acerca de EQUIPOS 4.0", mensaje)

    def _abrir_documentacion(self):
        """Abre la documentación"""
        QMessageBox.information(
            self,
            "Documentación",
            "La documentación está disponible en la carpeta 'docs' del proyecto:\n\n"
            "- arquitectura_equipos_firebase.md\n"
            "- migracion_desde_progain.md\n"
            "- backups_sqlite.md\n\n"
            "También puede consultar el archivo README.md",
        )

    # ==================== Menú Reportes ====================

    def _generar_reporte_detallado_pdf(self):
        """
        Genera reporte detallado de equipos (ingresos por alquiler, opcionalmente costos/gastos)
        usando Firebase y ReportGenerator.
        """
        try:
            from dialogos.dialogo_reporte_detallado_firebase import (
                DialogoReporteDetalladoFirebase,
            )
            from report_generator import ReportGenerator
            from PyQt6.QtWidgets import QFileDialog
        except Exception as e:
            logger.error(
                "Error importando dependencias de reporte detallado: %s", e,
                exc_info=True,
            )
            QMessageBox.critical(
                self,
                "Error",
                "No se pudieron cargar los componentes del reporte detallado:\n"
                f"{e}",
            )
            return

        try:
            moneda = self.config.get("app", {}).get("moneda", "RD$")

            dlg = DialogoReporteDetalladoFirebase(
                fm=self.fm,
                clientes_mapa=self.clientes_mapa,
                proyecto_id=self.config.get("app", {}).get("proyecto_id", 8),
                parent=self,
            )
            if not dlg.exec():
                return

            filtros = dlg.get_filtros()
            formato = dlg.formato or "pdf"
            logger.info(
                "Reporte detallado - filtros: %s, formato: %s",
                filtros,
                formato,
            )

            filtros_alq = {
                "fecha_inicio": filtros["fecha_inicio"],
                "fecha_fin": filtros["fecha_fin"],
            }
            if filtros["cliente_id"]:
                filtros_alq["cliente_id"] = filtros["cliente_id"]

            alquileres = self.fm.obtener_alquileres(filtros_alq)

            if not alquileres:
                QMessageBox.information(
                    self,
                    "Sin datos",
                    "No hay alquileres para el período o filtros seleccionados.",
                )
                return

            self._enriquecer_facturas_con_nombres(alquileres)

            datos = []
            for row in alquileres:
                horas = float(row.get("horas", 0) or 0)
                monto = float(row.get("monto", 0) or 0)

                datos.append(
                    {
                        "fecha": str(row.get("fecha", "")),
                        "cliente": row.get("cliente_nombre", ""),
                        "equipo": row.get("equipo_nombre", ""),
                        "operador": row.get("operador_nombre", ""),
                        "ubicacion": row.get("ubicacion", ""),
                        "conduce": row.get("conduce", ""),
                        "horas": round(horas, 2),
                        "monto": round(monto, 2),
                    }
                )

            ext = "PDF (*.pdf)" if formato == "pdf" else "Excel (*.xlsx)"
            sugerido = (
                f"Reporte_Detallado_Equipos_{filtros['fecha_inicio']}_a_"
                f"{filtros['fecha_fin']}"
            ).replace(" ", "_")
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte Detallado de Equipos",
                sugerido,
                ext,
            )
            if not file_path:
                return

            column_map = {
                "fecha": "Fecha",
                "cliente": "Cliente",
                "equipo": "Equipo",
                "operador": "Operador",
                "ubicacion": "Ubicación",
                "conduce": "Conduce",
                "horas": "Horas",
                "monto": f"Monto ({moneda})",
            }

            title = "REPORTE DETALLADO DE EQUIPOS"
            date_range = (
                f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"
            )

            rg = ReportGenerator(
                data=datos,
                title=title,
                cliente="",
                date_range=date_range,
                currency_symbol=moneda,
                storage_manager=self.sm,
                column_map=column_map,
            )

            if formato == "pdf":
                ok, error = rg.to_pdf(file_path)
            else:
                ok, error = rg.to_excel(file_path)

            if ok:
                QMessageBox.information(
                    self,
                    "Éxito",
                    "Reporte detallado generado exitosamente:\n"
                    f"{file_path}",
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo generar el reporte detallado:\n"
                    f"{error}",
                )

        except Exception as e:
            logger.error(
                "Error al generar reporte detallado de equipos: %s", e,
                exc_info=True,
            )
            QMessageBox.critical(
                self,
                "Error",
                "Error al generar reporte detallado de equipos:\n"
                f"{str(e)}",
            )

    def _generar_reporte_operadores(self):
        """
        Genera reporte de operadores (horas trabajadas, facturación, etc.)
        usando Firebase y ReportGenerator.
        """
        try:
            from dialogos.dialogo_reporte_operadores_firebase import (
                DialogoReporteOperadoresFirebase,
            )
            from report_generator import ReportGenerator
        except Exception as e:
            logger.error(
                "Error importando dependencias de reporte de operadores: %s",
                e,
                exc_info=True,
            )
            QMessageBox.critical(
                self,
                "Error",
                "No se pudieron cargar los componentes del reporte de operadores:\n"
                f"{e}",
            )
            return

        try:
            moneda = self.config.get("app", {}).get("moneda", "RD$")

            dlg = DialogoReporteOperadoresFirebase(
                fm=self.fm,
                operadores_mapa=self.operadores_mapa,
                equipos_mapa=self.equipos_mapa,
                proyecto_id=self.config.get("app", {}).get("proyecto_id", 8),
                parent=self,
            )
            if not dlg.exec():
                return

            filtros = dlg.get_filtros()
            formato = dlg.formato or "pdf"
            logger.info(
                "Reporte operadores - filtros: %s, formato: %s",
                filtros,
                formato,
            )

            filtros_alq = {
                "fecha_inicio": filtros["fecha_inicio"],
                "fecha_fin": filtros["fecha_fin"],
            }
            if filtros["operador_id"]:
                filtros_alq["operador_id"] = filtros["operador_id"]
            if filtros["equipo_id"]:
                filtros_alq["equipo_id"] = filtros["equipo_id"]

            alquileres = self.fm.obtener_alquileres(filtros_alq)

            if not alquileres:
                QMessageBox.information(
                    self,
                    "Sin datos",
                    "No hay alquileres para el período o filtros seleccionados.",
                )
                return

            self._enriquecer_facturas_con_nombres(alquileres)

            pagos = self.fm.obtener_pagos_operadores({})
            fi = filtros["fecha_inicio"]
            ff = filtros["fecha_fin"]

            pagos_filtrados = []
            for p in pagos or []:
                f = p.get("fecha")
                if not isinstance(f, str):
                    continue
                if not (fi <= f <= ff):
                    continue
                if (
                    filtros["operador_id"]
                    and str(p.get("operador_id")) != filtros["operador_id"]
                ):
                    continue
                if (
                    filtros["equipo_id"]
                    and str(p.get("equipo_id")) != filtros["equipo_id"]
                ):
                    continue
                pagos_filtrados.append(p)

            datos = []
            for row in alquileres:
                monto = float(row.get("monto", 0) or 0)
                horas = float(row.get("horas", 0) or 0)
                datos.append(
                    {
                        "fecha": row.get("fecha", ""),
                        "operador": row.get("operador_nombre", ""),
                        "equipo": row.get("equipo_nombre", ""),
                        "cliente": row.get("cliente_nombre", ""),
                        "ubicacion": row.get("ubicacion", ""),
                        "conduce": row.get("conduce", ""),
                        "horas": horas,
                        "monto": monto,
                    }
                )

            pagos_por_operador: dict[str, float] = {}
            for p in pagos_filtrados:
                oid = str(p.get("operador_id") or "")
                monto_p = float(p.get("monto", 0) or 0)
                pagos_por_operador[oid] = (
                    pagos_por_operador.get(oid, 0.0) + monto_p
                )

            from PyQt6.QtWidgets import QFileDialog

            ext = "PDF (*.pdf)" if formato == "pdf" else "Excel (*.xlsx)"
            sugerido = (
                f"Reporte_Operadores_{filtros['fecha_inicio']}_a_"
                f"{filtros['fecha_fin']}"
            ).replace(" ", "_")
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte de Operadores",
                sugerido,
                ext,
            )
            if not file_path:
                return

            column_map = {
                "fecha": "Fecha",
                "operador": "Operador",
                "equipo": "Equipo",
                "cliente": "Cliente",
                "ubicacion": "Ubicación",
                "conduce": "Conduce",
                "horas": "Horas",
                "monto": "Monto Facturado",
            }

            title = "REPORTE DE OPERADORES"
            date_range = (
                f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"
            )

            rg = ReportGenerator(
                data=datos,
                title=title,
                cliente="",
                date_range=date_range,
                currency_symbol=moneda,
                storage_manager=self.sm,
                column_map=column_map,
            )

            rg.pagos_por_operador = pagos_por_operador

            if formato == "pdf":
                ok, error = rg.to_pdf(file_path)
            else:
                ok, error = rg.to_excel(file_path)

            if ok:
                QMessageBox.information(
                    self,
                    "Éxito",
                    "Reporte de operadores generado exitosamente:\n"
                    f"{file_path}",
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo generar el reporte de operadores:\n"
                    f"{error}",
                )

        except Exception as e:
            logger.error(
                "Error al generar reporte de operadores: %s", e,
                exc_info=True,
            )
            QMessageBox.critical(
                self,
                "Error",
                "Error al generar reporte de operadores:\n"
                f"{str(e)}",
            )

    def _generar_estado_cuenta_cliente_pdf(self):
        """Genera estado de cuenta (cliente o general) con filtros de equipo/operador y abonos agrupados por fecha."""
        try:
            from dialogos.estado_cuenta_dialog import EstadoCuentaDialog
            from report_generator import ReportGenerator

            moneda = self.config.get('app', {}).get('moneda', 'RD$')

            # Abrir diálogo (con preview) y recoger filtros
            dialog = EstadoCuentaDialog(self.fm, parent=self, currency_symbol=moneda)
            if not dialog.exec():
                return  # Usuario canceló

            filtros = dialog.get_filtros()
            logger.info(f"Generando estado de cuenta con filtros: {filtros}")

            # Normalizar cliente_id a string (cuando exista)
            cliente_id = filtros["cliente_id"]
            if cliente_id is not None:
                cliente_id = str(cliente_id)
            filtros["cliente_id"] = cliente_id  # aseguramos string o None

            # ---------------- 1) FACTURAS (alquileres) ----------------
            filtros_alq = {
                "fecha_inicio": filtros["fecha_inicio"],
                "fecha_fin": filtros["fecha_fin"],
            }
            if cliente_id:
                filtros_alq["cliente_id"] = cliente_id
            if filtros["equipo_id"]:
                filtros_alq["equipo_id"] = filtros["equipo_id"]
            if filtros["operador_id"]:
                filtros_alq["operador_id"] = filtros["operador_id"]

            facturas = self.fm.obtener_alquileres(filtros_alq) or []
            logger.info(f"Estado cuenta: facturas encontradas = {len(facturas)} para filtros_alq={filtros_alq}")

            # ---------------- 2) ABONOS ----------------
            abonos = self.fm.obtener_abonos(
                cliente_id=cliente_id,
                fecha_inicio=filtros["fecha_inicio"],
                fecha_fin=filtros["fecha_fin"],
            ) or []

            logger.info(f"Estado cuenta: abonos crudos = {abonos}")
            logger.info(f"Estado cuenta: abonos encontrados = {len(abonos)} para cliente_id={cliente_id}")

            abonos_por_fecha = self._agrupar_abonos_por_fecha(abonos)

            if not facturas:
                QMessageBox.information(
                    self, "Sin datos",
                    "No hay alquileres para el período o filtros seleccionados."
                )
                return

            # ---------------- 3) Enriquecer facturas con nombres legibles ----------------
            self._enriquecer_facturas_con_nombres(facturas)

            # ---------------- 4) Totales ----------------
            total_facturado = sum(float(row.get("monto", 0) or 0) for row in facturas)
            total_abonado = sum(monto for _, monto in abonos_por_fecha)
            saldo = total_facturado - total_abonado

            logger.info(
                f"Estado cuenta: total_facturado={total_facturado}, "
                f"total_abonado={total_abonado}, saldo={saldo}"
            )

            # ---------------- 5) Título, archivo destino, etc. ----------------
            es_general = cliente_id is None
            cliente_nombre = "GENERAL" if es_general else filtros["cliente_nombre"]
            title = "ESTADO DE CUENTA GENERAL" if es_general else f"ESTADO DE CUENTA - {cliente_nombre}"
            date_range = f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"

            # Nombre de archivo sugerido
            nombre_archivo = f"Estado_Cuenta_{cliente_nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            nombre_archivo = nombre_archivo.replace(" ", "_")

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Estado de Cuenta",
                nombre_archivo,
                "PDF (*.pdf)"
            )
            if not file_path:
                return

            # 6) Preparar y generar PDF
            column_map = self._build_column_map_estado_cuenta(es_general)

            rg = ReportGenerator(
                data=facturas,
                title=title,
                cliente=cliente_nombre,
                date_range=date_range,
                currency_symbol=moneda,
                storage_manager=self.sm,
                column_map=column_map
            )
            # Pasar resumen de abonos por fecha y totales
            rg.abonos_por_fecha = abonos_por_fecha  # [(fecha, total)]
            rg.total_facturado = total_facturado
            rg.total_abonado = total_abonado
            rg.saldo = saldo
            rg.abonos = abonos  # compatibilidad, por si to_pdf usa _group_abonos_by_date

            ok, error = rg.to_pdf(file_path)
            if ok:
                QMessageBox.information(self, "Éxito", f"Estado de cuenta generado exitosamente:\n{file_path}")
            else:
                QMessageBox.critical(self, "Error", f"No se pudo generar el estado de cuenta:\n{error}")

        except Exception as e:
            logger.error(f"Error al generar estado de cuenta: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al generar estado de cuenta:\n{str(e)}")


    def _generar_estado_cuenta_general_pdf(self):
        """Genera estado de cuenta general de todos los clientes"""
        self._generar_estado_cuenta_cliente_pdf()

    def _agrupar_abonos_por_fecha(self, abonos: list) -> list[tuple[str, float]]:
        """
        Agrupa abonos por fecha y devuelve lista ordenada: [(fecha 'YYYY-MM-DD', total_en_fecha), ...]
        """
        acumulado: dict[str, float] = {}
        for a in abonos or []:
            fecha = a.get("fecha")
            if not fecha:
                continue
            monto = float(a.get("monto", 0) or 0)
            acumulado[fecha] = acumulado.get(fecha, 0.0) + monto
        return sorted(acumulado.items(), key=lambda x: x[0])

    def _build_column_map_estado_cuenta(self, es_general: bool) -> dict:
        """
        Columnas para el PDF del estado de cuenta.
        Sin 'CondStorage' porque ahora anexamos los conduces en el PDF.
        """
        if es_general:
            return {
                "fecha": "Fecha",
                "conduce": "Conduce",
                "ubicacion": "Ubicación",
                "equipo_nombre": "Equipo",
                "operador_nombre": "Operador",
                "horas": "Horas",
                "monto": "Monto",
                "cliente_nombre": "Cliente",
            }
        else:
            return {
                "fecha": "Fecha",
                "conduce": "Conduce",
                "ubicacion": "Ubicación",
                "equipo_nombre": "Equipo",
                "operador_nombre": "Operador",
                "horas": "Horas",
                "monto": "Monto",
            }

    def _enriquecer_facturas_con_nombres(self, facturas: list) -> None:
        """
        Modifica 'facturas' IN-PLACE agregando nombres legibles y conservando 'conduce_storage_path'.
        """
        for row in facturas:
            cid = str(row.get("cliente_id", "") or "")
            eid = str(row.get("equipo_id", "") or "")
            oid = str(row.get("operador_id", "") or "")

            row["cliente_nombre"] = self.clientes_mapa.get(cid, f"ID:{cid}")
            row["equipo_nombre"] = self.equipos_mapa.get(eid, f"ID:{eid}")
            row["operador_nombre"] = self.operadores_mapa.get(
                oid, f"ID:{oid}"
            )

            row["conduce"] = row.get("conduce") or ""
            row["ubicacion"] = row.get("ubicacion") or ""

            row["conduce_storage_path"] = row.get(
                "conduce_storage_path"
            ) or row.get("CondStorage") or ""

    def _cargar_mapas_y_poblar_tabs(self):
        """
        Carga mapas globales desde Firebase, construye subcategorias_by_cat a partir
        del catálogo de subcategorías y actualiza todos los tabs con dichos mapas.
        Luego dispara la carga inicial de datos en cada tab.
        """
        try:
            import time

            logger.info("Cargando mapas de nombres...")

            equipos = self.fm.obtener_equipos(activo=None)
            self.equipos_mapa = {
                str(eq["id"]): eq.get("nombre", "N/A") for eq in equipos
            }

            time.sleep(0.3)

            clientes = self.fm.obtener_entidades(tipo="Cliente", activo=None)
            self.clientes_mapa = {
                str(cl["id"]): cl.get("nombre", "N/A") for cl in clientes
            }

            time.sleep(0.3)

            operadores = self.fm.obtener_entidades(
                tipo="Operador", activo=None
            )
            self.operadores_mapa = {
                str(op["id"]): op.get("nombre", "N/A") for op in operadores
            }

            time.sleep(0.3)

            self.cuentas_mapa = {
                str(k): v
                for k, v in (
                    self.fm.obtener_mapa_global("cuentas") or {}
                ).items()
            }
            time.sleep(0.3)
            self.categorias_mapa = {
                str(k): v
                for k, v in (
                    self.fm.obtener_mapa_global("categorias") or {}
                ).items()
            }
            time.sleep(0.3)
            self.subcategorias_mapa = {
                str(k): v
                for k, v in (
                    self.fm.obtener_mapa_global("subcategorias") or {}
                ).items()
            }

            subcats_catalogo = []
            if hasattr(self.fm, "obtener_subcategorias_catalogo"):
                subcats_catalogo = self.fm.obtener_subcategorias_catalogo() or []

            by_cat: dict[str, dict[str, str]] = {}
            for sc in subcats_catalogo:
                sid = str(sc.get("id"))
                cid = sc.get("categoria_id")
                cid = str(cid) if cid not in (None, "", 0, "0") else None
                nom = sc.get("nombre") or self.subcategorias_mapa.get(sid, "")
                if cid:
                    by_cat.setdefault(cid, {})[sid] = nom

            logger.info(
                "Mapas cargados. Actualizando título y poblando tabs..."
            )

            self.setWindowTitle(
                f"EQUIPOS 4.0 - {len(self.equipos_mapa)} Equipos Totales"
            )

            mapas_completos = {
                "equipos": self.equipos_mapa,
                "clientes": self.clientes_mapa,
                "operadores": self.operadores_mapa,
                "cuentas": self.cuentas_mapa,
                "categorias": self.categorias_mapa,
                "subcategorias": self.subcategorias_mapa,
                "subcategorias_catalogo": subcats_catalogo,
                "subcategorias_by_cat": by_cat,
            }

            if hasattr(self.dashboard_tab, "actualizar_mapas"):
                self.dashboard_tab.actualizar_mapas(mapas_completos)
            if hasattr(self.registro_tab, "actualizar_mapas"):
                self.registro_tab.actualizar_mapas(mapas_completos)
            if hasattr(self.gastos_tab, "actualizar_mapas"):
                self.gastos_tab.actualizar_mapas(mapas_completos)
            if hasattr(self.pagos_tab, "actualizar_mapas"):
                self.pagos_tab.actualizar_mapas(mapas_completos)

            if hasattr(self.dashboard_tab, "refrescar_datos"):
                self.dashboard_tab.refrescar_datos()
            if hasattr(self.registro_tab, "_cargar_alquileres"):
                self.registro_tab._cargar_alquileres()
            if hasattr(self.gastos_tab, "_recargar_por_fecha"):
                self.gastos_tab._recargar_por_fecha()
            elif hasattr(self.gastos_tab, "_cargar_gastos"):
                self.gastos_tab._cargar_gastos()
            if hasattr(self.pagos_tab, "_cargar_pagos"):
                self.pagos_tab._cargar_pagos()

        except Exception as e:
            logger.critical(
                "Error en _cargar_mapas_y_poblar_tabs: %s", e, exc_info=True
            )
            error_msg = str(e)
            if (
                "429" in error_msg
                or "Quota exceeded" in error_msg
                or "ResourceExhausted" in error_msg
            ):
                QMessageBox.critical(
                    self,
                    "Error: Cuota de Firebase Excedida",
                    "Se ha excedido la cuota de Firebase/Firestore.\n\n"
                    "Posibles soluciones:\n"
                    "1. Espere unos minutos e intente nuevamente\n"
                    "2. Verifique su plan de Firebase (¿Free tier?)\n"
                    "3. Revise el uso en Firebase Console\n"
                    "4. Considere actualizar a un plan de pago\n\n"
                    "La aplicación se cerrará. Por favor, espere e intente nuevamente.",
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error Crítico de Carga",
                    "No se pudieron cargar los datos iniciales.\n\n"
                    f"Error: {e}\n\n"
                    "Posibles causas:\n"
                    "- Faltan índices en Firebase/Firestore\n"
                    "- Problemas de conexión a Internet\n"
                    "- Credenciales incorrectas\n\n"
                    "Por favor, revise los logs y reinicie la aplicación.",
                )
            self.setWindowTitle("EQUIPOS 4.0 - ERROR DE CARGA")
            QTimer.singleShot(1000, self.close)

    # ------------------- Reporte de Rendimientos -------------------

    def _generar_reporte_rendimientos(self):
        """
        Genera un reporte de rendimientos por equipo:
          - Horas facturadas
          - Monto facturado
          - Horas pagadas a operadores
          - Monto pagado a operadores
          - Precios promedio por hora
          - Margen bruto simple (Facturado - Pagado operador)
          - Margen en porcentaje sobre lo facturado
        """
        try:
            from dialogos.dialogo_reporte_rendimientos_firebase import (
                DialogoReporteRendimientosFirebase,
            )
            from report_generator import ReportGenerator
            from PyQt6.QtWidgets import QFileDialog
        except Exception as e:
            logger.error(
                "Error importando dependencias de reporte de rendimientos: %s",
                e,
                exc_info=True,
            )
            QMessageBox.critical(
                self,
                "Error",
                "No se pudieron cargar los componentes del reporte de rendimientos:\n"
                f"{e}",
            )
            return

        try:
            moneda = self.config.get("app", {}).get("moneda", "RD$")

            dlg = DialogoReporteRendimientosFirebase(
                fm=self.fm,
                equipos_mapa=self.equipos_mapa,
                parent=self,
            )
            if not dlg.exec():
                return

            filtros = dlg.get_filtros()
            formato = dlg.formato or "pdf"
            logger.info(
                "Reporte rendimientos - filtros: %s, formato: %s",
                filtros,
                formato,
            )

            rendimiento = self.fm.obtener_rendimiento_por_equipo(
                fecha_inicio=filtros["fecha_inicio"],
                fecha_fin=filtros["fecha_fin"],
                equipo_id=filtros["equipo_id"],
            )

            if not rendimiento:
                QMessageBox.information(
                    self,
                    "Sin datos",
                    "No hay datos de alquileres/pagos para el período o equipo seleccionado.",
                )
                return

            datos = []
            for r in rendimiento:
                eid = str(r.get("equipo_id", "") or "")
                nombre = self.equipos_mapa.get(
                    eid, r.get("equipo_nombre") or f"ID:{eid}"
                )

                horas_fact = float(r.get("horas_facturadas", 0) or 0)
                monto_fact = float(r.get("monto_facturado", 0) or 0)
                horas_pag = float(r.get("horas_pagadas_operador", 0) or 0)
                monto_pag = float(r.get("monto_pagado_operador", 0) or 0)

                precio_hora_fact = (
                    monto_fact / horas_fact if horas_fact > 0 else 0.0
                )
                precio_hora_pag = (
                    monto_pag / horas_pag if horas_pag > 0 else 0.0
                )

                margen = monto_fact - monto_pag
                margen_pct = (
                    margen / monto_fact * 100.0 if monto_fact > 0 else 0.0
                )

                horas_fact_fmt = f"{round(horas_fact, 2):,.2f}"
                horas_pag_fmt = f"{round(horas_pag, 2):,.2f}"

                monto_fact_fmt = f"{moneda} {round(monto_fact, 2):,.2f}"
                monto_pag_fmt = f"{moneda} {round(monto_pag, 2):,.2f}"
                precio_fact_fmt = f"{moneda} {round(precio_hora_fact, 2):,.2f}"
                precio_pag_fmt = f"{moneda} {round(precio_hora_pag, 2):,.2f}"
                margen_fmt = f"{moneda} {round(margen, 2):,.2f}"
                margen_pct_fmt = f"{round(margen_pct, 2):,.2f}%"

                datos.append(
                    {
                        "equipo": nombre,
                        "horas_facturadas": horas_fact_fmt,
                        "monto_facturado": monto_fact_fmt,
                        "horas_pagadas_operador": horas_pag_fmt,
                        "monto_pagado_operador": monto_pag_fmt,
                        "precio_hora_facturado": precio_fact_fmt,
                        "precio_hora_pagado": precio_pag_fmt,
                        "margen_bruto_simple": margen_fmt,
                        "margen_porcentaje": margen_pct_fmt,
                    }
                )

            ext = "PDF (*.pdf)" if formato == "pdf" else "Excel (*.xlsx)"
            sugerido = (
                f"Reporte_Rendimientos_{filtros['fecha_inicio']}_a_"
                f"{filtros['fecha_fin']}"
            ).replace(" ", "_")
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte de Rendimientos",
                sugerido,
                ext,
            )
            if not file_path:
                return

            column_map = {
                "equipo": "Equipo",
                "horas_facturadas": "Horas Fact.",
                "monto_facturado": "Facturado",
                "horas_pagadas_operador": "Horas Pag.",
                "monto_pagado_operador": "Pagado Op.",
                "precio_hora_facturado": "Precio/h Fact.",
                "precio_hora_pagado": "Precio/h Pag.",
                "margen_bruto_simple": "Margen",
                "margen_porcentaje": "% Margen",
            }

            title = "REPORTE DE RENDIMIENTOS POR EQUIPO"
            date_range = (
                f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"
            )

            rg = ReportGenerator(
                data=datos,
                title=title,
                cliente="",
                date_range=date_range,
                currency_symbol=moneda,
                storage_manager=self.sm,
                column_map=column_map,
            )

            if formato == "pdf":
                ok, error = rg.to_pdf(file_path)
            else:
                ok, error = rg.to_excel(file_path)

            if ok:
                QMessageBox.information(
                    self,
                    "Éxito",
                    "Reporte de rendimientos generado exitosamente:\n"
                    f"{file_path}",
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo generar el reporte de rendimientos:\n"
                    f"{error}",
                )

        except Exception as e:
            logger.error(
                "Error al generar reporte de rendimientos: %s", e,
                exc_info=True,
            )
            QMessageBox.critical(
                self,
                "Error",
                "Error al generar reporte de rendimientos:\n"
                f"{str(e)}",
            )

    # ------------------- Previews -------------------

    def _abrir_preview_rendimientos(self):
        from dialogos.dialogo_preview_rendimientos import (
            DialogoPreviewRendimientos,
        )

        dlg = DialogoPreviewRendimientos(
            fm=self.fm,
            equipos_mapa=self.equipos_mapa,
            config=self.config,
            storage_manager=self.sm,
            parent=self,
        )
        dlg.exec()

    def _abrir_preview_reporte_detallado(self):
        from dialogos.dialogo_preview_reporte_detallado import (
            DialogoPreviewReporteDetallado,
        )

        dlg = DialogoPreviewReporteDetallado(
            fm=self.fm,
            clientes_mapa=self.clientes_mapa,
            config=self.config,
            storage_manager=self.sm,
            app_gui=self,
            parent=self,
        )
        dlg.exec()