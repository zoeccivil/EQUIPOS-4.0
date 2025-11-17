import sqlite3
from tkinter import Tk, filedialog, messagebox

# IDs y nombres correctos según tu tabla (¡agrega más si tienes más equipos!)
equipos = {
    1: 72.5,    # RETROPALA 420D
    2: 5,    # RETROPALA 420IT
    3: 408,    # RETROPALA 416E
    4: 491.5,    # EXCAVADORA 325BL
    5: 295.8,    # EXCAVADORA VOLVO 330 EL
    6: 0,    # MINICARGADOR BOBCAT
    7: 0,    # RODILLO WACKER 3 TON
    8: 0,    # CAMION GRUA ISUZU
    9: 0,    # TIJERILLA JLG
    10: 0,   # CAMION KIA 2700
    11: 0,   # CAMION JAC
    12: 0,   # CAMION VOLTEO HINO
}

# Si ya tienes los valores de horas acumuladas para cada equipo, reemplaza el 0 por el valor que corresponda.

# 1. Mostrar diálogo para elegir la base de datos
root = Tk()
root.withdraw()
messagebox.showinfo("Seleccionar Base de Datos", "Selecciona el archivo de tu base de datos (SQLite).")
db_path = filedialog.askopenfilename(
    title="Selecciona la base de datos",
    filetypes=[("SQLite DB", "*.db *.sqlite3 *.sqlite"), ("Todos los archivos", "*.*")]
)

if not db_path:
    messagebox.showerror("Error", "No seleccionaste ninguna base de datos.")
    exit()

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 2. Borra todos los mantenimientos actuales
    cur.execute("DELETE FROM mantenimientos;")
    conn.commit()

    # 3. Inserta un mantenimiento inicial para cada equipo
    for equipo_id, horas in equipos.items():
        cur.execute("""
            INSERT INTO mantenimientos (
                equipo_id, fecha, descripcion, tipo, valor, odometro_horas, notas, created_at, proximo_tipo, proximo_valor, proximo_fecha, odometro_km
            ) VALUES (
                ?, DATE('now'), ?, NULL, 0, ?, NULL, DATETIME('now'), 'HORAS', 300, NULL, NULL
            )
        """, (
            equipo_id,
            "Migración de horas históricas" if horas else "Inicio registro automático",
            horas if horas is not None else 0
        ))

    conn.commit()
    conn.close()
    messagebox.showinfo("Éxito", "¡Mantenimientos iniciales insertados correctamente!\n\nAhora puedes editar el campo 'odometro_horas' si lo deseas.")

except Exception as e:
    messagebox.showerror("Error", f"Ocurrió un error:\n{e}")