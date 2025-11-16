from fpdf import FPDF

class PDFUtils:
    """Utilidad para generar reportes PDF."""

    @staticmethod
    def crear_pdf_simple(titulo, contenido, nombre_archivo):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, titulo, ln=True, align="C")
        pdf.set_font("Arial", "", 12)
        for linea in contenido.split('\n'):
            pdf.cell(0, 10, linea, ln=True)
        pdf.output(nombre_archivo)
        return nombre_archivo

    @staticmethod
    def crear_pdf_tabla(titulo, encabezados, filas, nombre_archivo):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, titulo, ln=True, align="C")
        pdf.set_font("Arial", "B", 12)
        for encabezado in encabezados:
            pdf.cell(40, 10, encabezado, 1)
        pdf.ln()
        pdf.set_font("Arial", "", 12)
        for fila in filas:
            for elemento in fila:
                pdf.cell(40, 10, str(elemento), 1)
            pdf.ln()
        pdf.output(nombre_archivo)
        return nombre_archivo
