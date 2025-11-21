class equipo:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.nombre = kwargs.get('nombre')
        self.categoria_id = kwargs.get('categoria_id')
        self.descripcion = kwargs.get('descripcion', '')
        self.activo = kwargs.get('activo', 1)
