import zipfile
import os

class ZipUtils:
    """Utilidad para manejar archivos ZIP."""

    @staticmethod
    def comprimir_archivos(nombre_zip, archivos):
        """Comprime una lista de archivos en un solo archivo ZIP."""
        try:
            with zipfile.ZipFile(nombre_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for archivo in archivos:
                    if os.path.exists(archivo):
                        zipf.write(archivo, os.path.basename(archivo))
            return nombre_zip
        except Exception as e:
            print(f"Error comprimiendo archivos: {e}")
            return None

    @staticmethod
    def descomprimir_archivo(nombre_zip, ruta_destino):
        """Descomprime el contenido de un archivo ZIP en la ruta especificada."""
        try:
            with zipfile.ZipFile(nombre_zip, 'r') as zipf:
                zipf.extractall(ruta_destino)
            return True
        except Exception as e:
            print(f"Error descomprimiendo archivo: {e}")
            return False

    @staticmethod
    def listar_contenido(nombre_zip):
        """Retorna una lista con los nombres de archivos incluidos en el ZIP."""
        try:
            with zipfile.ZipFile(nombre_zip, 'r') as zipf:
                return zipf.namelist()
        except Exception as e:
            print(f"Error listando contenido ZIP: {e}")
            return []
