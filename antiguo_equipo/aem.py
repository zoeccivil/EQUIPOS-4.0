import sqlite3
from PyQt6.QtWidgets import QApplication, QFileDialog
import sys
import re

PROYECTO_ID = 8
EQUIPO_ID = 1  # ID para el equipo "420D"
PATRON = r"420D"  # Busca el texto 420D en la descripción

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

    # Busca todas las transacciones sin equipo en proyecto 8, que tengan "420D" en la descripción
    cur.execute("""
        SELECT id, descripcion FROM transacciones
        WHERE proyecto_id = ?
          AND (equipo_id IS NULL OR equipo_id = '' OR equipo_id = 0)
    """, (PROYECTO_ID,))
    trans = [dict(row) for row in cur.fetchall()]

    actualizados = 0
    for t in trans:
        desc = t['descripcion'] or ""
        if re.search(PATRON, desc, re.IGNORECASE):
            cur.execute("UPDATE transacciones SET equipo_id = ? WHERE id = ?", (EQUIPO_ID, t['id']))
            actualizados += 1

    conn.commit()
    print(f"Transacciones actualizadas a equipo_id={EQUIPO_ID} (modelo 420D): {actualizados} de {len(trans)}")
    conn.close()

if __name__ == "__main__":
    main()