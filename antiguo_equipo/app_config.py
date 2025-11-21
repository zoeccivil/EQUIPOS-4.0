import os

class AppConfig:
    """Gestor de configuración general para la aplicación."""

    def __init__(self, archivo_config="config.json"):
        self.archivo_config = archivo_config
        self.config = self.cargar_configuracion()

    def cargar_configuracion(self):
        if not os.path.exists(self.archivo_config):
            return self.config_por_defecto()
        import json
        with open(self.archivo_config, "r", encoding="utf-8") as f:
            return json.load(f)

    def guardar_configuracion(self, datos):
        import json
        with open(self.archivo_config, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4)
        self.config = datos

    def config_por_defecto(self):
        return {
            "moneda": "RD$",
            "idioma": "es",
            "tema": "claro",
            "ruta_bd": "database.db"
        }
