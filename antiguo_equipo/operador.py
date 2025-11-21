class Operador:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.nombre = kwargs.get('nombre')
        self.telefono = kwargs.get('telefono', '')
        self.cedula = kwargs.get('cedula', '')
        self.activo = kwargs.get('activo', 1)
