import os

class EnvUtils:
    """Utilidad para manejo de variables de entorno."""

    @staticmethod
    def obtener_variable(nombre, defecto=None):
        """Obtiene el valor de una variable de entorno, o retorna el defecto si no existe."""
        return os.environ.get(nombre, defecto)

    @staticmethod
    def establecer_variable(nombre, valor):
        """Establece una variable de entorno temporalmente (solo para el proceso actual)."""
        os.environ[nombre] = str(valor)
        return True

    @staticmethod
    def eliminar_variable(nombre):
        """Elimina una variable de entorno del proceso actual."""
        try:
            del os.environ[nombre]
            return True
        except KeyError:
            return False

    @staticmethod
    def listar_variables():
        """Retorna un dict con todas las variables de entorno del proceso actual."""
        return dict(os.environ)
