import sqlite3
import pandas as pd
from tkinter import filedialog, Tk
import sys

def elegir_base_de_datos():
    """Abre un diálogo para que el usuario seleccione un archivo de base de datos."""
    print("Por favor, selecciona tu archivo de base de datos...")
    root = Tk()
    root.withdraw()
    filepath = filedialog.askopenfilename(
        title="Selecciona tu BASE DE DATOS (.db)",
        filetypes=(("Archivos de base de datos", "*.db *.sqlite *.sqlite3"),)
    )
    if not filepath:
        print("\n❌ No se seleccionó archivo. Abortando.")
        sys.exit()
    print(f"Base de datos seleccionada: {filepath}\n")
    return filepath

def arreglar_adjuntos(db_path):
    """Añade la columna conduce_adjunto_path y migra los datos existentes."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # --- PASO 1: Añadir la columna si no existe ---
        print("Paso 1: Verificando la columna 'conduce_adjunto_path' en la tabla 'transacciones'...")
        try:
            cursor.execute("ALTER TABLE transacciones ADD COLUMN conduce_adjunto_path TEXT;")
            print("  - Columna 'conduce_adjunto_path' añadida exitosamente.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("  - La columna ya existe. No se necesita acción.")
            else:
                raise e
        
        # --- PASO 2: Migrar los datos existentes ---
        print("\nPaso 2: Buscando datos de adjuntos existentes para migrar...")
        df_a_migrar = pd.read_sql_query(
            "SELECT transaccion_id, conduce_adjunto_path FROM equipos_alquiler_meta WHERE conduce_adjunto_path IS NOT NULL", conn
        )

        if df_a_migrar.empty:
            print("  - No se encontraron datos de adjuntos para migrar. Todo listo.")
            conn.close()
            return
            
        print(f"  - Se encontraron {len(df_a_migrar)} rutas de adjuntos para copiar a la tabla 'transacciones'.")
        
        confirmacion = input("¿Deseas proceder con la migración de estos datos? (s/n): ").lower()

        if confirmacion == 's':
            print("\nMigrando datos...")
            actualizados = 0
            for index, row in df_a_migrar.iterrows():
                cursor.execute("""
                    UPDATE transacciones
                    SET conduce_adjunto_path = ?
                    WHERE id = ?
                """, (row['conduce_adjunto_path'], row['transaccion_id']))
                actualizados += 1
            
            conn.commit()
            print(f"✅ ¡Éxito! Se han migrado {actualizados} rutas de adjuntos.")
        else:
            print("❌ Operación de migración cancelada por el usuario.")

    except Exception as e:
        print(f"\n❌ Ocurrió un error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    db_file = elegir_base_de_datos()
    arreglar_adjuntos(db_file)