"""
Gestor de almacenamiento en Firebase Cloud Storage para EQUIPOS 4.0
Maneja la subida y descarga de archivos (conduces, facturas, etc.)
"""

import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple
import tempfile
from firebase_admin import storage

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False
    logger.warning("PIL/Pillow no disponible. Las imágenes no se procesarán.")


class StorageManager:
    def __init__(self, bucket_name: str | None = None, service_account_json: str | None = None):
        """
        Constructor tolerante: intenta usar firebase_admin si ya está inicializado,
        o inicializarlo si se le pasa service_account_json. Si falla, deja self.bucket = None.
        """
        from firebase_admin import storage as fb_storage, credentials as fb_credentials, initialize_app as fb_initialize_app, _apps as fb_apps
        import logging

        self.logger = logging.getLogger(__name__)
        self.bucket = None

        try:
            # Si no hay app y nos dieron credenciales, intentamos inicializar
            if not fb_apps:
                if service_account_json:
                    try:
                        cred = fb_credentials.Certificate(service_account_json)
                        fb_initialize_app(cred, {'storageBucket': bucket_name} if bucket_name else None)
                        self.logger.info("firebase_admin inicializado desde StorageManager.")
                    except Exception as init_err:
                        self.logger.warning(f"No se pudo inicializar firebase_admin desde StorageManager: {init_err}")
                else:
                    self.logger.debug("firebase_admin no inicializado y no se proporcionaron credenciales a StorageManager.")

            # Si ahora hay apps, intentar obtener bucket
            if fb_apps:
                try:
                    self.bucket = fb_storage.bucket()
                    self.logger.info(f"StorageManager: bucket inicializado: {getattr(self.bucket, 'name', None)}")
                except Exception as e:
                    self.logger.warning(f"No se pudo obtener bucket desde firebase_admin: {e}")
                    self.bucket = None
            else:
                self.bucket = None

        except Exception as e:
            self.logger.error(f"Error inicializando StorageManager: {e}", exc_info=True)
            self.bucket = None

    def is_available(self) -> bool:
        return self.bucket is not None
    
    def _process_image(self, origen_path: str, width: int = 1200, height: int = 800) -> Optional[str]:
        """
        Procesa una imagen: redimensiona manteniendo aspecto y convierte a JPEG con compresión optimizada.
        Retorna la ruta del archivo temporal procesado o None si falla.
        
        Para archivos muy grandes, usa compresión más agresiva.
        """
        if not _HAS_PIL:
            logger.warning("PIL no disponible, no se procesará la imagen")
            return None
        
        try:
            with Image.open(origen_path) as img:
                # Obtener tamaño original
                original_size = img.size
                original_pixels = original_size[0] * original_size[1]
                
                # Convertir a RGB
                img = img.convert("RGB")
                
                # Redimensionar manteniendo aspecto
                img.thumbnail((width, height), Image.Resampling.LANCZOS)
                new_size = img.size
                
                logger.info(f"Redimensionando imagen de {original_size} a {new_size}")
                
                # Determinar calidad de JPEG basada en el tamaño
                # Más píxeles en la imagen original = más compresión
                if original_pixels > 3000000:  # >3 megapixels
                    quality = 70
                elif original_pixels > 1500000:  # >1.5 megapixels
                    quality = 80
                else:
                    quality = 85
                
                # Guardar en archivo temporal
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpeg')
                temp_path = temp_file.name
                temp_file.close()
                
                img.save(temp_path, format="JPEG", quality=quality, optimize=True)
                
                # Verificar tamaño final
                final_size = os.path.getsize(temp_path)
                final_size_mb = final_size / 1024 / 1024
                logger.info(f"Imagen procesada y guardada: {temp_path} ({final_size_mb:.2f} MB, calidad={quality})")
                
                return temp_path
                
        except Exception as e:
            logger.error(f"Error al procesar imagen {origen_path}: {e}", exc_info=True)
            return None
    
    def guardar_conduce(self, 
                       file_path: str,
                       alquiler: dict,
                       procesar_imagen: bool = True) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Sube un archivo de conduce a Firebase Storage.
        
        Estructura de carpetas en Storage:
        - Ruta: conduces/AÑO/MES/<identificador>.ext
        - AÑO: Año de la fecha del alquiler (o año actual si no hay fecha)
        - MES: Mes de la fecha del alquiler en formato 02 dígitos (01-12)
        - <identificador>: Número de conduce del alquiler, o ID del alquiler si no hay número
        - .ext: Extensión del archivo original (.jpeg si se procesa imagen)
        
        Ejemplo: conduces/2025/11/00575.jpeg
        
        Args:
            file_path: Ruta local al archivo seleccionado
            alquiler: Diccionario con datos del alquiler (debe tener 'fecha' y opcionalmente 'conduce')
            procesar_imagen: Si True, procesa imágenes antes de subir (redimensiona y optimiza)
        
        Returns:
            Tuple (éxito, url_publica, ruta_storage, mensaje_error)
            - éxito: True si se subió correctamente
            - url_publica: URL pública para acceder al archivo
            - ruta_storage: Ruta interna del archivo en Firebase Storage
            - mensaje_error: Descripción del error si falló, None si fue exitoso
        """
        try:
            logger.info(f"=== Iniciando subida de conduce ===")
            logger.info(f"Archivo: {file_path}")
            logger.info(f"Alquiler: {alquiler}")
            logger.info(f"Procesar imagen: {procesar_imagen}")
            
            # Validar archivo existe
            if not os.path.exists(file_path):
                error_msg = f"Archivo no encontrado: {file_path}"
                logger.error(error_msg)
                return False, None, None, error_msg
            
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / 1024 / 1024
            logger.info(f"Tamaño del archivo: {file_size} bytes ({file_size_mb:.2f} MB)")
            
            # Advertir si el archivo es muy grande (>10MB para Storage)
            if file_size_mb > 10:
                logger.warning(f"Archivo muy grande ({file_size_mb:.2f} MB). Firebase Storage puede tener límites.")
            
            # Determinar año/mes desde fecha del alquiler
            # Se usa la fecha del alquiler para organizar en carpetas por año y mes
            # Si no hay fecha válida, se usa la fecha actual como fallback
            fecha_str = alquiler.get('fecha', '')
            try:
                fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                anio = str(fecha_dt.year)
                mes = f"{fecha_dt.month:02d}"
            except Exception:
                # Fallback a fecha actual si la fecha del alquiler no es válida
                now = datetime.now()
                anio = str(now.year)
                mes = f"{now.month:02d}"
                logger.warning(f"Fecha del alquiler no válida ({fecha_str}), usando fecha actual")
            
            # Generar nombre de archivo basado en el número de conduce o ID del alquiler
            # Prioridad: 1) número de conduce, 2) ID del alquiler, 3) 'temp'
            conduce_num = alquiler.get('conduce') or alquiler.get('id', 'temp')
            ext = Path(file_path).suffix.lower()
            
            # Procesar imagen si es necesario
            archivo_a_subir = file_path
            archivo_temporal = None
            
            if procesar_imagen and ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
                archivo_procesado = self._process_image(file_path)
                if archivo_procesado:
                    archivo_a_subir = archivo_procesado
                    archivo_temporal = archivo_procesado
                    ext = '.jpeg'
            
            # Construir ruta en Storage siguiendo el esquema: conduces/YYYY/MM/<identificador>.ext
            # Donde YYYY es el año, MM es el mes (01-12) y <identificador> es el número de conduce o ID
            nombre_archivo = f"{conduce_num}{ext}"
            storage_path = f"conduces/{anio}/{mes}/{nombre_archivo}"
            logger.info(f"Ruta de storage construida: {storage_path}")
            
            # Subir archivo
            logger.info(f"Subiendo archivo a Storage: {archivo_a_subir} -> {storage_path}")
            blob = self.bucket.blob(storage_path)
            
            try:
                blob.upload_from_filename(archivo_a_subir)
                logger.info(f"Archivo subido exitosamente a Storage")
            except Exception as e_upload:
                error_msg = f"Error al subir archivo a Storage: {str(e_upload)}"
                logger.error(error_msg, exc_info=True)
                # Limpiar archivo temporal si se creó
                if archivo_temporal and os.path.exists(archivo_temporal):
                    try:
                        os.unlink(archivo_temporal)
                    except Exception:
                        pass
                return False, None, None, error_msg
            
            # Intentar hacer el archivo público, si falla usar URL firmada
            try:
                blob.make_public()
                url_publica = blob.public_url
                logger.info(f"Archivo hecho público: {url_publica}")
            except Exception as e_public:
                # Si no se puede hacer público, generar URL firmada (válida por 7 días)
                logger.warning(f"No se pudo hacer público el archivo: {e_public}")
                logger.info("Generando URL firmada temporal...")
                try:
                    # Generar URL firmada requiere credenciales con permisos adecuados
                    from google.auth import credentials as google_credentials
                    url_publica = blob.generate_signed_url(
                        version="v4",
                        expiration=timedelta(days=7),
                        method="GET"
                    )
                    logger.info(f"URL firmada generada (válida 7 días)")
                except Exception as e_signed:
                    logger.error(f"Error al generar URL firmada: {e_signed}", exc_info=True)
                    # Como último recurso, usar la URL pública sin verificar
                    logger.warning("Usando URL pública sin verificar como fallback")
                    url_publica = blob.public_url
            
            # Limpiar archivo temporal si se creó
            if archivo_temporal and os.path.exists(archivo_temporal):
                try:
                    os.unlink(archivo_temporal)
                except Exception:
                    pass
            
            logger.info(f"Conduce subido: {storage_path} -> {url_publica}")
            return True, url_publica, storage_path, None
            
        except Exception as e:
            error_msg = f"Error al guardar conduce: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, None, None, error_msg
    
    def descargar_conduce(self, storage_path: str, destino_local: Optional[str] = None) -> Optional[str]:
        """
        Descarga un archivo desde Storage.
        
        Args:
            storage_path: Ruta del archivo en Storage
            destino_local: Ruta local donde guardar (si None, usa temp)
        
        Returns:
            Ruta local del archivo descargado o None si falla
        """
        try:
            blob = self.bucket.blob(storage_path)
            
            if not destino_local:
                # Crear archivo temporal
                ext = Path(storage_path).suffix
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                destino_local = temp_file.name
                temp_file.close()
            
            blob.download_to_filename(destino_local)
            logger.info(f"Archivo descargado: {storage_path} -> {destino_local}")
            return destino_local
            
        except Exception as e:
            logger.error(f"Error al descargar archivo {storage_path}: {e}")
            return None
    
    def eliminar_conduce(self, storage_path: str) -> bool:
        """
        Elimina un archivo de Storage.
        
        Args:
            storage_path: Ruta del archivo en Storage
        
        Returns:
            True si se eliminó correctamente
        """
        try:
            blob = self.bucket.blob(storage_path)
            blob.delete()
            logger.info(f"Archivo eliminado de Storage: {storage_path}")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar archivo {storage_path}: {e}")
            return False
    
    def obtener_url_publica(self, storage_path: str) -> Optional[str]:
        """
        Obtiene la URL pública de un archivo en Storage.
        
        Args:
            storage_path: Ruta del archivo en Storage
        
        Returns:
            URL pública o None si falla
        """
        try:
            blob = self.bucket.blob(storage_path)
            # Hacer público si no lo está
            if not blob.public_url:
                blob.make_public()
            return blob.public_url
        except Exception as e:
            logger.error(f"Error al obtener URL pública de {storage_path}: {e}")
            return None
    
    def obtener_url_firmada(self, storage_path: str, expiracion_minutos: int = 60) -> Optional[str]:
        """
        Genera una URL firmada temporal para acceder a un archivo privado.
        
        Args:
            storage_path: Ruta del archivo en Storage
            expiracion_minutos: Minutos hasta que expire la URL
        
        Returns:
            URL firmada o None si falla
        """
        try:
            from datetime import timedelta
            blob = self.bucket.blob(storage_path)
            url = blob.generate_signed_url(expiration=timedelta(minutes=expiracion_minutos))
            return url
        except Exception as e:
            logger.error(f"Error al generar URL firmada de {storage_path}: {e}")
            return None


    # --- NUEVO: método de conveniencia para el PDF / UI ---
    def get_download_url(self, storage_path: str, prefer_firmada: bool = True, expiracion_minutos: int = 120) -> Optional[str]:
        """
        Devuelve una URL de descarga usable para un objeto en Storage.
        - Si storage_path ya es una URL http(s), se retorna tal cual.
        - Si prefer_firmada=True (por defecto), intenta generar URL firmada;
          si falla, intenta pública.
        - Si prefer_firmada=False, intenta hacer público; si falla, genera firmada.
        """
        if not storage_path:
            return None
        if isinstance(storage_path, str) and storage_path.startswith(("http://", "https://")):
            return storage_path
        try:
            if prefer_firmada:
                url = self.obtener_url_firmada(storage_path, expiracion_minutos=expiracion_minutos)
                if url:
                    return url
                return self.obtener_url_publica(storage_path)
            else:
                url = self.obtener_url_publica(storage_path)
                if url:
                    return url
                return self.obtener_url_firmada(storage_path, expiracion_minutos=expiracion_minutos)
        except Exception as e:
            logger.warning(f"get_download_url: error con {storage_path}: {e}")
            return None
        
    # Añadir este método a tu clase StorageManager existente (solo el método):
    def generate_signed_url(self, blob_path: str, expiration_days: int = 7) -> str:
        """
        Genera una URL firmada (V4) para un objeto en el bucket, válida 'expiration_days' días.
        Requiere que StorageManager esté inicializado con credenciales de servicio válidas.
        """
        from datetime import timedelta
        from google.cloud.storage import Blob

        if not getattr(self, "bucket", None):
            raise RuntimeError("StorageManager no tiene bucket inicializado")

        blob: Blob = self.bucket.blob(blob_path)
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=int(expiration_days)),
            method="GET",
        )
        return str(url)