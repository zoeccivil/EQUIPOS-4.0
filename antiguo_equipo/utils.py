import re

class Utils:
    @staticmethod
    def limpiar_numero(texto: str):
        """Limpia un texto para dejar solo números (por ejemplo, para cédulas, teléfonos, etc.)"""
        return re.sub(r'\D', '', texto)

    @staticmethod
    def moneda_formateada(valor, moneda="RD$"):
        """Devuelve el valor formateado como moneda local."""
        try:
            return f"{moneda} {float(valor):,.2f}"
        except Exception:
            return f"{moneda} {valor}"

    @staticmethod
    def capitalize(texto: str):
        if texto:
            return texto[0].upper() + texto[1:]
        return texto
