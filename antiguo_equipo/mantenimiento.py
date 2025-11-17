class Mantenimiento:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.equipo = kwargs.get('equipo')
        self.fecha = kwargs.get('fecha')
        self.descripcion = kwargs.get('descripcion', '')
        self.valor = kwargs.get('valor', 0)
        # Extras si tu modelo los usa
        self.tipo = kwargs.get('tipo', '')
        self.operador = kwargs.get('operador', '')
        self.comentario = kwargs.get('comentario', '')
