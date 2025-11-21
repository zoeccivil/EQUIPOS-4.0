import argparse
import csv
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, UTC
from difflib import SequenceMatcher
import unicodedata

import firebase_admin
from firebase_admin import credentials, firestore
from google.api_core import exceptions as google_exceptions

# === CONFIGURACIÓN ===
SERVICE_ACCOUNT_KEY = "firebase_credentials.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("migracion.gastos.equipo")

BASE_DIR = Path(__file__).resolve().parents[1]
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def init_firestore(cred_path: str | None = None):
    cred_file = str(Path(cred_path or SERVICE_ACCOUNT_KEY).expanduser().resolve())
    if not Path(cred_file).exists():
        raise FileNotFoundError(f"No existe el archivo de credenciales: {cred_file}")
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_file)
        firebase_admin.initialize_app(cred)
    return firestore.client()


SINONIMOS = {
    " retro ": " retropala ",
    "retrop ": " retropala ",
    " retroexcavadora ": " retropala ",
    " exc ": " excavadora ",
    " excav ": " excavadora ",
    " pala ": " retropala ",
    " cat ": " caterpillar ",
}

def normalizar_texto(s: str) -> str:
    if not s:
        return ""
    import unicodedata
    s2 = s.lower()
    s2 = "".join(c for c in unicodedata.normalize("NFD", s2) if unicodedata.category(c) != "Mn")
    s2 = f" {s2} "
    for a, b in SINONIMOS.items():
        s2 = s2.replace(a, b)
    s2 = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in s2)
    s2 = " ".join(s2.split())
    return s2.strip()

def ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()


def _normalizar_campo_entero_a_string(data: dict, campo: str) -> tuple[bool, str]:
    if campo not in data:
        return False, ""
    valor = data[campo]
    if isinstance(valor, str):
        return False, valor
    try:
        valor_int = int(valor)
        return True, str(valor_int)
    except (ValueError, TypeError):
        logger.warning(f"{campo}={valor!r} no es numérico, se deja sin cambios.")
        return False, ""


def cargar_mapa_equipos(db) -> dict:
    mapa = {}
    docs = list(db.collection("equipos").stream())
    for d in docs:
        data = d.to_dict() or {}
        nombre = data.get("nombre") or data.get("equipo") or str(d.id)
        mapa[str(d.id)] = nombre
        if "id" in data:
            try:
                mapa[str(int(data["id"]))] = nombre
            except Exception:
                pass
    logger.info(f"Equipos cargados: {len(mapa)}")
    return mapa

def cargar_mapa_subcategorias(db) -> dict:
    mapa = {}
    docs = list(db.collection("subcategorias").stream())
    for d in docs:
        data = d.to_dict() or {}
        nombre = data.get("nombre") or str(d.id)
        mapa[str(d.id)] = nombre
        if "id" in data:
            try:
                mapa[str(int(data["id"]))] = nombre
            except Exception:
                pass
    logger.info(f"Subcategorías cargadas: {len(mapa)}")
    return mapa

def construir_cadena_candidata_desde_subcategoria(gasto: dict, subcategorias_mapa: dict) -> str:
    sub_id = gasto.get("subcategoria_id")
    if sub_id is None:
        return ""
    return subcategorias_mapa.get(str(sub_id), "") or ""

def adivinar_equipo_por_subcategoria(gasto: dict, equipos_mapa: dict, subcategorias_mapa: dict, threshold: float) -> tuple[str | None, float, str]:
    sub_txt = construir_cadena_candidata_desde_subcategoria(gasto, subcategorias_mapa)
    cand = normalizar_texto(sub_txt)
    if not cand:
        return None, 0.0, ""
    nombres_norm = {eid: normalizar_texto(nom) for eid, nom in equipos_mapa.items()}
    mejor = (None, 0.0, "")
    for eid, nom_norm in nombres_norm.items():
        sc = max(ratio(cand, nom_norm), ratio(nom_norm, cand))
        if nom_norm and nom_norm in cand:
            sc = max(sc, 0.95)
        if sc > mejor[1]:
            mejor = (eid, sc, equipos_mapa.get(eid, ""))
    if mejor[0] and mejor[1] >= threshold:
        return mejor
    return None, mejor[1], mejor[2]


def normalizar_ids_en_gastos(db) -> int:
    logger.info("Normalizando equipo_id numérico -> string en [gastos]...")
    col_ref = db.collection("gastos")
    docs = list(col_ref.stream())
    logger.info(f"Total documentos en gastos: {len(docs)}")
    batch = db.batch()
    batch_count = 0
    total_actualizados = 0
    for doc in docs:
        data = doc.to_dict() or {}
        cambios = {}
        cambiar_equipo, equipo_id_str = _normalizar_campo_entero_a_string(data, "equipo_id")
        if cambiar_equipo and equipo_id_str:
            cambios["equipo_id"] = equipo_id_str
        if not cambios:
            continue
        batch.update(doc.reference, cambios)
        batch_count += 1
        total_actualizados += 1
        if batch_count >= 400:
            logger.info(f"Enviando batch de {batch_count} updates en [gastos]...")
            batch.commit()
            batch = db.batch()
            batch_count = 0
    if batch_count > 0:
        logger.info(f"Enviando batch final de {batch_count} updates en [gastos]...")
        batch.commit()
    logger.info(f"Normalización completada. Documentos actualizados: {total_actualizados}")
    return total_actualizados

def iterar_gastos_sin_equipo(db, fecha_inicio: str | None, fecha_fin: str | None):
    col = db.collection("gastos")
    docs = list(col.stream())
    for snap in docs:
        data = snap.to_dict() or {}
        data["id"] = snap.id
        f = data.get("fecha") or ""
        if fecha_inicio and f < fecha_inicio:
            continue
        if fecha_fin and f > fecha_fin:
            continue
        eid = data.get("equipo_id")
        invalido = (
            eid in (None, "", 0) or
            (isinstance(eid, str) and eid.strip().lower() in ("0", "none", "null"))
        )
        if invalido:
            yield data

def batch_update(db, updates: list[tuple[str, dict]]) -> int:
    total = 0
    batch = db.batch()
    count = 0
    for doc_id, payload in updates:
        ref = db.collection("gastos").document(doc_id)
        batch.update(ref, payload)
        count += 1
        if count >= 400:
            batch.commit()
            total += count
            logger.info(f"Batch aplicado: {count} docs")
            batch = db.batch()
            count = 0
    if count > 0:
        batch.commit()
        total += count
        logger.info(f"Batch final aplicado: {count} docs")
    return total

def exportar_csv(path_csv: Path, filas: list[dict]):
    path_csv.parent.mkdir(parents=True, exist_ok=True)
    if not filas:
        return
    campos = sorted({k for fila in filas for k in fila.keys()})
    with path_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for r in filas:
            w.writerow(r)

# ... imports y utilidades igual ...

def main():
    parser = argparse.ArgumentParser(description="Migración: inferir equipo_id en 'gastos' usando SOLO subcategoría.")
    parser.add_argument("--credentials", help="Ruta al service account JSON", default=None)
    parser.add_argument("--desde", help="Fecha inicio (YYYY-MM-DD)", default=None)
    parser.add_argument("--hasta", help="Fecha fin (YYYY-MM-DD)", default=None)
    # 1) threshold de detección (para ver en el CSV del plan)
    parser.add_argument("--threshold", type=float, default=0.85, help="Umbral para detectar candidatos (aparecen en el plan).")
    # 2) threshold de commit (qué tan alto debe ser el score para ESCRIBIR en Firestore)
    parser.add_argument("--commit-threshold", type=float, default=0.95, help="Umbral mínimo para aplicar cambios (commit).")
    parser.add_argument("--limit", type=int, default=None, help="Máximo de gastos a procesar")
    parser.add_argument("--commit", action="store_true", help="Aplica cambios. Sin esto, solo genera plan (dry-run).")
    parser.add_argument("--normalizar-ids", action="store_true", help="Primero normaliza equipo_id numérico -> string en 'gastos'.")
    args = parser.parse_args()

    db = init_firestore(args.credentials)

    try:
        if args.normalizar_ids:
            normalizar_ids_en_gastos(db)

        equipos_mapa = cargar_mapa_equipos(db)
        subcategorias_mapa = cargar_mapa_subcategorias(db)

        proc = 0
        candidatos = 0
        para_commit = 0
        updates = []
        plan_rows = []

        now_tag = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        plan_csv = LOGS_DIR / f"plan_migracion_gastos_equipo_{now_tag}.csv"
        res_csv = LOGS_DIR / f"resultado_migracion_gastos_equipo_{now_tag}.csv"

        for gasto in iterar_gastos_sin_equipo(db, args.desde, args.hasta):
            proc += 1
            if args.limit and proc > args.limit:
                break

            eid, score, nom_eq = adivinar_equipo_por_subcategoria(
                gasto, equipos_mapa, subcategorias_mapa, threshold=args.threshold
            )

            # Siempre registramos en el plan el mejor match (aunque esté bajo)
            plan_rows.append({
                "gasto_id": gasto.get("id"),
                "fecha": gasto.get("fecha"),
                "subcategoria_id": gasto.get("subcategoria_id"),
                "subcategoria_txt": subcategorias_mapa.get(str(gasto.get("subcategoria_id")), ""),
                "descripcion": gasto.get("descripcion", ""),
                "comentario": gasto.get("comentario", ""),
                "equipo_detectado": eid or "",
                "equipo_nombre": nom_eq or "",
                "score": f"{score:.4f}",
            })

            # Solo “candidato” si superó el umbral de detección
            if eid:
                candidatos += 1
                # Solo se agrega a updates si cumple el umbral de commit
                if score >= args.commit_threshold:
                    para_commit += 1
                    updates.append((
                        gasto["id"],
                        {
                            "equipo_id": eid,
                            "migracion_equipo": {
                                "cuando": datetime.now(UTC).isoformat(),
                                "metodo": "subcategoria",
                                "score": score,
                                "equipo_nombre": nom_eq,
                            }
                        }
                    ))

        exportar_csv(plan_csv, plan_rows)
        logger.info(f"Plan de migración generado: {plan_csv}")
        logger.info(f"Procesados: {proc} | Candidatos (>= {args.threshold}): {candidatos} | Para commit (>= {args.commit_threshold}): {para_commit}")

        if args.commit and updates:
            n = batch_update(db, updates)
            logger.info(f"Actualizados en Firestore: {n}")
            res_rows = [{
                "gasto_id": gid,
                "equipo_id": payload["equipo_id"],
                "equipo_nombre": payload["migracion_equipo"]["equipo_nombre"],
                "score": payload["migracion_equipo"]["score"],
            } for gid, payload in updates]
            exportar_csv(res_csv, res_rows)
            logger.info(f"Resultado de migración: {res_csv}")
        elif args.commit and not updates:
            logger.info("No hay cambios para aplicar (ningún candidato alcanzó el commit-threshold).")
        else:
            logger.info("Dry-run: no se escribieron cambios. Use --commit para aplicar.")

    except google_exceptions.ResourceExhausted as e:
        logger.error(f"Cuota de Firestore excedida: {e}")
    except Exception as e:
        logger.error(f"Error general en la migración: {e}", exc_info=True)
        
if __name__ == "__main__":
    main()