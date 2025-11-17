from ftplib import FTP

class FTPUtils:
    """Utilidad para operaciones básicas con servidores FTP."""

    @staticmethod
    def conectar(servidor, usuario, password, puerto=21):
        """Establece conexión FTP y retorna el objeto FTP."""
        try:
            ftp = FTP()
            ftp.connect(servidor, puerto)
            ftp.login(usuario, password)
            return ftp
        except Exception as e:
            print(f"Error conectando a FTP: {e}")
            return None

    @staticmethod
    def listar_archivos(ftp, ruta="."):
        """Lista los archivos en la ruta dada del FTP."""
        try:
            return ftp.nlst(ruta)
        except Exception as e:
            print(f"Error listando archivos FTP: {e}")
            return []

    @staticmethod
    def descargar_archivo(ftp, archivo_remoto, archivo_local):
        """Descarga un archivo desde el FTP."""
        try:
            with open(archivo_local, 'wb') as f:
                ftp.retrbinary(f"RETR {archivo_remoto}", f.write)
            return True
        except Exception as e:
            print(f"Error descargando archivo FTP: {e}")
            return False

    @staticmethod
    def subir_archivo(ftp, archivo_local, archivo_remoto):
        """Sube un archivo al FTP."""
        try:
            with open(archivo_local, 'rb') as f:
                ftp.storbinary(f"STOR {archivo_remoto}", f)
            return True
        except Exception as e:
            print(f"Error subiendo archivo FTP: {e}")
            return False

    @staticmethod
    def cerrar(ftp):
        """Cierra la conexión FTP."""
        try:
            ftp.quit()
            return True
        except Exception as e:
            print(f"Error cerrando conexión FTP: {e}")
            return False
