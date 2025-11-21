import sqlite3
import pandas as pd
from tkinter import filedialog, Tk
import sys

def elegir_base_de_datos():
    # ... (puedes copiar la misma función del script anterior) ...
    print("Por favor, selecciona tu archivo de base de datos...")
    root = Tk()
    root.withdraw()
    filepath = filedialog.askopenfilename(
        title="Selecciona tu BASE DE DATOS (.db)",
        filetypes=(("Archivos de base de datos", "*.db *.sqlite *.sqlite3"),)
    )
    if not filepath:
        print("No se seleccionó archivo. Abortando.")
        sys.exit()
    return filepath

def migrar_datos_meta(db_path):
    """Copia los datos de equipos_alquiler_meta a transacciones."""
    try:
        conn = sqlite3.connect(db_path)
        
        # Leer los datos que necesitan ser migrados
        query = "SELECT transaccion_id, conduce, ubicacion, horas FROM equipos_alquiler_meta"
        df_meta = pd.read_sql_query(query, conn)
        df_a_migrar = df_meta.dropna(subset=['conduce', 'ubicacion', 'horas'], how='all')

        if df_a_migrar.empty:
            print("✅ No se encontraron datos para migrar en 'equipos_alquiler_meta'.")
            return

        print("--- CAMBIOS PROPUESTOS ---")
        print(f"Se migrarán los datos para {len(df_a_migrar)} registros:")
        print(df_a_migrar.rename(columns={'transaccion_id': 'ID_Transaccion'}).to_string(index=False))

        confirmacion = input("\n¿Deseas aplicar esta migración de datos? (s/n): ").lower()

        if confirmacion == 's':
            print("\nMigrando datos...")
            cursor = conn.cursor()
            for index, row in df_a_migrar.iterrows():
                cursor.execute("""
                    UPDATE transacciones
                    SET conduce = ?, ubicacion = ?, horas = ?
                    WHERE id = ?
                """, (row['conduce'], row['ubicacion'], row['horas'], row['transaccion_id']))
            
            conn.commit()
            print(f"✅ ¡Éxito! Se han migrado los datos de {len(df_a_migrar)} registros.")
        else:
            print("❌ Operación cancelada. No se realizó ningún cambio.")
            
    except Exception as e:
        print(f"\n❌ Ocurrió un error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    db_file = elegir_base_de_datos()
    migrar_datos_meta(db_file)