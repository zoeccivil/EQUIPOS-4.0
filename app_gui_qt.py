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
from config_manager import cargar_configuracion, guardar_configuracion
from theme_manager import ThemeManager

# Importar tabs
from dashboard_tab import DashboardTab
from registro_alquileres_tab import RegistroAlquileresTab
from gastos_equipos_tab import TabGastosEquipos
from pagos_operadores_tab import TabPagosOperadores

logger = logging.getLogger(__name__)

class AppGUI(QMainWindow):
    """
    Ventana principal de la aplicación EQUIPOS 4.0.
    Gestiona tabs, menús y configuración general.
    """
    
    def __init__(self, firebase_manager: FirebaseManager, backup_manager: BackupManager = None, config: dict = None):
        super().__init__()
        self.fm = firebase_manager
        self.bm = backup_manager
        self.config = config or {}
        
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
        
        # Tab de Registro de Alquileres
        self.registro_tab = RegistroAlquileresTab(self.fm)
        self.tabs.addTab(self.registro_tab, "Registro de Alquileres")
        
        # Tab de Gastos de Equipos
        self.gastos_tab = TabGastosEquipos(self.fm)
        self.tabs.addTab(self.gastos_tab, "Gastos de Equipos")
        
        # Tab de Pagos a Operadores
        self.pagos_tab = TabPagosOperadores(self.fm)
        self.tabs.addTab(self.pagos_tab, "Pagos a Operadores")
        
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
        gestion_menu.addAction("Equipos", self._gestionar_equipos)
        gestion_menu.addAction("Clientes", self._gestionar_clientes)
        gestion_menu.addAction("Operadores", self._gestionar_operadores)
        gestion_menu.addSeparator()
        gestion_menu.addAction("Mantenimientos", self._gestionar_mantenimientos)
        
        # Menú Reportes
        reportes_menu = menubar.addMenu("Reportes")
        reportes_menu.addAction("Reporte de Alquileres", self._reporte_alquileres)
        reportes_menu.addAction("Reporte de Gastos", self._reporte_gastos)
        reportes_menu.addAction("Reporte de Mantenimientos", self._reporte_mantenimientos)
        reportes_menu.addSeparator()
        reportes_menu.addAction("Estado de Cuenta", self._estado_cuenta)
        
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
        config_menu.addAction("Configurar Backups", self._configurar_backups)
        config_menu.addAction("Ver Configuración", self._ver_configuracion)
        
        # Menú Ayuda
        ayuda_menu = menubar.addMenu("Ayuda")
        ayuda_menu.addAction("Acerca de", self._acerca_de)
        ayuda_menu.addAction("Documentación", self._abrir_documentacion)
    
    def _cargar_datos_iniciales(self):
        """
        Carga los datos iniciales desde Firebase (Mapas de Nombres)
        ¡MODIFICADO (V7)!
        """
        try:
            logger.info("Cargando mapas de nombres...")
            
            # --- ¡CAMBIO CLAVE! ---
            # Pedimos TODOS los equipos y entidades, no solo los activos=True
            # activo=None significa "sin filtro de activo"
            equipos = self.fm.obtener_equipos(activo=None)
            self.equipos_mapa = {eq['id']: eq.get('nombre', 'N/A') for eq in equipos}
            
            clientes = self.fm.obtener_entidades(tipo='Cliente', activo=None)
            self.clientes_mapa = {cl['id']: cl.get('nombre', 'N/A') for cl in clientes}
            
            operadores = self.fm.obtener_entidades(tipo='Operador', activo=None)
            self.operadores_mapa = {op['id']: op.get('nombre', 'N/A') for op in operadores}
            # --- FIN DEL CAMBIO ---

            # Cargar mapas globales
            self.cuentas_mapa = self.fm.obtener_mapa_global('cuentas')
            self.categorias_mapa = self.fm.obtener_mapa_global('categorias')
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
            
            # Ahora, refrescar los datos
            self.dashboard_tab.refrescar_datos()
            self.registro_tab._cargar_alquileres()
            self.gastos_tab._cargar_gastos()
            self.pagos_tab._cargar_pagos()

        except Exception as e:
            logger.critical(f"Error CRÍTICO al cargar datos iniciales: {e}", exc_info=True)
            QMessageBox.critical(self, "Error Crítico de Carga",
                              f"No se pudieron cargar los datos iniciales (¿Faltan índices en Firebase?):\n\n{e}\n\nPor favor, revise los logs, cree los índices en Firebase y reinicie la aplicación.")
            self.setWindowTitle("EQUIPOS 4.0 - ERROR DE CARGA (REVISAR ÍNDICES)")
    
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
        QMessageBox.information(self, "En desarrollo",
                              "La ventana de gestión de equipos estará disponible próximamente.")
    
    def _gestionar_clientes(self):
        """Abre ventana de gestión de clientes"""
        QMessageBox.information(self, "En desarrollo",
                              "La ventana de gestión de clientes estará disponible próximamente.")
    
    def _gestionar_operadores(self):
        """Abre ventana de gestión de operadores"""
        QMessageBox.information(self, "En desarrollo",
                              "La ventana de gestión de operadores estará disponible próximamente.")
    
    def _gestionar_mantenimientos(self):
        """Abre ventana de gestión de mantenimientos"""
        QMessageBox.information(self, "En desarrollo",
                              "La ventana de gestión de mantenimientos estará disponible próximamente.")
    
    # ==================== Métodos del Menú Reportes ====================
    
    def _reporte_alquileres(self):
        """Genera reporte de alquileres"""
        QMessageBox.information(self, "En desarrollo",
                              "El reporte de alquileres estará disponible próximamente.")
    
    def _reporte_gastos(self):
        """Genera reporte de gastos"""
        QMessageBox.information(self, "En desarrollo",
                              "El reporte de gastos estará disponible próximamente.")
    
    def _reporte_mantenimientos(self):
        """Genera reporte de mantenimientos"""
        QMessageBox.information(self, "En desarrollo",
                              "El reporte de mantenimientos estará disponible próximamente.")
    
    def _estado_cuenta(self):
        """Genera estado de cuenta"""
        QMessageBox.information(self, "En desarrollo",
                              "El estado de cuenta estará disponible próximamente.")
    
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