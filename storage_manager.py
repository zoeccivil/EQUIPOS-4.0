"""
Gestor de almacenamiento en Firebase Cloud Storage para EQUIPOS 4.0
Maneja la subida y descarga de archivos (conduces, facturas, etc.)
"""

import os
import logging
from pathlib import Path
from datetime import datetime
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
    """
    Gestor de archivos en Firebase Cloud Storage.
    Sube conduces y otros archivos organizados por año/mes.
    """
    
    def __init__(self, bucket_name: str):
        """
        Inicializa el gestor de storage.
        
        Args:
            bucket_name: Nombre del bucket de Firebase Storage (ej: 'mi-proyecto.appspot.com')
        """
        try:
            self.bucket = storage.bucket(bucket_name)
            logger.info(f"Storage inicializado con bucket: {bucket_name}")
        except Exception as e:
            logger.error(f"Error al inicializar Storage: {e}")
            raise
    
    def _process_image(self, origen_path: str, width: int = 1200, height: int = 800) -> Optional[str]:
        """
        Procesa una imagen: redimensiona manteniendo aspecto y convierte a JPEG.
        Retorna la ruta del archivo temporal procesado o None si falla.
        """
        if not _HAS_PIL:
            logger.warning("PIL no disponible, no se procesará la imagen")
            return None
        
        try:
            with Image.open(origen_path) as img:
                # Convertir a RGB
                img = img.convert("RGB")
                # Redimensionar manteniendo aspecto
                img.thumbnail((width, height), Image.Resampling.LANCZOS)
                
                # Guardar en archivo temporal
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpeg')
                temp_path = temp_file.name
                temp_file.close()
                
                img.save(temp_path, format="JPEG", quality=85, optimize=True)
                logger.info(f"Imagen procesada: {origen_path} -> {temp_path}")
                return temp_path
                
        except Exception as e:
            logger.error(f"Error al procesar imagen {origen_path}: {e}")
            return None
    
    def guardar_conduce(self, 
                       file_path: str,
                       alquiler: dict,
                       procesar_imagen: bool = True) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Sube un archivo de conduce a Firebase Storage.
        
        Args:
            file_path: Ruta local al archivo seleccionado
            alquiler: Diccionario con datos del alquiler (debe tener 'fecha' y opcionalmente 'conduce')
            procesar_imagen: Si True, procesa imágenes antes de subir
        
        Returns:
            Tuple (éxito, url_publica, ruta_storage)
        """
        try:
            # Validar archivo existe
            if not os.path.exists(file_path):
                logger.error(f"Archivo no encontrado: {file_path}")
                return False, None, None
            
            # Determinar año/mes desde fecha del alquiler
            fecha_str = alquiler.get('fecha', '')
            try:
                fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                anio = str(fecha_dt.year)
                mes = f"{fecha_dt.month:02d}"
            except Exception:
                # Fallback a fecha actual
                now = datetime.now()
                anio = str(now.year)
                mes = f"{now.month:02d}"
            
            # Generar nombre de archivo
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
            
            # Construir ruta en Storage: conduces/YYYY/MM/conduce_XXX.ext
            nombre_archivo = f"{conduce_num}{ext}"
            storage_path = f"conduces/{anio}/{mes}/{nombre_archivo}"
            
            # Subir archivo
            blob = self.bucket.blob(storage_path)
            blob.upload_from_filename(archivo_a_subir)
            
            # Hacer el archivo público (opcional, puedes usar signed URLs si prefieres)
            blob.make_public()
            url_publica = blob.public_url
            
            # Limpiar archivo temporal si se creó
            if archivo_temporal and os.path.exists(archivo_temporal):
                try:
                    os.unlink(archivo_temporal)
                except Exception:
                    pass
            
            logger.info(f"Conduce subido: {storage_path} -> {url_publica}")
            return True, url_publica, storage_path
            
        except Exception as e:
            logger.error(f"Error al guardar conduce: {e}", exc_info=True)
            return False, None, None
    
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
