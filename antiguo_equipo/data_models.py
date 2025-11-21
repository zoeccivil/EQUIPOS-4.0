class Proyecto:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.nombre = kwargs.get('nombre')
        self.descripcion = kwargs.get('descripcion', '')
        self.fecha_inicio = kwargs.get('fecha_inicio')
        self.fecha_fin = kwargs.get('fecha_fin')
        self.activo = kwargs.get('activo', 1)

class Gasto:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.proyecto_id = kwargs.get('proyecto_id')
        self.monto = kwargs.get('monto', 0)
        self.fecha = kwargs.get('fecha')
        self.descripcion = kwargs.get('descripcion', '')
        self.categoria_id = kwargs.get('categoria_id')
        self.equipo_id = kwargs.get('equipo_id')
