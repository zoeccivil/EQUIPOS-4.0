# name=utils/adjuntos.py
"""
Helper para validar rutas y guardar archivos de "conduce".

Uso:
    from adjuntos import guardar_conduce

Esta versión es más robusta que la original:
- Normaliza rutas con pathlib
- Comprueba disponibilidad de la unidad (drive) y hace fallback a ./adjuntos
- Crea carpetas recursivamente con manejo de errores
- Procesa imágenes con Pillow (si está disponible) usando thumbnail para mantener aspecto
- Usa shutil.copy2 para preservar metadatos al copiar
- Devuelve la ruta relativa (con forward slashes) respecto a la carpeta base usada
"""
import os
import shutil
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# Configurar logging (si ya se configuró en la app principal, esto no lo sobreescribe).
logging.basicConfig(filename='progain.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

try:
    from PIL import Image
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False


def _normalize_base_dir(base_dir: str) -> Path:
    """
    Normaliza la ruta base: expande ~, transforma en Path y resuelve sin requerir existencia.
    """
    if not base_dir:
        base_dir = "./adjuntos"
    p = Path(base_dir).expanduser()
    try:
        # strict=False evita excepción si la ruta no existe todavía
        return p.resolve(strict=False)
    except Exception:
        return Path(os.path.abspath(str(p)))


def _ensure_drive_available(base_path: Path) -> bool:
    """
    Comprueba que la unidad/raíz de la ruta exista y sea accesible.
    - Si la ruta es relativa o no tiene letra de unidad (o UNC), devuelve True.
    - Para UNC (\\server\share) y letras de unidad comprueba existencia del root.
    """
    drive = base_path.drive  # en Windows puede ser 'D:' o '\\\\server\\share'
    if not drive:
        return True
    try:
        # Normalizar root path para comprobar existencia
        # Si drive es tipo 'D:' -> root 'D:\\'
        # Si drive es UNC '\\server\share' -> root = drive
        if drive.startswith("\\\\"):
            root = Path(drive)
        else:
            root = Path(drive + os.sep)
        return root.exists()
    except Exception:
        return False


def _safe_makedirs(path: Path) -> Tuple[bool, Optional[str]]:
    """
    Crea directorios de forma segura. Retorna (True, None) o (False, mensaje_error).
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True, None
    except Exception as e:
        logging.exception("Error creando carpeta %s: %s", path, e)
        return False, str(e)


def _process_image(origen: str, destino: str, width: int = 1200, height: int = 800) -> None:
    """
    Procesa la imagen con Pillow: convierte a RGB, ajusta tamaño manteniendo aspecto usando thumbnail
    y guarda como JPEG en destino.
    Lanza excepción si Pillow no está disponible o si ocurre algún error.
    """
    if not _HAS_PIL:
        raise RuntimeError("Pillow no está disponible")
    with Image.open(origen) as img:
        img = img.convert("RGB")
        # thumbnail preserva aspecto y no excede las dimensiones dadas
        img.thumbnail((width, height), Image.LANCZOS)
        # Asegurarse que el directorio destino existe antes de guardar
        dest_path = Path(destino)
        dest_parent = dest_path.parent
        dest_parent.mkdir(parents=True, exist_ok=True)
        img.save(destino, format="JPEG", quality=85, optimize=True)


def guardar_conduce(db_manager,
                    transaccion: dict,
                    file_path: str,
                    config: Optional[dict] = None,
                    width: int = 1200,
                    height: int = 800) -> str:
    """
    Guarda el archivo 'conduce' en la estructura base_dir/<anio>/<mes>/nombre.ext

    Parámetros:
    - db_manager: instancia del gestor de BD (no se usa dentro de esta función por ahora).
    - transaccion: dict que debe contener al menos 'id' y opcional 'fecha' y 'conduce'.
                  fecha esperada en formato 'YYYY-MM-DD' si está presente.
    - file_path: ruta absoluta al archivo origen seleccionado por el usuario.
    - config: dict opcional con clave 'carpeta_conduces' indicando la carpeta base.
    - width, height: dimensiones máximas (para procesar imágenes).

    Retorna:
    - ruta relativa (string) respecto a la carpeta base usada, con forward slashes.

    Lanza:
    - ValueError si faltan parámetros básicos
    - OSError u otras excepciones si la operación de I/O falla
    """
    if not transaccion or not file_path:
        raise ValueError("Falta transacción o archivo origen")

    # Determinar año/mes desde la fecha de la transacción; si falla, usar fecha actual
    fecha_str = transaccion.get('fecha', '')
    try:
        fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
        anio = str(fecha_dt.year)
        mes = f"{fecha_dt.month:02d}"
    except Exception:
        now = datetime.now()
        anio = str(now.year)
        mes = f"{now.month:02d}"

    conduce_num = transaccion.get('conduce') or str(transaccion.get('id', 'noid'))

    # Obtener carpeta base desde config (si dict), si no -> './adjuntos'
    base_dir_raw = None
    if isinstance(config, dict):
        base_dir_raw = config.get('carpeta_conduces') or config.get('carpeta_conductos')  # tolerancia por typo
    if not base_dir_raw:
        base_dir_raw = "./adjuntos"

    base_dir_path = _normalize_base_dir(base_dir_raw)

    # Si la unidad/raíz no está disponible, hacer fallback a ./adjuntos -> luego a tempdir
    if not _ensure_drive_available(base_dir_path):
        logging.warning("Unidad no disponible para base_dir %s. Usando ./adjuntos (fallback)", base_dir_path)
        base_dir_path = _normalize_base_dir("./adjuntos")

    ok, err = _safe_makedirs(base_dir_path)
    if not ok:
        logging.warning("No se pudo crear la carpeta base configurada (%s): %s. Intentando fallback './adjuntos'.", base_dir_raw, err)
        base_dir_path = _normalize_base_dir("./adjuntos")
        ok2, err2 = _safe_makedirs(base_dir_path)
        if not ok2:
            # último recurso: usar carpeta temporal del sistema
            tmp = Path(tempfile.gettempdir()) / "adjuntos_tmp"
            logging.warning("Fallback a tmpdir: %s (detalle: %s)", tmp, err2)
            ok3, err3 = _safe_makedirs(tmp)
            if not ok3:
                raise OSError(f"No se pudo crear ninguna carpeta de destino: {err3}")
            base_dir_path = tmp

    # Construir destino año/mes
    destino_dir = base_dir_path / anio / mes
    ok, err = _safe_makedirs(destino_dir)
    if not ok:
        raise OSError(f"No se pudo crear la carpeta destino: {destino_dir} -> {err}")

    # Preparar nombre destino y copiar/procesar
    origen_path = Path(file_path)
    if not origen_path.exists():
        raise FileNotFoundError(f"Archivo origen no encontrado: {file_path}")

    ext = origen_path.suffix.lower()
    try:
        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
            nombre_archivo = f"{conduce_num}.jpeg"
            destino = destino_dir / nombre_archivo
            try:
                _process_image(str(origen_path), str(destino), width=width, height=height)
            except Exception as e:
                logging.exception("Fallo al procesar imagen con Pillow (%s). Intentando copia directa. Error: %s", origen_path, e)
                shutil.copy2(str(origen_path), str(destino))
        else:
            # Mantener extensión original para archivos no-imagen
            nombre_archivo = f"{conduce_num}{ext}"
            destino = destino_dir / nombre_archivo
            shutil.copy2(str(origen_path), str(destino))
    except Exception as e:
        logging.exception("Error al guardar el conduce: %s -> %s : %s", origen_path, destino_dir, e)
        raise

    # Calcular ruta relativa respecto a la carpeta base utilizada y devolver con forward slashes
    try:
        relative_path = os.path.relpath(str(destino), str(base_dir_path)).replace("\\", "/")
    except Exception:
        # Fallback sencillo si relpath falla
        relative_path = f"{anio}/{mes}/{destino.name}"

    logging.info("Conduce guardado: %s (rel: %s)", destino, relative_path)
    return relative_path