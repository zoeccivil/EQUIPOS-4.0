class Abono:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.cliente = kwargs.get('cliente')
        self.fecha = kwargs.get('fecha')
        self.monto = kwargs.get('monto', 0)
        self.comentario = kwargs.get('comentario', '')
        # Extras si tu modelo los usa
        self.factura_aplicada = kwargs.get('factura_aplicada', '')
        self.transaccion_descripcion = kwargs.get('transaccion_descripcion', '')
