import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os

class PDF(FPDF):
    def __init__(self, orientation='P', unit='mm', format='Letter'):
        super().__init__(orientation, unit, format)
        self.set_auto_page_break(auto=True, margin=15)
        self.title_main = ""
        self.cliente = ""
        self.periodo = ""
        self.fecha_generacion = ""

    def set_header_info(self, title_main, cliente, periodo, fecha_generacion):
        self.title_main = title_main
        self.cliente = cliente
        self.periodo = periodo
        self.fecha_generacion = fecha_generacion

    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, self.title_main, ln=1, align='L')
        self.set_font('Helvetica', '', 11)
        if self.cliente:
            self.cell(0, 6, f"Cliente: {self.cliente}", ln=1, align='L')
        if self.periodo:
            self.cell(0, 6, f"Período: {self.periodo}", ln=1, align='L')
        if self.fecha_generacion:
            self.cell(0, 6, f"Fecha de generación: {self.fecha_generacion}", ln=1, align='L')
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

class ReportGenerator:
    def __init__(
        self, data=None, title="", cliente="", project_name="", date_range="", currency_symbol="RD$",
        abonos=None, total_facturado=None, total_abonado=None, saldo=None, carpeta_conduces=None, column_map=None
    ):
        self.title_main = title or "Estado de Cuenta de Alquileres"
        self.cliente = cliente
        self.project_name = project_name
        self.date_range = date_range
        self.currency = currency_symbol
        self.fecha_generacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.abonos = abonos if abonos is not None else []
        self.total_facturado = total_facturado
        self.total_abonado = total_abonado
        self.saldo = saldo
        self.carpeta_conduces = carpeta_conduces
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

    def to_pdf(self, filepath):
        if self.df.empty:
            print("[DEBUG] DataFrame está vacío, no hay datos para exportar.")
            return False, "No hay datos para exportar."

        try:
            print("[DEBUG] DataFrame columns:", self.df.columns)
            # Puedes mostrar también algunas filas para revisar
            print("[DEBUG] Primeras filas del DataFrame:")
            print(self.df.head())

            pdf = FPDF(orientation='P', unit='mm', format='Letter')
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            # Encabezado
            pdf.set_font('Helvetica', 'B', 16)
            pdf.cell(0, 10, f"ESTADO DE CUENTA - {self.cliente}", ln=1, align='L')
            pdf.set_font('Helvetica', '', 11)
            pdf.cell(0, 6, f"Período: {self.date_range}", ln=1, align='L')
            pdf.cell(0, 6, f"Fecha de generación: {self.fecha_generacion}", ln=1, align='L')
            pdf.ln(2)

            # Detalle de Servicios Facturados
            pdf.set_font('Helvetica', 'B', 13)
            pdf.cell(0, 8, "Detalle de Servicios Facturados", ln=1)
            pdf.ln(2)

            equipos = self.df['Equipo'].unique() if 'Equipo' in self.df.columns else ['(Sin equipo)']
            resumen_equipos = []
            # Ajuste: hoja carta -> 215mm ancho, márgenes 15mm -> usable ~185mm
            col_widths = [30, 28, 60, 20, 47]  # Fecha, Conduce, Ubicación, Horas, Monto

            for eq in equipos:
                df_eq = self.df[self.df['Equipo'] == eq] if 'Equipo' in self.df.columns else self.df

                pdf.set_font('Helvetica', 'B', 11)
                pdf.cell(0, 7, f"Equipo: {str(eq).upper()}", ln=1)
                pdf.ln(1)

            cols = ['Fecha', 'Conduce', 'Ubicación', 'Horas', 'Monto']
            col_widths = [30, 28, 60, 20, 47]  # Puedes ajustar estos valores

            for eq in equipos:
                df_eq = self.df[self.df['Equipo'] == eq] if 'Equipo' in self.df.columns else self.df

                pdf.set_font('Helvetica', 'B', 11)
                pdf.cell(0, 7, f"Equipo: {str(eq).upper()}", ln=1)
                pdf.ln(1)

                # Header tabla
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_fill_color(79, 129, 189)
                pdf.set_text_color(255, 255, 255)
                for idx, col in enumerate(cols):
                    pdf.cell(col_widths[idx], 8, col, border=1, align='C', fill=True)
                pdf.ln()

                # Filas
                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(0, 0, 0)
                fill = False
                total_horas = 0
                total_monto = 0
                for _, row in df_eq.iterrows():
                    pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
                    # --- Aquí nos aseguramos de que los campos siempre existan o sean ''
                    fecha = str(row.get('Fecha', ''))
                    conduce = str(row.get('Conduce', '')) if pd.notna(row.get('Conduce', '')) else ''
                    ubicacion = str(row.get('Ubicación', '')) if pd.notna(row.get('Ubicación', '')) else ''
                    horas = f"{float(row.get('Horas', 0) or 0):.2f}" if pd.notna(row.get('Horas', 0)) else ''
                    monto = f"{self.currency} {float(row.get('Monto', 0) or 0):,.2f}" if pd.notna(row.get('Monto', 0)) else ''

                    fila = [fecha, conduce, ubicacion, horas, monto]
                    total_horas += float(row.get('Horas', 0) or 0)
                    total_monto += float(row.get('Monto', 0) or 0)
                    for idx, value in enumerate(fila):
                        align = 'R' if cols[idx] in ['Horas', 'Monto'] else 'L'
                        pdf.cell(col_widths[idx], 7, value, border=1, align=align, fill=True)
                    pdf.ln()
                    fill = not fill

                # Total por equipo bien alineado
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_fill_color(220, 230, 241)
                pdf.cell(col_widths[0] + col_widths[1] + col_widths[2], 8, f"TOTAL {str(eq).upper()}", border=1, align='R', fill=True)
                pdf.cell(col_widths[3], 8, f"{total_horas:.2f}", border=1, align='R', fill=True)
                pdf.cell(col_widths[4], 8, f"{self.currency} {total_monto:,.2f}", border=1, align='R', fill=True)
                pdf.ln(10)
                resumen_equipos.append({'Equipo': eq, 'Total Horas': total_horas, 'Total Monto': total_monto})

            # ... resto del método ...

            # Resumen General por Equipos
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 9, "Resumen General por Equipos", ln=1)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_fill_color(31, 99, 33)
            pdf.set_text_color(255, 255, 255)
            resumen_cols = [80, 35, 45]
            pdf.cell(resumen_cols[0], 8, "Equipo", border=1, align='C', fill=True)
            pdf.cell(resumen_cols[1], 8, "Total Horas", border=1, align='C', fill=True)
            pdf.cell(resumen_cols[2], 8, "Total Monto", border=1, align='C', fill=True)
            pdf.ln()
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(0, 0, 0)
            total_general_horas = 0
            total_general_monto = 0
            for row in resumen_equipos:
                pdf.set_font('Helvetica', 'B', 10)
                pdf.cell(resumen_cols[0], 7, str(row['Equipo']).upper(), border=1, align='L')
                pdf.set_font('Helvetica', '', 10)
                pdf.cell(resumen_cols[1], 7, f"{row['Total Horas']:.2f}", border=1, align='R')
                pdf.cell(resumen_cols[2], 7, f"{self.currency} {row['Total Monto']:,.2f}", border=1, align='R')
                pdf.ln()
                total_general_horas += row['Total Horas']
                total_general_monto += row['Total Monto']
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(resumen_cols[0], 8, "TOTAL GENERAL", border=1, align='R', fill=True)
            pdf.cell(resumen_cols[1], 8, f"{total_general_horas:.2f}", border=1, align='R', fill=True)
            pdf.cell(resumen_cols[2], 8, f"{self.currency} {total_general_monto:,.2f}", border=1, align='R', fill=True)
            pdf.ln(15)

            # --- Tabla de resumen financiero ---
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 9, "Resumen Financiero", ln=1)
            pdf.set_font('Helvetica', '', 11)
            pdf.cell(60, 8, "Total Facturado:", border=1, align='R')
            pdf.cell(40, 8, f"{self.currency} {total_general_monto:,.2f}", border=1, align='R')
            pdf.ln()
            pdf.cell(60, 8, "Total Abonado:", border=1, align='R')
            pdf.cell(40, 8, f"{self.currency} {self.total_abonado:,.2f}", border=1, align='R')
            pdf.ln()
            pdf.set_font('Helvetica', 'B', 11)
            pdf.cell(60, 8, "Saldo Pendiente:", border=1, align='R')
            pdf.set_text_color(220, 30, 30) if self.saldo > 0 else pdf.set_text_color(0, 100, 0)
            pdf.cell(40, 8, f"{self.currency} {self.saldo:,.2f}", border=1, align='R')
            pdf.set_text_color(0, 0, 0)
            pdf.ln(10)

            # --- Abonos Detallados (identificados) ---
            if self.abonos:
                pdf.set_font('Helvetica', 'B', 11)
                pdf.cell(0, 8, "Detalle de Abonos", ln=1)
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_fill_color(79, 129, 189)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(25, 8, "Abono", border=1, align='C', fill=True)
                pdf.cell(35, 8, "Fecha", border=1, align='C', fill=True)
                pdf.cell(40, 8, "Monto", border=1, align='C', fill=True)
                pdf.cell(85, 8, "Comentario", border=1, align='C', fill=True)
                pdf.ln()
                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(0, 0, 0)
                total_abonos = 0
                for idx, ab in enumerate(self.abonos, 1):
                    nombre_abono = f"Abono {idx}"
                    fecha = ab.get('fecha', '')
                    monto = ab.get('monto', 0)
                    comentario = ab.get('comentario', '')
                    pdf.cell(25, 7, nombre_abono, border=1)
                    pdf.cell(35, 7, str(fecha), border=1)
                    pdf.cell(40, 7, f"{self.currency} {float(monto):,.2f}", border=1, align='R')
                    pdf.cell(85, 7, str(comentario), border=1)
                    pdf.ln()
                    total_abonos += float(monto)
                # Total de abonos al final
                pdf.set_font('Helvetica', 'B', 10)
                pdf.cell(60, 8, "Total Abonado", border=1, align='R', fill=True)
                pdf.cell(40, 8, f"{self.currency} {total_abonos:,.2f}", border=1, align='R', fill=True)
                pdf.cell(85, 8, "", border=1)  # Comentario vacío
                pdf.ln(8)

            # --- ANEXOS DE CONDUCES ---
            print("[DEBUG] Entrando a anexos de conduces")
            if self.carpeta_conduces and 'ConduceAdjunto' in self.df.columns:
                adjuntos = self.df[self.df['ConduceAdjunto'].notna() & (self.df['ConduceAdjunto'] != '')]
                print("[DEBUG] Adjuntos encontrados:", len(adjuntos))
                if not adjuntos.empty:
                    print("[DEBUG] Primeros paths adjuntos:", adjuntos['ConduceAdjunto'].head())
                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 14)
                    pdf.cell(0, 12, "Anexos: Conduces de Servicios", ln=1)
                    pdf.ln(2)
                    for _, row in adjuntos.iterrows():
                        relative_path = row['ConduceAdjunto']
                        full_path = os.path.normpath(os.path.join(self.carpeta_conduces, relative_path))
                        print(f"[DEBUG] Intentando anexar archivo: {full_path} (rel: {relative_path})")
                        info_conduce = f"Conduce No: {row.get('Conduce', 'N/A')} | Fecha: {row.get('Fecha', '')} | Equipo: {row.get('Equipo', '')}"
                        pdf.set_font('Helvetica', 'I', 11)
                        pdf.multi_cell(0, 7, info_conduce)
                        pdf.ln(1)
                        if os.path.exists(full_path):
                            try:
                                pdf.image(full_path, w=pdf.w - 30)
                                print(f"[DEBUG] Imagen anexada correctamente: {full_path}")
                            except Exception as e:
                                print(f"[DEBUG] Error al anexar imagen: {e}")
                                pdf.set_font('Helvetica', '', 10)
                                pdf.cell(0, 6, f"(No se pudo cargar el adjunto: {relative_path})", ln=1)
                        else:
                            print(f"[DEBUG] Adjunto no encontrado: {full_path}")
                            pdf.set_font('Helvetica', '', 10)
                            pdf.cell(0, 6, f"(Adjunto no encontrado: {relative_path})", ln=1)
                        pdf.add_page()
            else:
                print("[DEBUG] No se encontró la columna 'ConduceAdjunto' o carpeta_conduces no está definida.")

            pdf.output(filepath)
            return True, None
        except Exception as e:
            print(f"[DEBUG] Excepción en to_pdf: {e}")
            return False, str(e)


    def to_pdf_general(self, filepath):
        """
        NUEVA FUNCIÓN: Genera un estado de cuenta general para MÚLTIPLES clientes,
        utilizando tablas para un formato limpio y organizado.
        """
        if self.df.empty and not self.abonos:
            return False, "No hay datos para exportar."

        try:
            pdf = PDF(orientation='P', unit='mm', format='Letter')
            pdf.set_header_info(
                title_main=self.title_main,
                cliente="TODOS LOS CLIENTES",
                periodo=self.date_range,
                fecha_generacion=self.fecha_generacion
            )
            pdf.add_page()

            # --- Resumen Financiero General al Inicio ---
            pdf.set_font('Helvetica', 'B', 13)
            pdf.cell(0, 8, "Resumen Financiero General", ln=1)
            pdf.set_font('Helvetica', '', 11)
            pdf.cell(60, 8, "Total Facturado:", border=1, align='R')
            pdf.cell(40, 8, f"{self.currency} {self.total_facturado:,.2f}", border=1, align='R')
            pdf.ln()
            pdf.cell(60, 8, "Total Abonado:", border=1, align='R')
            pdf.cell(40, 8, f"{self.currency} {self.total_abonado:,.2f}", border=1, align='R')
            pdf.ln()
            pdf.set_font('Helvetica', 'B', 11)
            pdf.cell(60, 8, "Saldo General Pendiente:", border=1, align='R')
            pdf.set_text_color(220, 30, 30) if self.saldo > 0 else pdf.set_text_color(0, 100, 0)
            pdf.cell(40, 8, f"{self.currency} {self.saldo:,.2f}", border=1, align='R')
            pdf.set_text_color(0, 0, 0)
            pdf.ln(15)

            # --- Detalle por Cliente ---
            df_abonos = pd.DataFrame(self.abonos)
            if 'Cliente' not in self.df.columns:
                 return False, "La columna 'Cliente' no se encontró en los datos."

            is_first_client = True
            for cliente, df_cliente_facturas in self.df.groupby('Cliente'):
                
                if not is_first_client:
                    pdf.add_page()
                is_first_client = False

                pdf.set_font('Helvetica', 'B', 14)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(0, 10, f"Cliente: {cliente}", ln=1, fill=True)
                
                # --- Tabla de Facturas del cliente ---
                pdf.set_font('Helvetica', 'B', 11)
                pdf.cell(0, 8, "Detalle de Facturas", ln=1)
                
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_fill_color(220, 230, 241)
                col_widths_facturas = [25, 25, 80, 25, 30]
                pdf.cell(col_widths_facturas[0], 7, "Fecha", border=1, fill=True, align='C')
                pdf.cell(col_widths_facturas[1], 7, "Conduce", border=1, fill=True, align='C')
                pdf.cell(col_widths_facturas[2], 7, "Equipo", border=1, fill=True, align='C')
                pdf.cell(col_widths_facturas[3], 7, "Horas", border=1, fill=True, align='C')
                pdf.cell(col_widths_facturas[4], 7, "Monto", border=1, fill=True, align='C')
                pdf.ln()

                pdf.set_font('Helvetica', '', 9)
                total_facturado_cliente = 0
                for _, row in df_cliente_facturas.iterrows():
                    pdf.cell(col_widths_facturas[0], 6, str(row.get('Fecha', '')), border=1)
                    pdf.cell(col_widths_facturas[1], 6, str(row.get('Conduce', '')), border=1)
                    pdf.cell(col_widths_facturas[2], 6, str(row.get('Equipo', '')), border=1)
                    pdf.cell(col_widths_facturas[3], 6, f"{row.get('Horas', 0):.2f}", border=1, align='R')
                    pdf.cell(col_widths_facturas[4], 6, f"{self.currency} {row.get('Monto', 0):,.2f}", border=1, align='R')
                    pdf.ln()
                    total_facturado_cliente += row.get('Monto', 0)
                
                pdf.ln(5)

                # --- Tabla de Abonos del cliente ---
                total_abonado_cliente = 0
                df_cliente_abonos = pd.DataFrame()
                if not df_abonos.empty and 'cliente_nombre' in df_abonos.columns:
                    df_cliente_abonos = df_abonos[df_abonos['cliente_nombre'] == cliente]
                
                if not df_cliente_abonos.empty:
                    total_abonado_cliente = df_cliente_abonos['monto'].sum()
                    pdf.set_font('Helvetica', 'B', 11)
                    pdf.cell(0, 8, "Detalle de Abonos", ln=1)

                    pdf.set_font('Helvetica', 'B', 9)
                    col_widths_abonos = [30, 35, 120]
                    pdf.cell(col_widths_abonos[0], 7, "Fecha", border=1, fill=True, align='C')
                    pdf.cell(col_widths_abonos[1], 7, "Monto", border=1, fill=True, align='C')
                    pdf.cell(col_widths_abonos[2], 7, "Comentario", border=1, fill=True, align='C')
                    pdf.ln()

                    pdf.set_font('Helvetica', '', 9)
                    for _, row in df_cliente_abonos.iterrows():
                        pdf.cell(col_widths_abonos[0], 6, str(row['fecha']), border=1)
                        pdf.cell(col_widths_abonos[1], 6, f"{self.currency} {row.get('monto', 0):,.2f}", border=1, align='R')
                        pdf.cell(col_widths_abonos[2], 6, str(row.get('comentario', '')), border=1)
                        pdf.ln()
                
                pdf.ln(5)

                # --- Resumen del cliente ---
                saldo_cliente = total_facturado_cliente - total_abonado_cliente
                pdf.set_font('Helvetica', 'B', 10)
                pdf.cell(100, 8, "Total Facturado Cliente:", border=1, align='R')
                pdf.cell(40, 8, f"{self.currency} {total_facturado_cliente:,.2f}", border=1, align='R')
                pdf.ln()
                pdf.cell(100, 8, "Total Abonado Cliente:", border=1, align='R')
                pdf.cell(40, 8, f"{self.currency} {total_abonado_cliente:,.2f}", border=1, align='R')
                pdf.ln()
                pdf.set_font('Helvetica', 'B', 11)
                pdf.cell(100, 8, "Saldo Pendiente Cliente:", border=1, align='R')
                pdf.cell(40, 8, f"{self.currency} {saldo_cliente:,.2f}", border=1, align='R')
                pdf.ln()

            pdf.output(filepath)
            return True, filepath
        except Exception as e:
            # Es útil imprimir el error real para depuración
            import traceback
            traceback.print_exc()
            return False, str(e)

# Uso recomendado:
# column_map = {
#     'fecha': 'Fecha', 'conduce': 'Conduce', 'ubicacion': 'Ubicación',
#     'equipo_nombre': 'Equipo', 'horas': 'Horas', 'monto': 'Monto',
#     'conduce_adjunto_path': 'ConduceAdjunto'
# }
# generator = ReportGenerator(
#     data=lista_de_facturas,
#     cliente=nombre_cliente,
#     project_name=nombre_proyecto,
#     date_range=f"{fecha_inicio} a {fecha_fin}",
#     currency_symbol="RD$",
#     abonos=lista_de_abonos,
#     total_facturado=total_facturado,
#     total_abonado=total_abonado,
#     saldo=saldo_pendiente,
#     carpeta_conduces=ruta_dropbox_base,
#     column_map=column_map
# )
# ok, error = generator.to_pdf("estado_cuenta.pdf")
