import sqlite3
import sys

# Si tienes PyQt6 instalado, usa un diálogo visual. Si no, usa input().
try:
    from PyQt6.QtWidgets import QApplication, QFileDialog
    def elegir_db():
        app = QApplication(sys.argv)
        file, _ = QFileDialog.getOpenFileName(None, "Seleccionar base de datos SQLite", "", "SQLite DB (*.db *.sqlite);;Todos (*)")
        return file
except ImportError:
    def elegir_db():
        return input("Ruta de la base de datos SQLite: ").strip()

PALABRAS_EQUIPOS = ["VOLVO 330", "EXCAVADORA 325"]
PALABRAS_OPERADORES = ["JHONATTAN ROJAS RIVAR"]

def buscar_palabras_en_db(db_path, palabras, max_resultados=5):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    tablas = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    hallazgos = []
    print(f"\nAnalizando base de datos: {db_path}\n")
    for t in tablas:
        tabla = t['name']
        columnas = [c[1] for c in conn.execute(f"PRAGMA table_info('{tabla}')")]
        for columna in columnas:
            for palabra in palabras:
                try:
                    q = f"SELECT rowid, * FROM '{tabla}' WHERE UPPER({columna}) LIKE UPPER(?)"
                    cursor = conn.execute(q, (f"%{palabra}%",))
                    for row in cursor:
                        hallazgos.append((tabla, columna, palabra, dict(row)))
                        if len(hallazgos) >= max_resultados:
                            return hallazgos
                except Exception:
                    continue
    return hallazgos

if __name__ == "__main__":
    db_path = elegir_db()
    if not db_path:
        print("No se seleccionó base de datos.")
        sys.exit(1)

    print("\n=== BUSQUEDA DE EQUIPOS ===")
    hallazgos_eq = buscar_palabras_en_db(db_path, PALABRAS_EQUIPOS, max_resultados=5)
    if hallazgos_eq:
        for tabla, columna, palabra, row in hallazgos_eq:
            print(f"Encontrado '{palabra}' en tabla '{tabla}', columna '{columna}':\n  {row}\n")
    else:
        print("No se encontraron coincidencias para EQUIPOS.")

    print("\n=== BUSQUEDA DE OPERADORES ===")
    hallazgos_op = buscar_palabras_en_db(db_path, PALABRAS_OPERADORES, max_resultados=5)
    if hallazgos_op:
        for tabla, columna, palabra, row in hallazgos_op:
            print(f"Encontrado '{palabra}' en tabla '{tabla}', columna '{columna}':\n  {row}\n")
    else:
        print("No se encontraron coincidencias para OPERADORES.")

    print("\n--- FIN DEL REPORTE ---")
