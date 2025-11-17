class Equipo:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.nombre = kwargs.get('nombre')
        self.mantenimiento_trigger_tipo = kwargs.get('mantenimiento_trigger_tipo', '')
        self.mantenimiento_trigger_valor = kwargs.get('mantenimiento_trigger_valor', 0)
        self.activo = kwargs.get('activo', 1)
