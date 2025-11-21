import os
import json

class SessionManager:
    """Gestor de sesiones de usuario para la aplicación."""

    def __init__(self, archivo_sesion="session.json"):
        self.archivo_sesion = archivo_sesion
        self.sesion = self.cargar_sesion()

    def cargar_sesion(self):
        if not os.path.exists(self.archivo_sesion):
            return self.sesion_por_defecto()
        with open(self.archivo_sesion, "r", encoding="utf-8") as f:
            return json.load(f)

    def guardar_sesion(self, datos):
        with open(self.archivo_sesion, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4)
        self.sesion = datos

    def cerrar_sesion(self):
        if os.path.exists(self.archivo_sesion):
            os.remove(self.archivo_sesion)
        self.sesion = self.sesion_por_defecto()

    def sesion_por_defecto(self):
        return {
            "usuario": None,
            "rol": "consulta",
            "activa": False
        }
