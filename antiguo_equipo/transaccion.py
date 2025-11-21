class Transaccion:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.fecha = kwargs.get('fecha')
        self.conduce = kwargs.get('conduce')
        self.cliente = kwargs.get('cliente')
        self.operador = kwargs.get('operador')
        self.equipo = kwargs.get('equipo')
        self.ubicacion = kwargs.get('ubicacion')
        self.horas = kwargs.get('horas', 0)
        self.precio_por_hora = kwargs.get('precio_por_hora', 0)
        self.monto = kwargs.get('monto', 0)
        self.pagado = kwargs.get('pagado', False)
        # Extras si tu modelo los usa
        self.cliente_nombre = kwargs.get('cliente_nombre', self.cliente)
        self.operador_nombre = kwargs.get('operador_nombre', self.operador)
        self.equipo_nombre = kwargs.get('equipo_nombre', self.equipo)
