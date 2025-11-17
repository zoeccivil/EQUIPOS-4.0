import sqlite3
import pandas as pd
from tkinter import filedialog, Tk
import sys
from datetime import datetime

# --- LISTA DE IDs A BUSCAR ---
IDS_A_BUSCAR = [
    "fcfd0b97-9284-4e11-b2dd-b8a8fa82714e", "ff0daedd-7eda-413b-8ea0-c087296dd727",
    "d7013147-5190-4dae-8772-a68805a96c00", "7a6f4745-668b-4f5f-acb9-d862e267603a",
    "67d173de-dfa9-4227-925b-e0dea8fb1423", "d6dea19f-b47b-46fe-b8d5-0d6fc660517f",
    "4fa8064a-0c68-41e5-9a65-1d190cff8cdc", "7cc74cc0-d1fe-4d4b-af63-c1e4dd8c3b28",
    "c7488c6e-778a-401d-8d1b-9a40ff198e4b", "3f4189be-9834-4d09-8776-512a07b7f4df",
    "10a35c8b-7082-482e-b866-607b4d590a5b", "e8f66c2a-2f8e-4c75-aea4-c11735bd76e1",
    "41c27376-aae8-4f88-87d3-470db89563de", "6a99e74d-487f-4e62-9ba6-826eb57dd79f",
    "825b9a9f-96a5-4f22-b020-40e69e61a985", "0f9b2ea5-9a86-44e6-9548-371b4de8a171",
    "6019db20-6005-45ee-b267-9f3f0b3edf7f", "6b9eaed6-6b29-43f8-b3d5-1e79b7a5d4c6",
    "7d23c639-ac50-4f70-8f35-03dadd85abdb", "02a08523-2bfb-47fd-b9ad-a87300714f2d",
    "043d2b34-0fe2-47db-bfd6-c87644a8659a", "5c9a36fd-2afd-4f55-bc9f-41efbc22427b",
    "f6d0d560-8686-4930-94ac-1471f7c4d566", "a9583d8b-421b-458f-9b59-559faaff4f5b",
    "29b8019b-5bc2-49e8-9701-f273788db67b", "4b5c1d02-bdba-49d9-a0d5-dc7ebbcf0b57",
    "d76ad11e-4ac7-4384-8e2f-d7af0e2682f6", "421ab585-4043-4ce6-a0d4-b3293ba191fe",
    "43a1af43-62cb-4a90-8152-2275b750e7b2", "7cfa7c7e-e4a7-4f7c-9194-57e1c908e9bb",
    "d9438ab8-4701-47c1-a5e6-bc28f72e1ca5", "5d6764ed-69b0-43b8-860a-361d8ad1a91d",
    "e8a3f644-1194-43f6-aa89-33ac8c763417", "f5b50724-34a6-43db-9c1c-7721da1014d4",
    "26d4861f-3056-4ddd-ba01-a508ed412092", "634fb3e8-f24c-400a-b517-d304c2b0cbef",
    "4e73cef7-16a4-4cc7-9bf1-a99eb8746dcc", "a3a530fb-c67b-41c1-9b62-a4c8b42184f7",
    "f78ea703-df4c-46c1-ada6-0fad4b3182b0", "23f33b67-9af9-4c2c-9d91-8fc510ba0564",
    "5f5d29f2-2357-4b24-8130-ebaed385e2b3", "0eaa9dba-abb4-4a4f-b6d7-a2df32e45832",
    "7f90870a-8b96-47f5-af1c-ddb710a822ba", "c5fad309-e7f0-4716-9cb9-e71c5c947fa4",
    "1b8ef0f3-9c24-45b8-83de-0416ed8c8efc", "6f1f7de0-1430-4bfd-a384-3fc3a82c18f7",
    "8ab684bd-a6be-4c08-bf0d-20fe77126924", "c3fa4056-3f2e-4bf2-8e54-e0c40b1f1315",
    "b316f9e5-abf7-46dc-bc67-6d65206ca8e3", "5f770b54-343a-4c18-900b-4ea891f1503a",
    "93eb604c-0f09-4b19-b666-5e1062110137", "fd3ff028-34d7-461b-875c-d8a1ee0c9f83",
    "f4659324-b748-4da1-b441-2e5514ecb9a8", "9f3e54bb-8758-4090-92b7-a2e3ce1be62d",
    "278fcd58-ba92-4049-a203-a2e80480d61e", "49595f94-fb45-40fb-909e-2941d29dd39d",
    "f4dd62e7-5994-45c5-8011-d285c218523f", "c230d449-b14b-43a8-b0e8-f12d5c277c5c"
]

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

def buscar_operadores_metodo_viejo(db_path, ids_a_buscar):
    """
    Busca transacciones usando la lógica del 'método antiguo' (por categoría)
    y muestra el operador_id y nombre del operador.
    """
    if not ids_a_buscar:
        print("La lista de IDs para buscar está vacía.")
        return

    try:
        conn = sqlite3.connect(db_path)

        placeholders = ', '.join('?' for _ in ids_a_buscar)
        
        # Consulta que usa la lógica del "método antiguo"
        query = f"""
            SELECT
                T.id,
                T.fecha,
                T.descripcion,
                T.monto,
                T.operador_id,
                OPE.nombre as operador_nombre,
                CAT.nombre as categoria_nombre
            FROM transacciones T
            LEFT JOIN equipos_entidades OPE ON T.operador_id = OPE.id
            INNER JOIN categorias CAT ON T.categoria_id = CAT.id
            WHERE
                CAT.nombre = 'PAGO HRS OPERADOR'
                AND T.id IN ({placeholders})
            ORDER BY T.fecha
        """
        
        print("Buscando transacciones con la lógica del 'Método Antiguo'...")
        df_resultados = pd.read_sql_query(query, conn, params=ids_a_buscar)
        
        if df_resultados.empty:
            print("\nNo se encontró ninguna transacción que coincida con los IDs y la categoría 'PAGO HRS OPERADOR'.")
            return

        print(f"\n✅ Se encontraron {len(df_resultados)} transacciones que coinciden:")
        print("--- RESULTADOS (MÉTODO ANTIGUO) ---")
        print(df_resultados.to_string())

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"Resultado_Busqueda_Metodo_Antiguo_{timestamp}.xlsx"
        df_resultados.to_excel(nombre_archivo, index=False)
        print(f"\nResultados también guardados en el archivo: {nombre_archivo}")

    except Exception as e:
        print(f"\n❌ Ocurrió un error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    db_file = elegir_base_de_datos()
    buscar_operadores_metodo_viejo(db_file, IDS_A_BUSCAR)