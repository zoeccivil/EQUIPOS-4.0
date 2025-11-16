import paramiko
import os

class SFTPUtils:
    """Utilidad para operaciones básicas con servidores SFTP."""

    @staticmethod
    def conectar(servidor, usuario, password, puerto=22):
        """Establece conexión SFTP y retorna el objeto SFTP."""
        try:
            transport = paramiko.Transport((servidor, puerto))
            transport.connect(username=usuario, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            return sftp, transport
        except Exception as e:
            print(f"Error conectando a SFTP: {e}")
            return None, None

    @staticmethod
    def listar_archivos(sftp, ruta="."):
        """Lista los archivos en la ruta dada del SFTP."""
        try:
            return sftp.listdir(ruta)
        except Exception as e:
            print(f"Error listando archivos SFTP: {e}")
            return []

    @staticmethod
    def descargar_archivo(sftp, archivo_remoto, archivo_local):
        """Descarga un archivo desde el SFTP."""
        try:
            sftp.get(archivo_remoto, archivo_local)
            return True
        except Exception as e:
            print(f"Error descargando archivo SFTP: {e}")
            return False

    @staticmethod
    def subir_archivo(sftp, archivo_local, archivo_remoto):
        """Sube un archivo al SFTP."""
        try:
            sftp.put(archivo_local, archivo_remoto)
            return True
        except Exception as e:
            print(f"Error subiendo archivo SFTP: {e}")
            return False

    @staticmethod
    def cerrar(sftp, transport):
        """Cierra la conexión SFTP."""
        try:
            if sftp:
                sftp.close()
            if transport:
                transport.close()
            return True
        except Exception as e:
            print(f"Error cerrando conexión SFTP: {e}")
            return False
