from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QFileDialog, QMessageBox, QMenuBar, QMenu
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QTimer
import shutil
from datetime import datetime
from dashboard_tab import DashboardTab
from registro_alquileres_tab import RegistroAlquileresTab
from ventana_gestion_entidad import VentanaGestionEntidad
from ventana_gestion_equipos import VentanaGestionEquipos
from ventana_gestion_mantenimiento import VentanaGestionMantenimientos
from ventana_analisis import VentanaAnalisis
from ventana_analisis_gastos import VentanaAnalisisGastos
from ventana_gestion_abonos import VentanaGestionAbonos
from estado_cuenta_dialog import EstadoCuentaDialog
import sys
from logic import DatabaseManager
from config_manager import cargar_configuracion, guardar_configuracion
from reportes_tab import ReportesTab
import config_manager
from filtros_modal import FiltrosReporteDialog
from DialogoPagoOperador import DialogoPagoOperador
from estado_cuenta_dialog import EstadoCuentaDialog
from PyQt6.QtWidgets import QMessageBox
from report_generator import ReportGenerator
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from report_generator import ReportGenerator
from estado_cuenta_dialog import EstadoCuentaDialog
import unicodedata
from datetime import datetime
from utils_nombre import generar_nombre_archivo
from PyQt6.QtWidgets import QMessageBox
from dialogo_reporte_detallado import DialogoReporteDetallado
from reporte_detallado_pdf import ReporteDetalladoPDF
import os
from dialogo_reporte_operadores import DialogoReporteOperadores
from reporte_operadores import ReporteOperadores
from TabGastosEquipos import TabGastosEquipos
from TabPagosOperadores import TabPagosOperadores

class AppGUI(QMainWindow):
    def __init__(self, db_manager, config):
        super().__init__()
        self.db = db_manager
        self.config = config
        print(f"[DEBUG] AppGUI recibe config: {self.config}")
        self.report_generator = ReportGenerator()
        self.proyecto_actual = None

        # Inicialización de atributos
        self.clientes_mapa = {}
        self.equipos_mapa = {}
        self.operadores_mapa = {}
        self.cliente_filtro = "Todos"
        self.equipo_filtro = "Todos"
        self.operador_filtro = "Todos"
        self.fecha_inicio = None
        self.fecha_fin = None
        self.setWindowTitle("Gestor de Alquileres")
        self.resize(1366, 768)
        self.restart_required = False

        # 1. Crear los tabs primero
        self._create_tabs()

        # 2. Crear el menú (usa self.reportes_tab)
        self._create_menu_bar()

        # 3. Cargar configuración
        self.config = config_manager.cargar_configuracion()

        # 4. Cargar proyecto inicial al arranque
        self.cargar_proyecto_inicial()
        QTimer.singleShot(100, self.cargar_proyecto_inicial)

    def _create_tabs(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.registro_tab = RegistroAlquileresTab(self.db, self.proyecto_actual, config=self.config)
        self.tabs.addTab(self.registro_tab, "Registro de Alquileres")

        self.gastos_equipos_tab = TabGastosEquipos(self.db, proyecto_id=8)
        self.tabs.addTab(self.gastos_equipos_tab, "Gastos Equipos")

        self.pagos_operadores_tab = TabPagosOperadores(self.db, proyecto_id=8)
        self.tabs.addTab(self.pagos_operadores_tab, "Pagos a Operadores")

        self.dashboard_tab = DashboardTab(self.db, self.proyecto_actual)
        self.tabs.addTab(self.dashboard_tab, "Dashboard")

        self.tabs.setCurrentIndex(0)
        
    def _create_menu_bar(self):
        menubar = self.menuBar()
        archivo_menu = menubar.addMenu("Archivo")
        archivo_menu.addAction("Crear Copia de Seguridad...", self._crear_backup)
        archivo_menu.addAction("Restaurar desde Copia de Seguridad...", self._restaurar_backup)
        archivo_menu.addSeparator()
        archivo_menu.addAction("Seleccionar Base de Datos...", self.elegir_base_datos)
        archivo_menu.addSeparator()
        archivo_menu.addAction("Salir", self.close)

        reportes_menu = menubar.addMenu("Reportes")

        reportes_menu.addAction(
            "Exportar Detallado Equipos",
            self.generar_reporte_detallado_pdf
        )
        reportes_menu.addAction(
            "Reporte Operadores",
            self.generar_reporte_operadores
        )
        reportes_menu.addAction(
            "Estado de Cuenta Cliente (Individual o Todos)",
            self.generar_estado_cuenta_cliente_pdf
        )
        reportes_menu.addAction(
            "Estado de Cuenta General (PDF)",
            self.generar_estado_cuenta_general_pdf
        )

        gestion_menu = menubar.addMenu("Gestión")
        gestion_menu.addAction("Clientes", lambda: self._abrir_ventana_gestion("Cliente"))
        gestion_menu.addAction("Operadores", lambda: self._abrir_ventana_gestion("Operador"))
        gestion_menu.addAction("Equipos", self._abrir_ventana_gestion_equipos)
        gestion_menu.addAction("Mantenimiento de Equipos", self._abrir_ventana_mantenimiento)
        gestion_menu.addSeparator()
        gestion_menu.addAction("Gestionar Abonos", self._abrir_ventana_gestion_abonos)

        config_menu = menubar.addMenu("Configuración")
        config_menu.addAction("Seleccionar Carpeta CONDUCES", self.seleccionar_carpeta_conduces)

    def elegir_base_datos(self):
        archivo, _ = QFileDialog.getOpenFileName(
            self, "Selecciona la base de datos", "", "Archivos SQLite (*.db);;Todos los archivos (*)"
        )
        if archivo:
            self.config['database_path'] = archivo
            guardar_configuracion(self.config)
            QMessageBox.information(self, "Configuración", f"¡Ruta guardada!\n{archivo}")
            self.db_manager = DatabaseManager(archivo)
            # Opcional: refrescar las vistas/tabs

    def seleccionar_carpeta_conduces(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        carpeta_actual = self.config.get("carpeta_conduces", "")
        nueva_carpeta = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta base para CONDUCES", carpeta_actual or ""
        )
        if nueva_carpeta:
            self.config["carpeta_conduces"] = nueva_carpeta
            guardar_configuracion(self.config)
            QMessageBox.information(self, "Configuración guardada", f"Carpeta de CONDUCES establecida:\n{nueva_carpeta}")

    def cargar_proyecto_inicial(self):
        proyectos = self.db.obtener_proyectos()
        if not proyectos:
            QMessageBox.critical(self, "Error Base de Datos", "No se encontraron proyectos.")
            return
        proyecto_target = next((p for p in proyectos if p['nombre'] == "EQUIPOS PESADOS ZOEC"), None)
        if proyecto_target:
            self.proyecto_actual = proyecto_target
            # Actualiza los tabs que dependen del proyecto
            self.dashboard_tab.proyecto_actual = self.proyecto_actual
            self.registro_tab.proyecto_actual = self.proyecto_actual
            self.dashboard_tab.configurar_filtros()
            self.registro_tab.poblar_filtros()
            self.registro_tab.refrescar_tabla()
            self.setWindowTitle(f"Gestor de Alquileres - {self.proyecto_actual['nombre']}")
            # --- INTEGRACIÓN DEL NUEVO TAB DE GASTOS (si existe) ---
            if hasattr(self, "gastos_equipos_tab"):
                self.gastos_equipos_tab.proyecto_id = self.proyecto_actual['id']
                self.gastos_equipos_tab._cargar_filtros()
                self.gastos_equipos_tab._cargar_gastos()
            if hasattr(self, "pagos_operadores_tab"):
                self.pagos_operadores_tab.proyecto_id = self.proyecto_actual['id']
                self.pagos_operadores_tab._cargar_filtros()
                self.pagos_operadores_tab._cargar_pagos()
        else:
            QMessageBox.critical(self, "Error de Proyecto", "No se encontró el proyecto 'EQUIPOS PESADOS ZOEC'.")

    def cargar_proyecto(self, proyecto_id):
        self.proyecto_actual = self.db.obtener_proyecto_por_id(proyecto_id)
        self.dashboard_tab.proyecto_actual = self.proyecto_actual
        self.dashboard_tab.configurar_filtros()
        self.registro_tab.proyecto_actual = self.proyecto_actual
        self.registro_tab.refrescar_tabla()
        self.setWindowTitle(f"Gestor de Alquileres - {self.proyecto_actual['nombre']}")

    # Métodos de backup/restauración
    def _crear_backup(self):
        db_path = self.config.get('database_path', '') if self.config else ''
        if not db_path:
            QMessageBox.warning(self, "Advertencia", "No hay base de datos seleccionada.")
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_sugerido = f"backup_progain_{timestamp}.db"
        ruta_destino, _ = QFileDialog.getSaveFileName(self, "Guardar copia de seguridad como...", nombre_sugerido, "Archivos de Base de Datos (*.db)")
        if ruta_destino:
            shutil.copy(db_path, ruta_destino)
            QMessageBox.information(self, "Éxito", f"Copia de seguridad creada en:\n{ruta_destino}")

    def _restaurar_backup(self):
        db_path = self.config.get('database_path', '') if self.config else ''
        if not db_path:
            QMessageBox.warning(self, "Advertencia", "No hay base de datos seleccionada.")
            return
        ruta_backup, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo de copia de seguridad", "", "Archivos de Base de Datos (*.db)")
        if ruta_backup:
            shutil.copy(ruta_backup, db_path)
            QMessageBox.information(self, "Éxito", "Base de datos restaurada correctamente. Reinicia la aplicación.")
            self.restart_required = True
            self.close()

    def _cambiar_base_de_datos(self):
        db_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Base de Datos",
            "",
            "Archivos SQLite (*.db);;Todos los archivos (*)"
        )
        if db_path:
            self.config["database_path"] = db_path
            guardar_configuracion(self.config)
            QMessageBox.information(self, "Base de Datos", f"Seleccionada: {db_path}")

            # 1. Inicializa el nuevo gestor de base de datos
            self.db = DatabaseManager(db_path)

            # 2. Asegura que las tablas núcleo existan **ANTES** de consultar cualquier dato
            if hasattr(self.db, "crear_tablas_nucleo"):
                self.db.crear_tablas_nucleo()
            elif hasattr(self.db, "verificar_estructura"):
                self.db.verificar_estructura()

            # 3. Refresca el proyecto inicial y los tabs
            self.cargar_proyecto_inicial()


    def generar_reporte_detallado_pdf(self):
        if not self.proyecto_actual:
            QMessageBox.warning(self, "Proyecto no cargado", "Debe cargar un proyecto para generar reportes.")
            return


        dialog = DialogoReporteDetallado(self.db, self.proyecto_actual, self)
        if dialog.exec():
            filtros = dialog.get_filtros()
            cliente_idx = dialog.combo_cliente.currentIndex()
            cliente_nombre = dialog.combo_cliente.currentText() if cliente_idx != 0 else "TODOS LOS CLIENTES"
            formato = dialog.formato  # 'pdf' o 'excel'
            moneda = self.proyecto_actual['moneda'] if 'moneda' in self.proyecto_actual.keys() else 'RD$'

            ext = "pdf" if formato == "pdf" else "xlsx"
            nombre_archivo = f"Reporte_Detallado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            ruta_guardar = get_save_file_with_extension(self, formato, nombre_archivo)
            if not ruta_guardar:
                return

            report_gen = ReporteDetalladoPDF(self.db)
            if formato == "pdf":
                ok, resultado = report_gen.exportar(
                    self.proyecto_actual['id'], filtros, cliente_nombre, moneda,
                    nombre_archivo=os.path.basename(ruta_guardar),
                    ruta_forzada=ruta_guardar
                )
            elif formato == "excel":
                ok, resultado = report_gen.exportar_excel(
                    self.proyecto_actual['id'], filtros, cliente_nombre, moneda,
                    nombre_archivo=os.path.basename(ruta_guardar),
                    ruta_forzada=ruta_guardar
                )
            if ok:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Éxito", f"Reporte generado en:\n{resultado}")
            else:
                QMessageBox.warning(self, "Error al generar reporte", str(resultado))


    def generar_reporte_operadores(self):
        from datetime import datetime
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        # 1. Muestra el diálogo de filtros
        dialog = DialogoReporteOperadores(self.db, self.proyecto_actual, self)
        if not dialog.exec():
            return

        filtros = dialog.get_filtros()
        formato = dialog.formato  # 'pdf' o 'excel'
        moneda = self.proyecto_actual['moneda'] if 'moneda' in self.proyecto_actual else 'RD$'
        nombre_archivo = f"Reporte_Operadores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{formato}"

        # 2. Diálogo de guardar
        ruta_guardar, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar reporte como...",
            os.path.join(os.path.expanduser("~"), nombre_archivo),
            "Archivos PDF (*.pdf)" if formato == "pdf" else "Archivos Excel (*.xlsx)"
        )
        if not ruta_guardar:
            return

        # 3. Ejecuta el reporte
        report_gen = ReporteOperadores(self.db)
        if formato == "pdf":
            ok, resultado = report_gen.exportar_pdf(
                self.proyecto_actual['id'], filtros, ruta_guardar, moneda
            )
        elif formato == "excel":
            ok, resultado = report_gen.exportar_excel(
                self.proyecto_actual['id'], filtros, ruta_guardar, moneda
            )
        else:
            QMessageBox.warning(self, "Error", "Formato de reporte no soportado.")
            return

        # 4. Muestra el resultado
        if ok:
            QMessageBox.information(self, "Éxito", f"Reporte generado en:\n{resultado}")
        else:
            QMessageBox.warning(self, "Error al generar reporte", str(resultado))

    def generar_estado_cuenta_cliente_pdf(self):
        if not self.proyecto_actual:
            QMessageBox.warning(self, "Proyecto no cargado", "Debe cargar un proyecto para generar reportes.")
            return

        # Abrir el diálogo para seleccionar cliente y fechas
        dialog = EstadoCuentaDialog(self.db, self.proyecto_actual, self)
        if not dialog.exec():
            return  # Usuario canceló

        filtros = dialog.get_filtros()
        if not filtros:
            QMessageBox.warning(self, "Cliente Requerido", "Por favor, seleccione un cliente.")
            return

        if filtros['cliente_id'] is None:
            # Todos los clientes (reporte global)
            facturas, abonos = self.db.obtener_datos_estado_cuenta_general_global(
                filtros['fecha_inicio'],
                filtros['fecha_fin']
            )
            title = "ESTADO DE CUENTA GENERAL"
            project_name = self.proyecto_actual['nombre']
            cliente_nombre = "GENERAL"
            total_facturado = sum(float(row.get('monto', 0)) for row in facturas)
            total_abonado = sum(float(row.get('monto', 0)) for row in abonos)
        else:
            # Reporte individual
            facturas, abonos = self.db.obtener_datos_estado_cuenta_cliente_global(
                filtros['cliente_id'],
                filtros['fecha_inicio'],
                filtros['fecha_fin']
            )
            title = f"ESTADO DE CUENTA - {filtros['cliente_nombre']}"
            project_name = self.proyecto_actual['nombre']
            cliente_nombre = filtros.get('cliente_nombre', 'Cliente')
            total_facturado = sum(float(row.get('monto', 0)) for row in facturas)
            total_abonado = self.db.obtener_total_abonos_cliente(
                self.proyecto_actual['id'],
                filtros['cliente_id'],
                filtros['fecha_inicio'],
                filtros['fecha_fin']
            )

        saldo = total_facturado - total_abonado

        if not facturas:
            QMessageBox.information(self, "Sin datos", "No hay datos para el período o filtros seleccionados.")
            return

        # --- ¡Asegurarse de que "conduce" y "ubicacion" estén siempre presentes! ---
        for row in facturas:
            if 'conduce' not in row or row['conduce'] is None:
                row['conduce'] = ''
            if 'ubicacion' not in row or row['ubicacion'] is None:
                row['ubicacion'] = ''

        column_map = {
            'fecha': 'Fecha',
            'conduce': 'Conduce',
            'ubicacion': 'Ubicación',
            'equipo_nombre': 'Equipo',
            'horas': 'Horas',
            'monto': 'Monto',
            'conduce_adjunto_path': 'ConduceAdjunto'
        }
        if facturas and 'cliente_nombre' in facturas[0]:
            column_map['cliente_nombre'] = 'Cliente'

        date_range = f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"

        # Nombre de archivo automático usando utilitario
        nombre_archivo = generar_nombre_archivo(cliente_nombre)
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", nombre_archivo, "PDF (*.pdf)")
        if not file_path:
            return

        carpeta_conduces = self.config.get('carpeta_conduces')
        print(f"[DEBUG] (generar_estado_cuenta_cliente_pdf) carpeta_conduces: {carpeta_conduces}")
        print(f"[DEBUG] column_map: {column_map}")
        if facturas:
            print(f"[DEBUG] Primeros facturas: {facturas[:2]}")

        rg = ReportGenerator(
            data=facturas,
            title=title,
            project_name=project_name,
            date_range=date_range,
            currency_symbol=self.proyecto_actual['moneda'],
            column_map=column_map,
            carpeta_conduces=carpeta_conduces,
            abonos=abonos,
            total_facturado=total_facturado,
            total_abonado=total_abonado,
            saldo=saldo
        )
        ok, error = rg.to_pdf(file_path)
        if ok:
            QMessageBox.information(self, "Éxito", f"Reporte generado en:\n{file_path}")
        else:
            QMessageBox.critical(self, "Error", f"No se pudo generar el reporte:\n{error}")
            

    def generar_estado_cuenta_general_pdf(self):
        if not self.proyecto_actual:
            QMessageBox.warning(self, "Proyecto no cargado", "Debe cargar un proyecto para generar reportes.")
            return

        dialog = EstadoCuentaDialog(self.db, self.proyecto_actual, self)
        dialog.combo_cliente.setCurrentText("Todos") # Forzar la selección de "Todos"
        
        if not dialog.exec():
            return # Usuario canceló

        filtros = dialog.get_filtros()
        if filtros['cliente_id'] is not None:
            QMessageBox.warning(self, "Error", "Este botón es solo para el reporte general de todos los clientes.")
            return
            

        # ...
        # 1. Obtener los datos de la base de datos (facturas y abonos)
        # --- LÍNEA MODIFICADA ---
        facturas, abonos = self.db.obtener_datos_estado_cuenta_general_global(
            self.proyecto_actual['id'], # <-- AÑADIR ESTE PARÁMETRO
            filtros['fecha_inicio'],
            filtros['fecha_fin']
        )
        # ...
        
        if not facturas:
            QMessageBox.information(self, "Sin datos", "No hay facturas en el período seleccionado.")
            return
            
        # 2. Calcular totales
        total_facturado = sum(float(row.get('monto', 0)) for row in facturas)
        total_abonado = sum(float(row.get('monto', 0)) for row in abonos)
        saldo = total_facturado - total_abonado

        # 3. Pedir al usuario dónde guardar el archivo
        nombre_archivo = generar_nombre_archivo("ESTADO_DE_CUENTA_GENERAL")
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte General", nombre_archivo, "PDF (*.pdf)")
        if not file_path:
            return

        # 4. Configurar y crear la instancia de ReportGenerator
        column_map = {'fecha': 'Fecha', 'conduce': 'Conduce', 'cliente_nombre': 'Cliente', 'equipo_nombre': 'Equipo', 'monto': 'Monto', 'horas': 'Horas'}
        
        rg = ReportGenerator(
            data=facturas,


            title="ESTADO DE CUENTA GENERAL",
            cliente="TODOS LOS CLIENTES",
            project_name=self.proyecto_actual['nombre'],
            date_range=f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}",
            currency_symbol=self.proyecto_actual.get('moneda', 'RD$'),
            column_map=column_map,
            abonos=abonos,
            total_facturado=total_facturado,
            total_abonado=total_abonado,
            saldo=saldo
        )
        
        # 5. Llamar a la nueva función para generar el PDF
        ok, resultado = rg.to_pdf_general(file_path)

        if ok:
            QMessageBox.information(self, "Éxito", f"Reporte general generado en:\n{resultado}")
        else:
            QMessageBox.critical(self, "Error", f"No se pudo generar el reporte:\n{resultado}")

    def _abrir_ventana_analisis(self):
        dialog = VentanaAnalisis(self.db, self.proyecto_actual)
        dialog.exec()

    def _abrir_ventana_analisis_gastos(self):
        dialog = VentanaAnalisisGastos(self.db, self.proyecto_actual)
        dialog.exec()

    def _abrir_ventana_gestion(self, tipo_entidad):
        dialog = VentanaGestionEntidad(self.db, self.proyecto_actual, tipo_entidad)
        dialog.exec()

    def _abrir_ventana_gestion_equipos(self):
        dialog = VentanaGestionEquipos(self.db, self.proyecto_actual)
        dialog.exec()

    def _abrir_ventana_mantenimiento(self):
        dialog = VentanaGestionMantenimientos(self.db, self.proyecto_actual)
        dialog.exec()

    def _abrir_ventana_gestion_abonos(self):
        dialog = VentanaGestionAbonos(self.db, self.proyecto_actual)
        dialog.exec()

    def _abrir_dialogo_filtros(self):
        dlg = FiltrosReporteDialog(self.db, self)
        if dlg.exec():
            filtros = dlg.get_filters()
            # Ahora puedes usar 'filtros' para tu función de reporte
            print(filtros)
            # Ejemplo: self.generar_reporte_detallado_excel(filtros)



def get_save_file_with_extension(parent, formato, nombre_archivo_sugerido):
    """
    Abre un QFileDialog para guardar archivo, ajustando automáticamente la extensión según el filtro.
    Si el usuario borra la extensión o cambia el tipo, se la repone.
    """
    if formato == "pdf":
        filtro = "Archivos PDF (*.pdf)"
        ext = ".pdf"
    else:
        filtro = "Archivos Excel (*.xlsx)"
        ext = ".xlsx"

    ruta_guardar, _ = QFileDialog.getSaveFileName(
        parent,
        "Guardar reporte como...",
        os.path.join(os.path.expanduser("~"), nombre_archivo_sugerido),
        filtro
    )

    if not ruta_guardar:
        return ""

    # Si el usuario borra la extensión o la cambia, la reponemos según el filtro
    if not ruta_guardar.lower().endswith(ext):
        ruta_guardar += ext
    return ruta_guardar
