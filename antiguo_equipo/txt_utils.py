class TXTUtils:
    """Utilidad para manejar archivos de texto plano."""

    @staticmethod
    def leer_txt(nombre_archivo):
        """Lee un archivo TXT y retorna el contenido como string."""
        try:
            with open(nombre_archivo, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error leyendo TXT: {e}")
            return ""

    @staticmethod
    def escribir_txt(nombre_archivo, contenido):
        """Escribe un string en un archivo TXT."""
        try:
            with open(nombre_archivo, "w", encoding="utf-8") as f:
                f.write(contenido)
            return True
        except Exception as e:
            print(f"Error escribiendo TXT: {e}")
            return False
