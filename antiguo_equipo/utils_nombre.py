import unicodedata
from datetime import datetime

def limpiar_nombre(nombre):
    """
    Elimina tildes y caracteres no válidos, 
    reemplaza espacios por guiones bajos y pone en mayúsculas.
    """
    nfkd = unicodedata.normalize('NFKD', nombre)
    solo_ascii = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return solo_ascii.replace(" ", "_").upper()

def generar_nombre_archivo(cliente_nombre, prefijo="Estado_Cuenta"):
    """
    Genera un nombre de archivo automático tipo:
    Estado_Cuenta_CLIENTE_YYYYMMDD_HHMMSS.pdf
    """
    nombre_limpio = limpiar_nombre(cliente_nombre)
    fecha_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefijo}_{nombre_limpio}_{fecha_hora}.pdf"
