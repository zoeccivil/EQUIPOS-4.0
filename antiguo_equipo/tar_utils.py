import tarfile
import os

class TarUtils:
    """Utilidad para manejar archivos TAR y TAR.GZ."""

    @staticmethod
    def comprimir_archivos(nombre_tar, archivos, modo="w:gz"):
        """
        Comprime una lista de archivos en un solo archivo TAR o TAR.GZ.
        modo puede ser 'w' (TAR) o 'w:gz' (TAR.GZ).
        """
        try:
            with tarfile.open(nombre_tar, mode=modo) as tar:
                for archivo in archivos:
                    if os.path.exists(archivo):
                        tar.add(archivo, arcname=os.path.basename(archivo))
            return nombre_tar
        except Exception as e:
            print(f"Error comprimiendo archivos TAR: {e}")
            return None

    @staticmethod
    def descomprimir_archivo(nombre_tar, ruta_destino="."):
        """Descomprime el contenido de un archivo TAR o TAR.GZ en la ruta especificada."""
        try:
            with tarfile.open(nombre_tar, "r:*") as tar:
                tar.extractall(path=ruta_destino)
            return True
        except Exception as e:
            print(f"Error descomprimiendo archivo TAR: {e}")
            return False

    @staticmethod
    def listar_contenido(nombre_tar):
        """Retorna una lista con los nombres de archivos incluidos en el TAR."""
        try:
            with tarfile.open(nombre_tar, "r:*") as tar:
                return tar.getnames()
        except Exception as e:
            print(f"Error listando contenido TAR: {e}")
            return []
