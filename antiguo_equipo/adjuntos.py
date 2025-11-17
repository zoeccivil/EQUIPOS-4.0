# utils/adjuntos.py
"""
Robusto helper para validar rutas y guardar archivos de "conduce".

Ahora con integración opcional para actualizar la transacción en la base de datos:
- Si pasas un db_manager y la transacción contiene 'id', la función intentará actualizar
  el campo conduce_adjunto_path en la tabla transacciones (por defecto).
- Puedes desactivar esa actualización automática pasando update_db=False.

Uso:
    from adjuntos import guardar_conduce

Parámetros principales:
    db_manager: instancia de DatabaseManager (o cualquier objeto que exponga `actualizar_conduce_adjunto`
                o `execute` para hacer el UPDATE).
    transaccion: dict con al menos 'id' (si quieres update automático), opcional 'fecha' y 'conduce'.
    file_path: ruta absoluta del archivo origen.
    config: dict opcional con 'carpeta_conduces'.
    update_db: bool (default True) — si True y se detecta un id en transaccion, se intentará hacer el update en la BD.
"""
import os
import shutil
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# logging (no sobrescribe configuración global si ya existe)
logging.basicConfig(filename='progain.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

try:
    from PIL import Image
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False


def _normalize_base_dir(base_dir: Optional[str]) -> Path:
    if not base_dir:
        base_dir = "./adjuntos"
    p = Path(base_dir).expanduser()
    try:
        return p.resolve(strict=False)
    except Exception:
        return Path(os.path.abspath(str(p)))


def _ensure_drive_available(base_path: Path) -> bool:
    drive = base_path.drive
    if not drive:
        logging.debug("_ensure_drive_available: ruta sin drive -> OK (%s)", base_path)
        return True
    try:
        if drive.startswith("\\\\"):
            root = Path(drive)
        else:
            root = Path(drive + os.sep)
        exists = root.exists()
        logging.debug("_ensure_drive_available: drive=%s exists=%s", drive, exists)
        return exists
    except Exception as e:
        logging.exception("Error comprobando drive %s: %s", drive, e)
        return False


def _safe_makedirs(path: Path) -> Tuple[bool, Optional[str]]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        logging.debug("_safe_makedirs: creado o existía %s", path)
        return True, None
    except Exception as e:
        logging.exception("Error creando carpeta %s: %s", path, e)
        return False, str(e)


def _process_image(origen: str, destino: str, width: int = 1200, height: int = 800) -> None:
    if not _HAS_PIL:
        raise RuntimeError("Pillow no está disponible")
    with Image.open(origen) as img:
        img = img.convert("RGB")
        img.thumbnail((width, height), Image.LANCZOS)
        dest_path = Path(destino)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(destino, format="JPEG", quality=85, optimize=True)


def _attempt_db_update(db_manager, transaccion_id: str, ruta_relativa: str) -> bool:
    """
    Intenta actualizar la transacción con la ruta del adjunto.
    Retorna True si la actualización parece haber tenido éxito, False en otro caso.
    Estrategia:
      1) Si db_manager tiene método 'actualizar_conduce_adjunto(transaccion_id, ruta)', úsalo.
      2) Si no, si tiene método 'execute' o '_ejecutar_consulta', ejecutar UPDATE manual.
    """
    if not db_manager or not transaccion_id:
        return False

    try:
        # Preferir método explícito si existe
        if hasattr(db_manager, "actualizar_conduce_adjunto"):
            ok = db_manager.actualizar_conduce_adjunto(transaccion_id, ruta_relativa)
            logging.debug("_attempt_db_update: usado actualizar_conduce_adjunto -> %s", ok)
            return bool(ok)

        # Si existe execute o _ejecutar_consulta intentar UPDATE directo
        if hasattr(db_manager, "execute"):
            try:
                db_manager.execute("UPDATE transacciones SET conduce_adjunto_path = ? WHERE id = ?", (ruta_relativa, transaccion_id))
                logging.debug("_attempt_db_update: UPDATE via execute OK")
                return True
            except Exception as e:
                logging.exception("_attempt_db_update: fallo UPDATE via execute: %s", e)
                return False

        if hasattr(db_manager, "_ejecutar_consulta"):
            try:
                db_manager._ejecutar_consulta("UPDATE transacciones SET conduce_adjunto_path = :r WHERE id = :id",
                                              {'r': ruta_relativa, 'id': transaccion_id}, commit=True)
                logging.debug("_attempt_db_update: UPDATE via _ejecutar_consulta OK")
                return True
            except Exception as e:
                logging.exception("_attempt_db_update: fallo UPDATE via _ejecutar_consulta: %s", e)
                return False

    except Exception as e:
        logging.exception("_attempt_db_update: excepción intentando actualizar BD: %s", e)
    return False


def guardar_conduce(db_manager,
                    transaccion: dict,
                    file_path: str,
                    config: Optional[dict] = None,
                    width: int = 1200,
                    height: int = 800,
                    update_db: bool = True) -> str:
    """
    Guarda el archivo 'conduce' y opcionalmente actualiza la fila de la transacción en la BD.

    - db_manager: instancia del gestor de BD (puede ser None si no se desea update automático).
    - transaccion: dict con al menos 'id' (si quieres update automático), opcional 'fecha' y 'conduce'.
    - file_path: ruta absoluta al archivo origen.
    - config: dict opcional con clave 'carpeta_conduces'.
    - width/height: dimensiones máximas para procesar imágenes.
    - update_db: si True e 'id' presente en transaccion y db_manager proporcionado, intentará hacer UPDATE.

    Retorna:
      ruta relativa (string) respecto a la carpeta base usada, con forward slashes.

    Excepciones:
      ValueError si faltan parámetros básicos
      FileNotFoundError si file_path no existe
      OSError u otras excepciones si la operación I/O falla
    """
    if not transaccion or not file_path:
        raise ValueError("Falta transacción o archivo origen")

    logging.debug("guardar_conduce: inicio. file_path=%s transaccion=%s config=%s update_db=%s",
                  file_path, transaccion, bool(config), update_db)

    # 1. Determinar año/mes
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

    # 2. Definir rutas candidatas
    base_dir_raw = (config.get('carpeta_conduces') or config.get('carpeta_conductos')) if isinstance(config, dict) else None
    
    # Lista de rutas candidatas, en orden de preferencia
    candidatas = [base_dir_raw] if base_dir_raw else []
    candidatas.append("./adjuntos") # Fallback local
    candidatas.append(str(Path(tempfile.gettempdir()) / "progain_adjuntos_tmp")) # Fallback final a temp

    base_dir_path = None
    
    # 3. Iterar y encontrar la primera ruta base que sea accesible o se pueda crear
    for raw_path in candidatas:
        if not raw_path:
            continue
            
        temp_base_path = _normalize_base_dir(raw_path)
        
        # Si no tiene unidad (o es relativo), asumimos que es local y seguimos con el intento de mkdir
        if not temp_base_path.drive or _ensure_drive_available(temp_base_path):
            ok_base, err_base = _safe_makedirs(temp_base_path)
            if ok_base:
                base_dir_path = temp_base_path
                logging.info("Carpeta base seleccionada: %s", base_dir_path)
                break
            else:
                logging.warning("Intento de crear base %s falló: %s", temp_base_path, err_base)
        else:
            logging.warning("Unidad no disponible para ruta: %s", temp_base_path)

    if not base_dir_path:
        raise OSError("No se pudo establecer una carpeta de destino válida para los adjuntos después de todos los fallbacks.")


    # 4. Construir destino y crear carpetas año/mes dentro de la base_dir_path
    destino_dir = base_dir_path / anio / mes
    ok, err = _safe_makedirs(destino_dir)
    if not ok:
        raise OSError(f"No se pudo crear la carpeta destino {destino_dir}: {err}")

    # 5. Copiar/Procesar el archivo
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
                logging.exception("Fallo procesar imagen con Pillow (%s). Intentando copia directa. Error: %s", origen_path, e)
                # Fallback: si falla Pillow o el proceso, hacer copia simple
                shutil.copy2(str(origen_path), str(destino))
        else:
            nombre_archivo = f"{conduce_num}{ext}"
            destino = destino_dir / nombre_archivo
            shutil.copy2(str(origen_path), str(destino))
    except Exception as e:
        logging.exception("Error al guardar el conduce: %s -> %s : %s", origen_path, destino_dir, e)
        # Re-lanzar para que la capa superior (DialogoAlquiler) capture, muestre el QMessageBox y registre.
        raise

    # 6. Calcular ruta relativa (forward slashes)
    try:
        relative_path = os.path.relpath(str(destino), str(base_dir_path)).replace("\\", "/")
    except Exception:
        relative_path = f"{anio}/{mes}/{destino.name}"

    logging.info("Conduce guardado: destino=%s relative=%s", destino, relative_path)

    # 7. Intentar actualizar la BD
    trans_id = transaccion.get('id')
    if update_db and db_manager and trans_id:
        try:
            updated = _attempt_db_update(db_manager, trans_id, relative_path)
            if updated:
                logging.info("Campo conduce_adjunto_path actualizado en DB para transaccion %s", trans_id)
            else:
                logging.debug("No se actualizó DB (método no disponible o fallo) para transaccion %s", trans_id)
        except Exception as e:
            logging.exception("Excepción intentando actualizar BD para transaccion %s: %s", trans_id, e)

    return relative_path