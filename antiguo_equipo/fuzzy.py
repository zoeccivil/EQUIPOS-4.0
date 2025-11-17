import sqlite3
from fuzzywuzzy import fuzz
from PyQt6.QtWidgets import QApplication, QFileDialog
import sys

# Configura el umbral de similitud (ajusta según necesidad)
FUZZY_THRESHOLD = 80

def buscar_mejor_equipo(descripcion, equipos):
    mejor_id = None
    mejor_score = 0
    for eq in equipos:
        score = fuzz.partial_ratio(eq['nombre'].lower(), descripcion.lower())
        if score > mejor_score:
            mejor_score = score
            mejor_id = eq['id']
    if mejor_score >= FUZZY_THRESHOLD:
        return mejor_id
    return None

def elegir_base_datos():
    app = QApplication(sys.argv)
    file_dialog = QFileDialog()
    file_dialog.setWindowTitle("Selecciona la base de datos SQLite")
    file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    file_dialog.setNameFilter("SQLite DB (*.sqlite3 *.db *.sqlite);;Todos los archivos (*)")
    if file_dialog.exec():
        files = file_dialog.selectedFiles()
        if files:
            return files[0]
    return None

def main():
    db_path = elegir_base_datos()
    if not db_path:
        print("No se seleccionó base de datos. Cancelado.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Obtener todos los equipos
    cur.execute("SELECT id, nombre FROM equipos")
    equipos = [dict(row) for row in cur.fetchall()]
    if not equipos:
        print("No hay equipos en la tabla 'equipos'.")
        return

    # Obtener todas las transacciones con equipo_id nulo, vacío o 0
    cur.execute("SELECT id, descripcion FROM transacciones WHERE equipo_id IS NULL OR equipo_id = '' OR equipo_id = 0")
    trans = [dict(row) for row in cur.fetchall()]

    actualizados = 0
    for t in trans:
        mejor_id = buscar_mejor_equipo(t["descripcion"], equipos)
        if mejor_id:
            cur.execute("UPDATE transacciones SET equipo_id = ? WHERE id = ?", (mejor_id, t["id"]))
            actualizados += 1

    conn.commit()
    print(f"Transacciones actualizadas: {actualizados}")
    conn.close()

if __name__ == "__main__":
    main()