import rarfile
import os

class RARUtils:
    """Utilidad para manejar archivos RAR."""

    @staticmethod
    def listar_contenido(nombre_rar):
        """Retorna una lista con los nombres de archivos incluidos en el RAR."""
        try:
            with rarfile.RarFile(nombre_rar) as rf:
                return rf.namelist()
        except Exception as e:
            print(f"Error listando contenido RAR: {e}")
            return []

    @staticmethod
    def extraer_archivo(nombre_rar, ruta_destino="."):
        """Extrae el contenido de un archivo RAR en la ruta especificada."""
        try:
            with rarfile.RarFile(nombre_rar) as rf:
                rf.extractall(path=ruta_destino)
            return True
        except Exception as e:
            print(f"Error extrayendo archivo RAR: {e}")
            return False

    @staticmethod
    def comprimir_archivos(nombre_rar, archivos):
        """RAR no soporta compresión directa desde Python, se recomienda usar utilidad externa."""
        print("Compresión RAR no soportada directamente desde Python. Use WinRAR o una utilidad externa.")
        return False
