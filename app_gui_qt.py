"""
Interfaz gráfica principal para EQUIPOS 4.0
Adaptada para trabajar con Firebase en lugar de SQLite
"""

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QFileDialog, QMessageBox, QMenuBar, 
    QMenu, QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout, QPushButton
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
from storage_manager import StorageManager # Importar StorageManager
from config_manager import cargar_configuracion, guardar_configuracion
from theme_manager import ThemeManager

# Importar tabs
from dashboard_tab import DashboardTab
from registro_alquileres_tab import RegistroAlquileresTab
from gastos_equipos_tab import TabGastosEquipos
from pagos_operadores_tab import TabPagosOperadores
# from reportes_tab import ReportesTab # ELIMINADO: Reportes ahora en menú superior

logger = logging.getLogger(__name__)

class AppGUI(QMainWindow):
    """
    Ventana principal de la aplicación EQUIPOS 4.0.
    Gestiona tabs, menús y configuración general.
    """
    
    # --- ¡INICIO DE CORRECCIÓN (V10)! ---
    def __init__(self, firebase_manager: FirebaseManager, backup_manager: BackupManager = None, 
                 storage_manager: StorageManager = None, config: dict = None):
        super().__init__()
        self.fm = firebase_manager
        self.bm = backup_manager
        self.sm = storage_manager # Guardar el storage_manager
        self.config = config or {}
    # --- FIN DE CORRECCIÓN (V10)! ---
        
        # Atributos de estado (Mapas de Nombres)
        self.clientes_mapa = {}
        self.equipos_mapa = {}
        self.operadores_mapa = {}
        self.cuentas_mapa = {}
        self.categorias_mapa = {}
        self.subcategorias_mapa = {}
        
        # Configuración de ventana
        self.setWindowTitle("EQUIPOS 4.0 - Cargando...")
        self.resize(1366, 768)
        
        # Crear interfaz
        self._crear_tabs()
        self._crear_menu()
        
        # Cargar datos iniciales
        QTimer.singleShot(100, self._cargar_datos_iniciales)
    
    def _crear_tabs(self):
        """Crea los tabs principales de la aplicación"""
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Tab de Dashboard
        self.dashboard_tab = DashboardTab(self.fm)
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        
        # --- ¡INICIO DE CORRECCIÓN (V10)! ---
        # Tab de Registro de Alquileres
        # Pasar el storage_manager al tab
        self.registro_tab = RegistroAlquileresTab(self.fm, storage_manager=self.sm)
        # --- FIN DE CORRECCIÓN (V10)! ---
        self.tabs.addTab(self.registro_tab, "Registro de Alquileres")
        
        # Tab de Gastos de Equipos
        self.gastos_tab = TabGastosEquipos(self.fm)
        self.tabs.addTab(self.gastos_tab, "Gastos de Equipos")
        
        # Tab de Pagos a Operadores
        self.pagos_tab = TabPagosOperadores(self.fm)
        self.tabs.addTab(self.pagos_tab, "Pagos a Operadores")
        
        # ELIMINADO: Tab de Reportes - ahora en menú superior
        # self.reportes_tab = None
        
        # Establecer tab inicial
        self.tabs.setCurrentIndex(1)  # Abrir en Registro de Alquileres por defecto
    
    def _crear_registro_placeholder(self):
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel("Registro de Alquileres")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
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
        label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        info_label = QLabel("Aquí se registrarán los gastos asociados a los equipos")
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
        label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        info_label = QLabel("Aquí se gestionarán los pagos a los operadores de equipos")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(label)
        layout.addWidget(info_label)
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def _crear_menu(self):
        """Crea el menú principal de la aplicación"""
        menubar = self.menuBar()
        # Menú Archivo
        archivo_menu = menubar.addMenu("Archivo")
        archivo_menu.addAction("Crear Backup Manual...", self._crear_backup_manual)
        archivo_menu.addAction("Información del Último Backup", self._info_ultimo_backup)
        archivo_menu.addSeparator()
        archivo_menu.addAction("Salir", self.close)
        
        # Menú Gestión
        gestion_menu = menubar.addMenu("Gestión")
        gestion_menu.addAction("🏗️ Equipos", self._gestionar_equipos)
        gestion_menu.addAction("👥 Clientes", self._gestionar_clientes)
        gestion_menu.addAction("👷 Operadores", self._gestionar_operadores)
        gestion_menu.addSeparator()
        gestion_menu.addAction("🔧 Mantenimientos", self._gestionar_mantenimientos)
        gestion_menu.addAction("💵 Gestionar Abonos", self._gestionar_abonos)
        
        # Menú Reportes
        reportes_menu = menubar.addMenu("Reportes")
        reportes_menu.addAction("📄 Exportar Detallado Equipos", self._generar_reporte_detallado_pdf)
        reportes_menu.addAction("👷 Reporte Operadores", self._generar_reporte_operadores)
        reportes_menu.addAction("💰 Estado de Cuenta Cliente", self._generar_estado_cuenta_cliente_pdf)
        reportes_menu.addAction("📊 Estado de Cuenta General", self._generar_estado_cuenta_general_pdf)
        
        # Menú Configuración
        config_menu = menubar.addMenu("Configuración")
        
        # Submenú de temas
        temas_menu = QMenu("Tema", self)
        for tema in ThemeManager.get_available_themes():
            action = QAction(tema, self)
            action.triggered.connect(lambda checked, t=tema: self._cambiar_tema(t))
            temas_menu.addAction(action)
        config_menu.addMenu(temas_menu)
        
        config_menu.addSeparator()
        config_menu.addAction("🔑 Configurar Credenciales Firebase", self._configurar_firebase)
        config_menu.addAction("📋 Configurar Backups", self._configurar_backups)
        config_menu.addAction("⚙️ Ver Configuración", self._ver_configuracion)
        
        # Menú Ayuda
        ayuda_menu = menubar.addMenu("Ayuda")
        ayuda_menu.addAction("Acerca de", self._acerca_de)
        ayuda_menu.addAction("Documentación", self._abrir_documentacion)
    
    def _cargar_datos_iniciales(self):
        """
        Carga los datos iniciales desde Firebase (Mapas de Nombres)
        Con pequeñas pausas entre consultas para evitar exceder cuotas de Firestore
        """
        try:
            logger.info("Cargando mapas de nombres...")
            
            # Cargar con pequeñas pausas para evitar rate limiting
            equipos = self.fm.obtener_equipos(activo=None)
            self.equipos_mapa = {eq['id']: eq.get('nombre', 'N/A') for eq in equipos}
            
            # Pequeña pausa entre consultas
            import time
            time.sleep(0.3)
            
            clientes = self.fm.obtener_entidades(tipo='Cliente', activo=None)
            self.clientes_mapa = {cl['id']: cl.get('nombre', 'N/A') for cl in clientes}
            
            time.sleep(0.3)
            
            operadores = self.fm.obtener_entidades(tipo='Operador', activo=None)
            self.operadores_mapa = {op['id']: op.get('nombre', 'N/A') for op in operadores}

            time.sleep(0.3)
            
            # Cargar mapas globales
            self.cuentas_mapa = self.fm.obtener_mapa_global('cuentas')
            time.sleep(0.3)
            self.categorias_mapa = self.fm.obtener_mapa_global('categorias')
            time.sleep(0.3)
            self.subcategorias_mapa = self.fm.obtener_mapa_global('subcategorias')
            
            logger.info("Mapas cargados. Actualizando título y poblando tabs...")
            
            # Actualizar título con contador de equipos
            self.setWindowTitle(f"EQUIPOS 4.0 - {len(self.equipos_mapa)} Equipos Totales")
            
            mapas_completos = {
                "equipos": self.equipos_mapa,
                "clientes": self.clientes_mapa,
                "operadores": self.operadores_mapa,
                "cuentas": self.cuentas_mapa,
                "categorias": self.categorias_mapa,
                "subcategorias": self.subcategorias_mapa
            }
            
            # Pasar mapas a cada tab
            self.dashboard_tab.actualizar_mapas(mapas_completos)
            self.registro_tab.actualizar_mapas(mapas_completos)
            self.gastos_tab.actualizar_mapas(mapas_completos)
            self.pagos_tab.actualizar_mapas(mapas_completos)

            # --- ELIMINADO: Tab de reportes movido al menú superior ---
            # Los reportes ahora se generan desde el menú "Reportes"
            # if not self.reportes_tab:
            #     self.reportes_tab = ReportesTab(
            #         self.fm,
            #         storage_manager=self.sm,
            #         clientes_mapa=self.clientes_mapa,
            #         operadores_mapa=self.operadores_mapa,
            #         equipos_mapa=self.equipos_mapa
            #     )
            #     self.tabs.addTab(self.reportes_tab, "Reportes")
            # --- FIN DE CÓDIGO ELIMINADO ---
            
            # Ahora, refrescar los datos
            self.dashboard_tab.refrescar_datos()
            self.registro_tab._cargar_alquileres()
            self.gastos_tab._cargar_gastos()
            self.pagos_tab._cargar_pagos()

        except Exception as e:
            logger.critical(f"Error CRÍTICO al cargar datos iniciales: {e}", exc_info=True)
            
            # Mensaje específico para problemas de cuota
            error_msg = str(e)
            if "429" in error_msg or "Quota exceeded" in error_msg or "ResourceExhausted" in error_msg:
                QMessageBox.critical(
                    self, 
                    "Error: Cuota de Firebase Excedida",
                    "Se ha excedido la cuota de Firebase/Firestore.\n\n"
                    "Posibles soluciones:\n"
                    "1. Espere unos minutos e intente nuevamente\n"
                    "2. Verifique su plan de Firebase (¿Free tier?)\n"
                    "3. Revise el uso en Firebase Console\n"
                    "4. Considere actualizar a un plan de pago\n\n"
                    "La aplicación se cerrará. Por favor, espere e intente nuevamente."
                )
            else:
                QMessageBox.critical(
                    self, 
                    "Error Crítico de Carga",
                    f"No se pudieron cargar los datos iniciales.\n\n"
                    f"Error: {e}\n\n"
                    "Posibles causas:\n"
                    "- Faltan índices en Firebase/Firestore\n"
                    "- Problemas de conexión a Internet\n"
                    "- Credenciales incorrectas\n\n"
                    "Por favor, revise los logs y reinicie la aplicación."
                )
            self.setWindowTitle("EQUIPOS 4.0 - ERROR DE CARGA")
            # Cerrar la aplicación después del error crítico
            QTimer.singleShot(1000, self.close)
    
    # ==================== Métodos del Menú Archivo ====================
    
    def _crear_backup_manual(self):
        """Crea un backup manual de los datos de Firebase"""
        if not self.bm:
            QMessageBox.warning(self, "Backup no disponible",
                              "El sistema de backups no está configurado.")
            return
        
        reply = QMessageBox.question(self, "Crear Backup",
                                     "¿Desea crear un backup manual ahora?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.bm.crear_backup():
                    # Actualizar configuración
                    self.config['backup']['ultimo_backup'] = datetime.now().isoformat()
                    guardar_configuracion(self.config)
                    
                    QMessageBox.information(self, "Éxito",
                                          f"Backup creado exitosamente en:\n{self.config['backup']['ruta_backup_sqlite']}")
                else:
                    QMessageBox.warning(self, "Error",
                                      "No se pudo crear el backup. Revise los logs.")
            except Exception as e:
                QMessageBox.critical(self, "Error",
                                   f"Error al crear backup:\n{e}")
    
    def _info_ultimo_backup(self):
        """Muestra información del último backup"""
        if not self.bm:
            QMessageBox.information(self, "Backup no disponible",
                                  "El sistema de backups no está configurado.")
            return
        
        try:
            info = self.bm.obtener_info_backup()
            if info:
                mensaje = f"Información del último backup:\n\n"
                mensaje += f"Fecha: {info['fecha_backup']}\n"
                mensaje += f"Versión: {info['version']}\n"
                # ... (resto de los campos de info)
                mensaje += f"Tamaño: {info.get('tamanio_archivo', 0) / 1024:.2f} KB"
                
                QMessageBox.information(self, "Información de Backup", mensaje)
            else:
                QMessageBox.information(self, "Sin Backup",
                                      "No se ha creado ningún backup aún.")
        except Exception as e:
            QMessageBox.warning(self, "Error",
                              f"No se pudo obtener información del backup:\n{e}")
    
    # ==================== Métodos del Menú Gestión ====================
    
    def _gestionar_equipos(self):
        """Abre ventana de gestión de equipos"""
        from dialogos.gestion_equipos_dialog import GestionEquiposDialog
        try:
            dialog = GestionEquiposDialog(self.fm, parent=self)
            dialog.exec()
            # Recargar mapas después de la gestión
            self._cargar_datos_iniciales()
        except Exception as e:
            logger.error(f"Error al abrir gestión de equipos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al abrir gestión de equipos:\n{e}")
    
    def _gestionar_clientes(self):
        """Abre ventana de gestión de clientes"""
        from dialogos.gestion_entidad_dialog import GestionEntidadDialog
        try:
            dialog = GestionEntidadDialog(self.fm, tipo_entidad='Cliente', parent=self)
            dialog.exec()
            # Recargar mapas después de la gestión
            self._cargar_datos_iniciales()
        except Exception as e:
            logger.error(f"Error al abrir gestión de clientes: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al abrir gestión de clientes:\n{e}")
    
    def _gestionar_operadores(self):
        """Abre ventana de gestión de operadores"""
        from dialogos.gestion_entidad_dialog import GestionEntidadDialog
        try:
            dialog = GestionEntidadDialog(self.fm, tipo_entidad='Operador', parent=self)
            dialog.exec()
            # Recargar mapas después de la gestión
            self._cargar_datos_iniciales()
        except Exception as e:
            logger.error(f"Error al abrir gestión de operadores: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al abrir gestión de operadores:\n{e}")
    
    def _gestionar_mantenimientos(self):
        """Abre ventana de gestión de mantenimientos"""
        QMessageBox.information(self, "En desarrollo",
                              "La ventana de gestión de mantenimientos estará disponible próximamente.")
    
    # ==================== Métodos del Menú Configuración ====================
    
    def _cambiar_tema(self, tema: str):
        """Cambia el tema de la aplicación"""
        try:
            app = QApplication.instance()
            ThemeManager.apply_theme(app, tema)
            
            # Guardar en configuración
            if 'app' not in self.config:
                self.config['app'] = {}
            self.config['app']['tema'] = tema
            guardar_configuracion(self.config)
            
            QMessageBox.information(self, "Tema Cambiado",
                                  f"El tema '{tema}' se ha aplicado correctamente.\n\n"
                                  "Nota: Algunos cambios pueden requerir reiniciar la aplicación.")
        except Exception as e:
            QMessageBox.warning(self, "Error",
                              f"No se pudo cambiar el tema:\n{e}")
    
    def _configurar_firebase(self):
        """
        Permite configurar las credenciales de Firebase desde la interfaz.
        El usuario puede seleccionar un archivo de credenciales y configurar el bucket de Storage.
        """
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFormLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Configurar Firebase")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        # Información actual
        info_label = QLabel("<b>Configuración Actual de Firebase:</b>")
        layout.addWidget(info_label)
        
        form_layout = QFormLayout()
        
        # Credenciales actuales
        creds_actual = self.config.get('firebase', {}).get('credentials_path', 'No configurado')
        lbl_creds = QLabel(creds_actual)
        form_layout.addRow("Credenciales:", lbl_creds)
        
        # Project ID actual
        project_actual = self.config.get('firebase', {}).get('project_id', 'No configurado')
        lbl_project = QLabel(project_actual)
        form_layout.addRow("Project ID:", lbl_project)
        
        # Storage Bucket actual
        bucket_actual = self.config.get('firebase', {}).get('storage_bucket', 'No configurado')
        lbl_bucket = QLabel(bucket_actual)
        form_layout.addRow("Storage Bucket:", lbl_bucket)
        
        layout.addLayout(form_layout)
        
        # Sección para nueva configuración
        layout.addWidget(QLabel("\n<b>Nueva Configuración:</b>"))
        
        new_form = QFormLayout()
        
        # Campo para archivo de credenciales
        creds_layout = QHBoxLayout()
        self.txt_creds_path = QLineEdit()
        self.txt_creds_path.setPlaceholderText("Ruta al archivo de credenciales...")
        self.txt_creds_path.setText(creds_actual if creds_actual != 'No configurado' else '')
        creds_layout.addWidget(self.txt_creds_path)
        
        btn_browse_creds = QPushButton("📁 Buscar")
        btn_browse_creds.clicked.connect(lambda: self._browse_credentials_file(self.txt_creds_path))
        creds_layout.addWidget(btn_browse_creds)
        new_form.addRow("Credenciales:", creds_layout)
        
        # Campo para Project ID
        self.txt_project_id = QLineEdit()
        self.txt_project_id.setPlaceholderText("ID del proyecto Firebase...")
        self.txt_project_id.setText(project_actual if project_actual != 'No configurado' else '')
        new_form.addRow("Project ID:", self.txt_project_id)
        
        # Campo para Storage Bucket
        self.txt_storage_bucket = QLineEdit()
        self.txt_storage_bucket.setPlaceholderText("nombre-proyecto.appspot.com")
        self.txt_storage_bucket.setText(bucket_actual if bucket_actual != 'No configurado' else '')
        new_form.addRow("Storage Bucket:", self.txt_storage_bucket)
        
        layout.addLayout(new_form)
        
        # Nota informativa
        note_label = QLabel(
            "\n<i>Nota: Después de guardar los cambios, la aplicación se reiniciará "
            "automáticamente para aplicar la nueva configuración de Firebase.</i>"
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
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            line_edit.setText(file_path)
    
    def _save_firebase_config(self, dialog):
        """Guarda la nueva configuración de Firebase y reinicia la aplicación."""
        try:
            # Validar que se ingresaron los datos requeridos
            creds_path = self.txt_creds_path.text().strip()
            project_id = self.txt_project_id.text().strip()
            storage_bucket = self.txt_storage_bucket.text().strip()
            
            if not creds_path or not project_id:
                QMessageBox.warning(self, "Datos Incompletos",
                                  "Debe proporcionar al menos la ruta de credenciales y el Project ID.")
                return
            
            # Verificar que el archivo de credenciales existe
            if not os.path.exists(creds_path):
                QMessageBox.warning(self, "Archivo No Encontrado",
                                  f"No se encontró el archivo de credenciales:\n{creds_path}")
                return
            
            # Actualizar configuración
            if 'firebase' not in self.config:
                self.config['firebase'] = {}
            
            self.config['firebase']['credentials_path'] = creds_path
            self.config['firebase']['project_id'] = project_id
            
            if storage_bucket:
                self.config['firebase']['storage_bucket'] = storage_bucket
            
            # Guardar configuración
            guardar_configuracion(self.config)
            
            # Informar al usuario
            respuesta = QMessageBox.question(
                self,
                "Configuración Guardada",
                "La configuración de Firebase se guardó correctamente.\n\n"
                "¿Desea reiniciar la aplicación ahora para aplicar los cambios?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            dialog.accept()
            
            if respuesta == QMessageBox.StandardButton.Yes:
                # Reiniciar la aplicación
                logger.info("Reiniciando aplicación para aplicar nueva configuración Firebase...")
                QApplication.quit()
                os.execl(sys.executable, sys.executable, *sys.argv)
            
        except Exception as e:
            logger.error(f"Error al guardar configuración Firebase: {e}", exc_info=True)
            QMessageBox.critical(self, "Error",
                               f"Error al guardar la configuración:\n{e}")
    
    def _configurar_backups(self):
        """Abre ventana de configuración de backups"""
        QMessageBox.information(self, "En desarrollo",
                              "La configuración de backups estará disponible próximamente.")
    
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
    
    # ==================== Métodos del Menú Ayuda ====================
    
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
        QMessageBox.information(self, "Documentación",
                              "La documentación está disponible en la carpeta 'docs' del proyecto:\n\n"
                              "- arquitectura_equipos_firebase.md\n"
                              "- migracion_desde_progain.md\n"
                              "- backups_sqlite.md\n\n"
                              "También puede consultar el archivo README.md")
    
    # ==================== Métodos del Menú Reportes ====================
    
    def _generar_reporte_detallado_pdf(self):
        """Genera reporte detallado de equipos con conduces desde Firebase Storage"""
        QMessageBox.information(self, "En desarrollo",
                              "Reporte Detallado de Equipos en desarrollo.\n\n"
                              "Incluirá conduces desde Firebase Storage.")
    
    def _generar_reporte_operadores(self):
        """Genera reporte de operadores"""
        QMessageBox.information(self, "En desarrollo",
                              "Reporte de Operadores en desarrollo.")
    
    def _generar_estado_cuenta_cliente_pdf(self):
        """Genera estado de cuenta de un cliente individual o general"""
        try:
            # Importar diálogo y generador de reportes
            from dialogos.estado_cuenta_dialog import EstadoCuentaDialog
            from report_generator import ReportGenerator
            
            # Abrir diálogo para seleccionar cliente y fechas
            dialog = EstadoCuentaDialog(
                self.fm,
                {
                    'clientes_mapa': self.clientes_mapa,
                    'equipos_mapa': self.equipos_mapa,
                    'operadores_mapa': self.operadores_mapa
                },
                self
            )
            
            if not dialog.exec():
                return  # Usuario canceló
            
            filtros = dialog.get_filtros()
            logger.info(f"Generando estado de cuenta con filtros: {filtros}")
            
            # Obtener datos de alquileres (facturas)
            facturas = self.fm.obtener_alquileres_para_reporte(
                cliente_id=filtros['cliente_id'],
                fecha_inicio=filtros['fecha_inicio'],
                fecha_fin=filtros['fecha_fin']
            )
            
            # Obtener abonos
            abonos = self.fm.obtener_abonos(
                cliente_id=filtros['cliente_id'],
                fecha_inicio=filtros['fecha_inicio'],
                fecha_fin=filtros['fecha_fin']
            )
            
            if not facturas:
                QMessageBox.information(
                    self, "Sin datos",
                    "No hay alquileres para el período o filtros seleccionados."
                )
                return
            
            # Enriquecer datos con nombres (cliente, equipo, operador)
            for row in facturas:
                # Agregar nombres desde mapas
                if 'cliente_id' in row:
                    row['cliente_nombre'] = next(
                        (nombre for nombre, id_val in self.clientes_mapa.items() if id_val == row['cliente_id']),
                        'Desconocido'
                    )
                if 'equipo_id' in row:
                    row['equipo_nombre'] = next(
                        (nombre for nombre, id_val in self.equipos_mapa.items() if id_val == row['equipo_id']),
                        'Desconocido'
                    )
                if 'operador_id' in row:
                    row['operador_nombre'] = next(
                        (nombre for nombre, id_val in self.operadores_mapa.items() if id_val == row['operador_id']),
                        'Desconocido'
                    )
                
                # Asegurar que conduce y ubicación existan
                if 'conduce' not in row or row['conduce'] is None:
                    row['conduce'] = ''
                if 'ubicacion' not in row or row['ubicacion'] is None:
                    row['ubicacion'] = ''
                
                # Agregar columna para ruta de Storage (si existe)
                if 'conduce_storage_path' in row and row['conduce_storage_path']:
                    row['CondStorage'] = row['conduce_storage_path']
                else:
                    row['CondStorage'] = ''
            
            # Calcular totales
            total_facturado = sum(float(row.get('monto', 0)) for row in facturas)
            total_abonado = sum(float(row.get('monto', 0)) for row in abonos)
            saldo = total_facturado - total_abonado
            
            # Definir título y nombre de cliente
            if filtros['cliente_id'] is None:
                title = "ESTADO DE CUENTA GENERAL"
                cliente_nombre = "GENERAL"
            else:
                title = f"ESTADO DE CUENTA - {filtros['cliente_nombre']}"
                cliente_nombre = filtros['cliente_nombre']
            
            # Mapeo de columnas para el PDF
            column_map = {
                'fecha': 'Fecha',
                'conduce': 'Conduce',
                'ubicacion': 'Ubicación',
                'equipo_nombre': 'Equipo',
                'horas': 'Horas',
                'monto': 'Monto',
                'CondStorage': 'CondStorage'  # Columna para rutas de Firebase Storage
            }
            
            # Si es reporte general, incluir cliente
            if filtros['cliente_id'] is None:
                column_map['cliente_nombre'] = 'Cliente'
            
            date_range = f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"
            
            # Pedir ubicación para guardar PDF
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
            
            # Generar PDF
            rg = ReportGenerator(
                data=facturas,
                title=title,
                cliente=cliente_nombre,
                date_range=date_range,
                currency_symbol="RD$",
                storage_manager=self.sm,
                column_map=column_map
            )
            
            # Agregar información de abonos y totales
            rg.abonos = abonos
            rg.total_facturado = total_facturado
            rg.total_abonado = total_abonado
            rg.saldo = saldo
            
            ok, error = rg.to_pdf(file_path)
            
            if ok:
                QMessageBox.information(
                    self, "Éxito",
                    f"Estado de cuenta generado exitosamente:\n{file_path}"
                )
            else:
                QMessageBox.critical(
                    self, "Error",
                    f"No se pudo generar el estado de cuenta:\n{error}"
                )
        
        except Exception as e:
            logger.error(f"Error al generar estado de cuenta: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Error",
                f"Error al generar estado de cuenta:\n{str(e)}"
            )
    
    def _generar_estado_cuenta_general_pdf(self):
        """Genera estado de cuenta general de todos los clientes"""
        # Reutilizar la misma función - el diálogo permite seleccionar "Todos"
        self._generar_estado_cuenta_cliente_pdf()
    
    # ==================== Métodos del Menú Gestión ====================
    
    def _gestionar_abonos(self):
        """Abre ventana de gestión de abonos"""
        try:
            from dialogos.ventana_gestion_abonos import VentanaGestionAbonos
            
            dialogo = VentanaGestionAbonos(self.fm, self.mapas, parent=self)
            dialogo.exec()
            
        except Exception as e:
            logger.error(f"Error al abrir gestión de abonos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al abrir gestión de abonos:\n{str(e)}")