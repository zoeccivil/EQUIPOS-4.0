import json

class JSONUtils:
    """Utilidad para manejar operaciones con archivos JSON."""

    @staticmethod
    def leer_json(nombre_archivo):
        """Lee un archivo JSON y retorna el contenido como dict."""
        try:
            with open(nombre_archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error leyendo JSON: {e}")
            return None

    @staticmethod
    def escribir_json(nombre_archivo, datos):
        """Escribe un dict en un archivo JSON."""
        try:
            with open(nombre_archivo, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=4)
            return True
        except Exception as e:
            print(f"Error escribiendo JSON: {e}")
            return False
