import argparse
import logging
from pathlib import Path
from datetime import datetime, UTC
import csv

import firebase_admin
from firebase_admin import credentials, firestore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("migracion.pagos")

SERVICE_ACCOUNT_KEY = "firebase_credentials.json"

def init_db(cred_path=None):
    cred_file = str(Path(cred_path or SERVICE_ACCOUNT_KEY).expanduser().resolve())
    if not Path(cred_file).exists():
        raise FileNotFoundError(f"No existe credencial: {cred_file}")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(cred_file))
    return firestore.client()

def ensure_categoria(db, nombre: str):
    col = db.collection("categorias")
    for d in col.stream():
        data = d.to_dict() or {}
        if (data.get("nombre", "") or "").strip().lower() == nombre.strip().lower():
            return d.id
    ref = col.document()
    ref.set({"nombre": nombre})
    return ref.id

def ensure_subcategoria(db, nombre: str, categoria_id: str):
    col = db.collection("subcategorias")
    for d in col.stream():
        data = d.to_dict() or {}
        if (data.get("nombre", "") or "").strip().lower() == nombre.strip().lower() and str(data.get("categoria_id") or "") == str(categoria_id):
            return d.id
    ref = col.document()
    ref.set({"nombre": nombre, "categoria_id": str(categoria_id)})
    return ref.id

def cargar_mapa_equipos(db):
    m = {}
    for d in db.collection("equipos").stream():
        data = d.to_dict() or {}
        nom = data.get("nombre") or data.get("equipo") or d.id
        m[str(d.id)] = nom
        if "id" in data:
            try:
                m[str(int(data["id"]))] = nom
            except Exception:
                pass
    return m

def obtener_cliente_ubicacion_ultimo_alquiler(db, equipo_id: str):
    snaps = list(db.collection("alquileres").where("equipo_id", "==", str(equipo_id)).stream())
    if not snaps:
        return "", ""
    clientes_map = {}
    # Construir mapa clientes {id:nombre} si existe colección 'clientes'
    for c in db.collection("clientes").stream():
        cd = c.to_dict() or {}
        clientes_map[str(c.id)] = cd.get("nombre") or str(c.id)
    ult = sorted((s.to_dict() for s in snaps), key=lambda x: x.get("fecha", ""))[-1]
    cid = str(ult.get("cliente_id") or "")
    return clientes_map.get(cid, cid) if cid else "", ult.get("ubicacion", "") or ""

def batch_commit(db, updates):
    batch = db.batch()
    count = 0
    total = 0
    for ref, payload in updates:
        batch.update(ref, payload)
        count += 1
        if count >= 400:
            batch.commit()
            total += count
            logging.info(f"Batch aplicado: {count}")
            batch = db.batch()
            count = 0
    if count:
        batch.commit()
        total += count
        logging.info(f"Batch final aplicado: {count}")
    return total

def main():
    ap = argparse.ArgumentParser(description="Enriquecer pagos_operadores con categoria/subcategoria/equipo/descripcion/comentario.")
    ap.add_argument("--credentials", default=None, help="Ruta al service account JSON")
    ap.add_argument("--cuenta-id-default", default=None, help="Cuenta por defecto si falta cuenta_id")
    ap.add_argument("--commit", action="store_true", help="Aplicar cambios (por defecto dry-run)")
    args = ap.parse_args()

    db = init_db(args.credentials)
    equipos_map = cargar_mapa_equipos(db)
    cat_id = ensure_categoria(db, "PAGO HRS OPERADOR")

    plan_rows = []
    updates = []

    for snap in db.collection("pagos_operadores").stream():
        d = snap.to_dict() or {}
        gid = snap.id

        # Resolver subcategoría (nombre equipo si hay)
        equipo_id = d.get("equipo_id")
        equipo_nom = equipos_map.get(str(equipo_id), "") if equipo_id else ""

        sub_id = d.get("subcategoria_id")
        if not sub_id and equipo_nom and cat_id:
            sub_id = ensure_subcategoria(db, equipo_nom, cat_id)

        # Descripción/Comentario
        desc = d.get("descripcion")
        comm = d.get("comentario")
        horas = d.get("horas")
        operador_nom = str(d.get("operador_nombre") or "")  # por si existiera
        if not operador_nom and d.get("operador_id"):
            # se puede enriquecer leyendo 'operadores' si tienes colección
            pass
        if not desc:
            desc = f"Pago {horas or ''} Horas Operador {operador_nom}".strip()
        if not comm:
            cliente, ubicacion = ("", "")
            if equipo_id:
                cliente, ubicacion = obtener_cliente_ubicacion_ultimo_alquiler(db, str(equipo_id))
            comm = f"Pago {horas or ''} Horas, Operador {operador_nom}, Cliente {cliente}, Ubicacion {ubicacion}".strip()

        # Cuenta por defecto si no hay
        cuenta_id = d.get("cuenta_id") or args.cuenta_id_default

        payload = {}
        if not d.get("categoria_id") and cat_id:
            payload["categoria_id"] = cat_id
        if sub_id and d.get("subcategoria_id") != sub_id:
            payload["subcategoria_id"] = sub_id
        if desc and d.get("descripcion") != desc:
            payload["descripcion"] = desc
        if comm and d.get("comentario") != comm:
            payload["comentario"] = comm
        if cuenta_id and not d.get("cuenta_id"):
            payload["cuenta_id"] = str(cuenta_id)

        if payload:
            payload["migracion_pagos"] = {
                "cuando": datetime.now(UTC).isoformat(),
                "metodo": "enriquecer_subcat_desc_com",
            }
            updates.append((snap.reference, payload))

        plan_rows.append({
            "pago_id": gid,
            "equipo_id": str(equipo_id or ""),
            "equipo_nombre": equipo_nom,
            "categoria_id": payload.get("categoria_id", d.get("categoria_id", "")),
            "subcategoria_id": payload.get("subcategoria_id", d.get("subcategoria_id", "")),
            "descripcion": payload.get("descripcion", d.get("descripcion", "")),
            "comentario": payload.get("comentario", d.get("comentario", "")),
            "cuenta_id": payload.get("cuenta_id", d.get("cuenta_id", "")),
        })

    # CSV plan
    logs_dir = Path(__file__).resolve().parents[1] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    plan_csv = logs_dir / f"plan_migracion_pagos_operadores_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"
    with plan_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(plan_rows[0].keys()) if plan_rows else ["pago_id"])
        w.writeheader()
        for r in plan_rows:
            w.writerow(r)
    logger.info(f"Plan generado: {plan_csv}")

    if args.commit and updates:
        n = batch_commit(db, updates)
        logger.info(f"Pagos enriquecidos: {n}")
    elif args.commit and not updates:
        logger.info("No hay cambios para aplicar.")
    else:
        logger.info("Dry-run: no se escribieron cambios. Use --commit para aplicar.")

if __name__ == "__main__":
    main()