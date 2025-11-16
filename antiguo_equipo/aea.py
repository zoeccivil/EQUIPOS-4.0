import re
import sqlite3
from PyQt6.QtWidgets import QApplication, QFileDialog
import sys
from fuzzywuzzy import fuzz

PROYECTO_ID = 8
FUZZY_THRESHOLD = 85  # puedes bajar a 75 si quieres más "agresividad"

def partes_clave(nombre):
    # Extrae palabras y números del nombre del equipo para hacer matching
    return re.findall(r'[A-Z]+|\d+', nombre.upper())

def main():
    app = QApplication(sys.argv)
    file_dialog = QFileDialog()
    file_dialog.setWindowTitle("Selecciona la base de datos SQLite")
    file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    file_dialog.setNameFilter("SQLite DB (*.sqlite3 *.db *.sqlite);;Todos los archivos (*)")
    if file_dialog.exec():
        files = file_dialog.selectedFiles()
        if files:
            db_path = files[0]
        else:
            print("No se seleccionó base de datos. Cancelado.")
            return
    else:
        print("No se seleccionó base de datos. Cancelado.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Trae todos los equipos
    cur.execute("SELECT id, nombre FROM equipos")
    equipos = [dict(row) for row in cur.fetchall()]

    # Prepara keys de búsqueda para cada equipo
    equipo_busqueda = []
    for eq in equipos:
        claves = partes_clave(eq['nombre'])
        equipo_busqueda.append({'id': eq['id'], 'nombre': eq['nombre'], 'claves': claves})

    # Transacciones sin equipo en el proyecto 8
    cur.execute("""
        SELECT id, descripcion FROM transacciones
        WHERE proyecto_id = ? AND (equipo_id IS NULL OR equipo_id = '' OR equipo_id = 0)
    """, (PROYECTO_ID,))
    trans = [dict(row) for row in cur.fetchall()]

    actualizados = 0
    for t in trans:
        desc = (t['descripcion'] or "").upper()
        mejor_score = 0
        mejor_equipo = None

        # 1. Matching por clave/s (número/modelo o palabra)
        for eq in equipo_busqueda:
            # a) Si todas las claves (palabras/números) están en la descripción
            if all(c in desc for c in eq['claves']):
                mejor_equipo = eq['id']
                mejor_score = 100
                break
            # b) Matching fuzzy por nombre completo
            score = fuzz.partial_ratio(eq['nombre'].upper(), desc)
            if score > mejor_score:
                mejor_score = score
                mejor_equipo = eq['id']

        if mejor_score >= FUZZY_THRESHOLD:
            cur.execute("UPDATE transacciones SET equipo_id = ? WHERE id = ?", (mejor_equipo, t['id']))
            actualizados += 1

    conn.commit()
    print(f"Transacciones actualizadas automáticamente: {actualizados} de {len(trans)}")
    conn.close()

if __name__ == "__main__":
    main()