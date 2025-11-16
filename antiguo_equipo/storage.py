import json
import os

class Storage:
    """Gestor simple para guardar y cargar datos persistentes."""

    @staticmethod
    def guardar_json(nombre_archivo, datos):
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=4)

    @staticmethod
    def cargar_json(nombre_archivo):
        if not os.path.exists(nombre_archivo):
            return None
        with open(nombre_archivo, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def existe_archivo(nombre_archivo):
        return os.path.exists(nombre_archivo)
