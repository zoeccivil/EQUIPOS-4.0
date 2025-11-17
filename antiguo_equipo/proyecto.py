class Proyecto:
    def __init__(self, db_manager, proyecto_id):
        self.db = db_manager
        self.id = proyecto_id
        datos = self.db.obtener_proyecto_por_id(proyecto_id)
        self.nombre = datos.get("nombre", "")
        self.moneda = datos.get("moneda", "RD$")

    # Puedes agregar más métodos útiles aquí si necesitas
    # Por ejemplo, para cargar estadísticas, KPIs, etc.
