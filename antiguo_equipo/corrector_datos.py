import sqlite3
import pandas as pd
from tkinter import filedialog, Tk
import sys

def elegir_archivo(titulo, tipos_archivo):
    """
    Abre un diálogo para que el usuario seleccione un archivo.
    """
    print(f"Por favor, selecciona el archivo: {titulo}...")
    root = Tk()
    root.withdraw()  # Oculta la ventana raíz
    
    filepath = filedialog.askopenfilename(
        title=titulo,
        filetypes=tipos_archivo
    )
    
    if not filepath:
        print(f"\n❌ No se seleccionó ningún archivo para '{titulo}'. Abortando.")
        sys.exit()
        
    print(f"Archivo seleccionado: {filepath}\n")
    return filepath

def corregir_datos():
    """
    Lee un reporte de Excel, encuentra los datos correctos usando la lógica del
    Método 1 y actualiza las filas en la base de datos.
    """
    # 1. Seleccionar los archivos necesarios
    excel_path = elegir_archivo(
        "Selecciona tu REPORTE de Excel",
        (("Archivos de Excel", "*.xlsx"),)
    )
    db_path = elegir_archivo(
        "Selecciona tu BASE DE DATOS (.db)",
        (("Archivos de base de datos", "*.db *.sqlite *.sqlite3"),)
    )

    try:
        # 2. Leer los IDs problemáticos del archivo de Excel
        ids_a_corregir = set()
        xls = pd.ExcelFile(excel_path)
        
        if 'Diferencias_de_Datos' in xls.sheet_names:
            df_diferencias = pd.read_excel(xls, sheet_name='Diferencias_de_Datos')
            ids_a_corregir.update(df_diferencias['ID_Transaccion'].unique())
            
        if 'Solo_en_Metodo_1' in xls.sheet_names:
            df_solo_1 = pd.read_excel(xls, sheet_name='Solo_en_Metodo_1')
            ids_a_corregir.update(df_solo_1['id'].unique())

        if not ids_a_corregir:
            print("✅ No se encontraron IDs para corregir en el archivo de Excel. No se necesita hacer nada.")
            return

        print(f"Se encontraron {len(ids_a_corregir)} registros para revisar y corregir.")

        # 3. Conectar a la BD y preparar las correcciones
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cambios_propuestos = []
        
        for trans_id in ids_a_corregir:
            # Buscar la información CORRECTA (cliente_id y operador_id de la tabla meta)
            cursor.execute("""
                SELECT cliente_id, operador_id 
                FROM equipos_alquiler_meta 
                WHERE transaccion_id = ?
            """, (trans_id,))
            resultado = cursor.fetchone()
            
            if resultado:
                cliente_id_correcto, operador_id_correcto = resultado
                
                # Proponemos el cambio para esta transacción
                cambios_propuestos.append({
                    'ID_Transaccion': trans_id,
                    'Accion': "UPDATE transacciones",
                    'Nuevo_Tipo': 'Ingreso',
                    'Nuevo_Cliente_ID': cliente_id_correcto,
                    'Nuevo_Operador_ID': operador_id_correcto
                })

        if not cambios_propuestos:
            print("No se encontraron datos de referencia para corregir los registros. No se puede continuar.")
            conn.close()
            return
            
        # 4. Mostrar los cambios al usuario y pedir confirmación
        df_cambios = pd.DataFrame(cambios_propuestos)
        print("\n--- CAMBIOS PROPUESTOS ---")
        print("El script aplicará las siguientes correcciones en la tabla 'transacciones':")
        print(df_cambios.to_string(index=False))
        
        confirmacion = input("\n¿Deseas aplicar estos cambios en la base de datos? (s/n): ").lower()
        
        if confirmacion == 's':
            print("\n aplicando cambios...")
            for cambio in cambios_propuestos:
                cursor.execute("""
                    UPDATE transacciones
                    SET tipo = ?, cliente_id = ?, operador_id = ?
                    WHERE id = ?
                """, (
                    cambio['Nuevo_Tipo'],
                    cambio['Nuevo_Cliente_ID'],
                    cambio['Nuevo_Operador_ID'],
                    cambio['ID_Transaccion']
                ))
            
            conn.commit()
            print(f"✅ ¡Éxito! Se han actualizado {len(cambios_propuestos)} registros en la base de datos.")
        else:
            print("❌ Operación cancelada por el usuario. No se realizó ningún cambio.")
            
    except Exception as e:
        print(f"\n❌ Ocurrió un error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    corregir_datos()