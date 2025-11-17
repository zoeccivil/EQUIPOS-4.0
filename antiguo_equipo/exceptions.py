class AppError(Exception):
    """Excepción general para la aplicación."""
    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje

class ValidacionError(AppError):
    """Excepción para errores de validación."""
    pass

class PermisoError(AppError):
    """Excepción para errores de permisos."""
    pass

class ConexionError(AppError):
    """Excepción para errores de conexión a base de datos u otros servicios."""
    pass
