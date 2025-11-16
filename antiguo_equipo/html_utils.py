from bs4 import BeautifulSoup

class HTMLUtils:
    """Utilidad para manejar operaciones básicas con archivos HTML."""

    @staticmethod
    def leer_html(nombre_archivo):
        """Lee un archivo HTML y retorna el objeto BeautifulSoup."""
        try:
            with open(nombre_archivo, "r", encoding="utf-8") as f:
                contenido = f.read()
            return BeautifulSoup(contenido, "html.parser")
        except Exception as e:
            print(f"Error leyendo HTML: {e}")
            return None

    @staticmethod
    def escribir_html(nombre_archivo, contenido):
        """Escribe contenido HTML en un archivo."""
        try:
            with open(nombre_archivo, "w", encoding="utf-8") as f:
                f.write(contenido)
            return True
        except Exception as e:
            print(f"Error escribiendo HTML: {e}")
            return False

    @staticmethod
    def extraer_texto(html_soup):
        """Extrae el texto plano de un objeto BeautifulSoup."""
        if html_soup is None:
            return ""
        return html_soup.get_text(separator="\n")
