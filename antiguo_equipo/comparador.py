import sqlite3
import pandas as pd
from tkinter import filedialog, Tk
import sys
from datetime import datetime

def elegir_base_de_datos():
    """
    Abre un diálogo para que el usuario seleccione un archivo de base de datos.
    """
    print("Por favor, selecciona el archivo de la base de datos...")
    root = Tk()
    root.withdraw()  # Oculta la ventana raíz
    
    filepath = filedialog.askopenfilename(
        title="Selecciona tu archivo de base de datos",
        filetypes=(
            ("Archivos de base de datos", "*.db *.sqlite *.sqlite3"),
            ("Todos los archivos", "*.*")
        )
    )
    
    if not filepath:
        print("\n❌ No se seleccionó ningún archivo. Abortando el programa.")
        sys.exit()
        
    print(f"Base de datos seleccionada: {filepath}\n")
    return filepath

# --- DEFINICIÓN DE LAS CONSULTAS (SIN FILTRO DE PROYECTO) ---

QUERY_METODO_1 = """
    SELECT 
        T.id, T.proyecto_id, T.fecha, T.monto, T.pagado,
        COALESCE(META.conduce, T.conduce) AS conduce,
        COALESCE(META.ubicacion, T.ubicacion) AS ubicacion,
        COALESCE(META.horas, T.horas) AS horas,
        COALESCE(META.precio_por_hora, T.precio_por_hora) AS precio_por_hora,
        CLI.nombre AS cliente_nombre,
        OPE.nombre AS operador_nombre,
        NULL AS equipo_nombre
    FROM transacciones T
    LEFT JOIN equipos_alquiler_meta META ON T.id = META.transaccion_id
    INNER JOIN categorias CAT ON T.categoria_id = CAT.id
    LEFT JOIN equipos_entidades CLI ON META.cliente_id = CLI.id
    LEFT JOIN equipos_entidades OPE ON META.operador_id = OPE.id
    WHERE CAT.nombre = 'ALQUILERES'
"""

QUERY_METODO_2 = """
    SELECT 
        T.id, T.proyecto_id, T.fecha, T.monto, T.pagado,
        COALESCE(META.conduce, T.conduce, '') AS conduce,
        COALESCE(META.ubicacion, T.ubicacion, '') AS ubicacion,
        COALESCE(META.horas, T.horas, 0) AS horas,
        COALESCE(META.precio_por_hora, T.precio_por_hora, 0) AS precio_por_hora,
        CLI.nombre AS cliente_nombre,
        OPE.nombre AS operador_nombre,
        EQ.nombre AS equipo_nombre
    FROM transacciones T
    LEFT JOIN equipos_alquiler_meta META ON T.id = META.transaccion_id
    LEFT JOIN equipos EQ ON T.equipo_id = EQ.id
    LEFT JOIN equipos_entidades CLI ON T.cliente_id = CLI.id
    LEFT JOIN equipos_entidades OPE ON T.operador_id = OPE.id
    WHERE T.tipo = 'Ingreso'
"""

def comparar_y_exportar(db_path):
    """
    Ejecuta ambas consultas, compara los resultados y exporta un reporte a Excel.
    """
    print("--- Iniciando análisis completo de la base de datos ---")
    
    try:
        conn = sqlite3.connect(db_path)

        # Cargar todos los datos de ambos métodos
        df1 = pd.read_sql_query(QUERY_METODO_1 + " ORDER BY T.id ASC", conn)
        df2 = pd.read_sql_query(QUERY_METODO_2 + " ORDER BY T.id ASC", conn)
        
        conn.close()
        print("Datos cargados correctamente. Procediendo a comparar...")

        # --- ANÁLISIS DE DIFERENCIAS ---
        ids1 = set(df1['id'])
        ids2 = set(df2['id'])
        
        ids_comunes = ids1.intersection(ids2)
        ids_solo_en_1 = ids1 - ids2
        ids_solo_en_2 = ids2 - ids1

        # Obtener filas completas de registros únicos
        df_solo_en_1 = df1[df1['id'].isin(ids_solo_en_1)]
        df_solo_en_2 = df2[df2['id'].isin(ids_solo_en_2)]

        # Comparar valores en filas con IDs comunes
        df1_comun = df1[df1['id'].isin(ids_comunes)].set_index('id').sort_index()
        df2_comun = df2[df2['id'].isin(ids_comunes)].set_index('id').sort_index()
        
        diferencias_datos = []
        columnas_comunes = [
            'fecha', 'monto', 'pagado', 'conduce', 'ubicacion', 
            'horas', 'precio_por_hora', 'cliente_nombre', 'operador_nombre', 'equipo_nombre'
        ]

        for id_transaccion in df1_comun.index:
            for col in columnas_comunes:
                val1 = df1_comun.loc[id_transaccion, col]
                val2 = df2_comun.loc[id_transaccion, col]
                v1_norm = '' if pd.isna(val1) else str(val1).strip()
                v2_norm = '' if pd.isna(val2) else str(val2).strip()

                if v1_norm != v2_norm:
                    diferencias_datos.append({
                        'ID_Transaccion': id_transaccion,
                        'Columna_Afectada': col,
                        'Valor_Metodo_1': v1_norm,
                        'Valor_Metodo_2': v2_norm
                    })
        
        df_diferencias = pd.DataFrame(diferencias_datos)
        
        # --- CREAR REPORTE EN EXCEL ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"Reporte_Comparacion_{timestamp}.xlsx"
        
        with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
            # Hoja de Resumen
            resumen_data = {
                'Métrica': [
                    'Total de filas en Método 1', 
                    'Total de filas en Método 2',
                    'Registros con ID en común',
                    'Registros solo en Método 1',
                    'Registros solo en Método 2',
                    'Filas con diferencias de datos'
                ],
                'Cantidad': [
                    len(df1), 
                    len(df2),
                    len(ids_comunes),
                    len(ids_solo_en_1),
                    len(ids_solo_en_2),
                    len(df_diferencias)
                ]
            }
            pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen', index=False)
            
            # Hojas con los detalles
            if not df_diferencias.empty:
                df_diferencias.to_excel(writer, sheet_name='Diferencias_de_Datos', index=False)
            if not df_solo_en_1.empty:
                df_solo_en_1.to_excel(writer, sheet_name='Solo_en_Metodo_1', index=False)
            if not df_solo_en_2.empty:
                df_solo_en_2.to_excel(writer, sheet_name='Solo_en_Metodo_2', index=False)
        
        print(f"\n✅ ¡Análisis completado! Se ha generado el reporte en el archivo: '{nombre_archivo}'")

    except Exception as e:
        print(f"\n❌ Ocurrió un error: {e}")
        print("   Por favor, verifica que las librerías 'pandas' y 'openpyxl' estén instaladas.")

if __name__ == '__main__':
    # 1. Pedir al usuario que elija el archivo de la base de datos
    db_file_path = elegir_base_de_datos()
    
    # 2. Ejecutar la comparación y exportación
    comparar_y_exportar(db_file_path)