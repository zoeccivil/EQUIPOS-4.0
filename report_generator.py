"""
Generador de reportes PDF para EQUIPOS 4.0
Adaptado para trabajar con Firebase y Firebase Storage
"""

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib import colors
from datetime import datetime
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generador de reportes PDF con soporte para conduces desde Firebase Storage.
    """
    
    def __init__(
        self,
        data=None,
        title="",
        cliente="",
        date_range="",
        currency_symbol="RD$",
        storage_manager=None,
        column_map=None
    ):
        """
        Inicializa el generador de reportes.
        
        Args:
            data: Lista de diccionarios con datos a incluir en el reporte
            title: Título del reporte
            cliente: Nombre del cliente
            date_range: Rango de fechas del reporte
            currency_symbol: Símbolo de la moneda (por defecto "RD$")
            storage_manager: Instancia de StorageManager para descargar conduces
            column_map: Mapeo de nombres de columnas (original -> display)
        """
        self.title_main = title or "REPORTE DE ALQUILERES"
        self.cliente = cliente
        self.date_range = date_range
        self.currency = currency_symbol
        self.fecha_generacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.storage_manager = storage_manager
        
        # Datos de abonos y totales (para estado de cuenta)
        self.abonos = []
        self.total_facturado = 0
        self.total_abonado = 0
        self.saldo = 0
        
        # Convertir datos a DataFrame
        if data is not None:
            raw_df = pd.DataFrame([dict(row) for row in data])
            if column_map and not raw_df.empty:
                cols_a_usar = [col for col in column_map.keys() if col in raw_df.columns]
                self.df = raw_df[cols_a_usar]
                self.df = self.df.rename(columns=column_map)
            else:
                self.df = raw_df
        else:
            self.df = pd.DataFrame()
        
        # Archivos temporales descargados
        self.temp_files = []
    
    def to_pdf(self, filepath):
        """
        Genera el reporte en formato PDF.
        
        Args:
            filepath: Ruta donde guardar el PDF
            
        Returns:
            tuple: (éxito: bool, mensaje: str)
        """
        if self.df.empty:
            logger.warning("DataFrame está vacío, no hay datos para exportar")
            return False, "No hay datos para exportar."
        
        try:
            logger.info(f"Generando PDF en {filepath}")
            logger.debug(f"Columnas del DataFrame: {self.df.columns.tolist()}")
            logger.debug(f"Primeras filas:\n{self.df.head()}")
            
            # Crear documento PDF
            doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=15*mm, bottomMargin=15*mm)
            elementos = []
            estilos = getSampleStyleSheet()
            
            # Agregar estilo personalizado para alineación derecha
            if 'RightAlign' not in estilos:
                estilos.add(ParagraphStyle(name='RightAlign', alignment=TA_RIGHT))
            if 'CenterAlign' not in estilos:
                estilos.add(ParagraphStyle(name='CenterAlign', alignment=TA_CENTER))
            
            # Encabezado del documento
            elementos.append(Paragraph(f"<b>{self.title_main}</b>", estilos['Title']))
            if self.cliente:
                elementos.append(Paragraph(f"<b>Cliente:</b> {self.cliente}", estilos['Normal']))
            if self.date_range:
                elementos.append(Paragraph(f"<b>Período:</b> {self.date_range}", estilos['Normal']))
            elementos.append(Paragraph(f"<b>Fecha de generación:</b> {self.fecha_generacion}", estilos['Normal']))
            elementos.append(Spacer(1, 5*mm))
            
            # Detalle de Servicios Facturados por Equipo
            elementos.append(Paragraph("<b>Detalle de Servicios Facturados</b>", estilos['Heading2']))
            elementos.append(Spacer(1, 3*mm))
            
            equipos = self.df['Equipo'].unique() if 'Equipo' in self.df.columns else ['(Sin equipo)']
            resumen_equipos = []
            
            # Anchos de columna (total ~185mm para hoja carta con márgenes)
            col_widths = [30*mm, 28*mm, 60*mm, 20*mm, 47*mm]  # Fecha, Conduce, Ubicación, Horas, Monto
            
            for eq in equipos:
                df_eq = self.df[self.df['Equipo'] == eq] if 'Equipo' in self.df.columns else self.df
                
                # Título del equipo
                elementos.append(Paragraph(f"<b>Equipo: {str(eq).upper()}</b>", estilos['Heading3']))
                elementos.append(Spacer(1, 2*mm))
                
                # Encabezados de tabla
                cols = ['Fecha', 'Conduce', 'Ubicación', 'Horas', 'Monto']
                tabla_data = [cols]
                
                # Filas de datos
                total_horas = 0
                total_monto = 0
                
                for _, row in df_eq.iterrows():
                    fecha = str(row.get('Fecha', ''))
                    conduce = str(row.get('Conduce', '')) if pd.notna(row.get('Conduce', '')) else ''
                    ubicacion = str(row.get('Ubicación', '')) if pd.notna(row.get('Ubicación', '')) else ''
                    horas = float(row.get('Horas', 0) or 0)
                    monto = float(row.get('Monto', 0) or 0)
                    
                    horas_str = f"{horas:.2f}" if horas > 0 else ''
                    monto_str = f"{self.currency} {monto:,.2f}" if monto > 0 else ''
                    
                    tabla_data.append([fecha, conduce, ubicacion, horas_str, monto_str])
                    
                    total_horas += horas
                    total_monto += monto
                
                # Fila de totales
                tabla_data.append([
                    '', '', 'TOTAL', 
                    f"{total_horas:.2f}", 
                    f"{self.currency} {total_monto:,.2f}"
                ])
                
                # Crear tabla
                tabla = Table(tabla_data, colWidths=col_widths)
                tabla.setStyle(TableStyle([
                    # Encabezado
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    
                    # Datos
                    ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -2), 9),
                    ('ALIGN', (0, 1), (2, -2), 'LEFT'),
                    ('ALIGN', (3, 1), (-1, -2), 'RIGHT'),
                    
                    # Fila total
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, -1), (-1, -1), 10),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#DCE6F1")),
                    ('ALIGN', (2, -1), (2, -1), 'RIGHT'),
                    ('ALIGN', (3, -1), (-1, -1), 'RIGHT'),
                    
                    # Bordes
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    
                    # Filas alternadas
                    *[('BACKGROUND', (0, i), (-1, i), colors.HexColor("#F5F5F5")) 
                      for i in range(2, len(tabla_data)-1, 2)]
                ]))
                
                elementos.append(tabla)
                elementos.append(Spacer(1, 8*mm))
                
                resumen_equipos.append({
                    'Equipo': eq,
                    'Total Horas': total_horas,
                    'Total Monto': total_monto
                })
            
            # Resumen General por Equipos
            if len(resumen_equipos) > 1:
                elementos.append(PageBreak())
                elementos.append(Paragraph("<b>Resumen General por Equipos</b>", estilos['Heading2']))
                elementos.append(Spacer(1, 3*mm))
                
                resumen_cols = ['Equipo', 'Total Horas', 'Total Monto']
                resumen_data = [resumen_cols]
                
                total_general_horas = 0
                total_general_monto = 0
                
                for row in resumen_equipos:
                    resumen_data.append([
                        str(row['Equipo']).upper(),
                        f"{row['Total Horas']:.2f}",
                        f"{self.currency} {row['Total Monto']:,.2f}"
                    ])
                    total_general_horas += row['Total Horas']
                    total_general_monto += row['Total Monto']
                
                # Total general
                resumen_data.append([
                    'TOTAL GENERAL',
                    f"{total_general_horas:.2f}",
                    f"{self.currency} {total_general_monto:,.2f}"
                ])
                
                resumen_tabla = Table(resumen_data, colWidths=[80*mm, 35*mm, 45*mm])
                resumen_tabla.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1F6321")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    
                    ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#F0F0F0")),
                    ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                
                elementos.append(resumen_tabla)
                elementos.append(Spacer(1, 10*mm))
            
            # Anexos de Conduces (si están disponibles)
            if self.storage_manager and 'CondStorage' in self.df.columns:
                self._agregar_anexos_conduces(elementos, estilos)
            
            # Construir PDF
            doc.build(elementos)
            
            # Limpiar archivos temporales
            self._limpiar_temp_files()
            
            logger.info(f"PDF generado exitosamente: {filepath}")
            return True, f"Reporte generado exitosamente en:\n{filepath}"
            
        except Exception as e:
            logger.error(f"Error al generar PDF: {e}", exc_info=True)
            self._limpiar_temp_files()
            return False, f"Error al generar el reporte: {str(e)}"
    
    def _agregar_anexos_conduces(self, elementos, estilos):
        """
        Agrega una sección de anexos con las imágenes de los conduces.
        
        Args:
            elementos: Lista de elementos del PDF
            estilos: Estilos de ReportLab
        """
        try:
            # Filtrar registros que tengan conduce
            conduces_df = self.df[self.df['CondStorage'].notna() & (self.df['CondStorage'] != '')]
            
            if conduces_df.empty:
                logger.info("No hay conduces para agregar a los anexos")
                return
            
            logger.info(f"Agregando {len(conduces_df)} conduces a los anexos")
            
            # Nueva página para anexos
            elementos.append(PageBreak())
            elementos.append(Paragraph("<b>ANEXOS: Conduces de Servicios</b>", estilos['Heading1']))
            elementos.append(Spacer(1, 5*mm))
            
            # Descargar y agregar cada conduce
            for idx, row in conduces_df.iterrows():
                storage_path = row['CondStorage']
                fecha = row.get('Fecha', '')
                conduce_num = row.get('Conduce', f'Conduce {idx+1}')
                
                # Descargar conduce desde Storage
                temp_path = self._descargar_conduce(storage_path)
                
                if temp_path and os.path.exists(temp_path):
                    # Agregar etiqueta
                    elementos.append(Paragraph(
                        f"<b>Conduce:</b> {conduce_num} | <b>Fecha:</b> {fecha}",
                        estilos['Normal']
                    ))
                    elementos.append(Spacer(1, 2*mm))
                    
                    # Agregar imagen (máximo 180mm de ancho)
                    try:
                        img = Image(temp_path)
                        img._restrictSize(180*mm, 250*mm)  # Máximo ancho y alto
                        elementos.append(img)
                    except Exception as e:
                        logger.warning(f"No se pudo insertar imagen {storage_path}: {e}")
                        elementos.append(Paragraph(
                            f"<i>No se pudo cargar la imagen del conduce</i>",
                            estilos['Normal']
                        ))
                    
                    elementos.append(Spacer(1, 5*mm))
                else:
                    logger.warning(f"No se pudo descargar conduce: {storage_path}")
            
        except Exception as e:
            logger.error(f"Error al agregar anexos de conduces: {e}", exc_info=True)
    
    def _descargar_conduce(self, storage_path):
        """
        Descarga un conduce desde Firebase Storage a un archivo temporal.
        
        Args:
            storage_path: Ruta del archivo en Storage
            
        Returns:
            str: Ruta del archivo temporal o None si falla
        """
        if not self.storage_manager:
            return None
        
        try:
            # Crear archivo temporal
            ext = os.path.splitext(storage_path)[1] or '.jpg'
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            temp_path = temp_file.name
            temp_file.close()
            
            # Descargar desde Storage
            exito = self.storage_manager.descargar_conduce(storage_path, temp_path)
            
            if exito:
                self.temp_files.append(temp_path)
                return temp_path
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return None
                
        except Exception as e:
            logger.error(f"Error al descargar conduce {storage_path}: {e}")
            return None
    
    def _limpiar_temp_files(self):
        """Elimina archivos temporales descargados."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"Archivo temporal eliminado: {temp_file}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo temporal {temp_file}: {e}")
        
        self.temp_files = []
    
    def to_excel(self, filepath):
        """
        Genera el reporte en formato Excel.
        
        Args:
            filepath: Ruta donde guardar el Excel
            
        Returns:
            tuple: (éxito: bool, mensaje: str)
        """
        if self.df.empty:
            return False, "No hay datos para exportar."
        
        try:
            # Exportar DataFrame a Excel
            self.df.to_excel(filepath, index=False, sheet_name='Reporte')
            logger.info(f"Excel generado exitosamente: {filepath}")
            return True, f"Reporte Excel generado exitosamente en:\n{filepath}"
            
        except Exception as e:
            logger.error(f"Error al generar Excel: {e}", exc_info=True)
            return False, f"Error al generar el reporte Excel: {str(e)}"
