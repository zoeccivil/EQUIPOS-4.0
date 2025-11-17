class Filters:
    @staticmethod
    def filtrar_por_fecha(lista, fecha_inicio=None, fecha_fin=None, clave='fecha'):
        """Filtra una lista de dicts por rango de fechas."""
        if not fecha_inicio and not fecha_fin:
            return lista
        resultado = []
        for item in lista:
            fecha = item.get(clave)
            if fecha:
                if fecha_inicio and fecha < fecha_inicio:
                    continue
                if fecha_fin and fecha > fecha_fin:
                    continue
            resultado.append(item)
        return resultado

    @staticmethod
    def filtrar_por_campo(lista, campo, valor):
        """Filtra una lista de dicts por campo y valor exacto."""
        if valor in (None, '', 'Todos'):
            return lista
        return [item for item in lista if item.get(campo) == valor]
