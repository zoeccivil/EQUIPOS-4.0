class Validators:
    @staticmethod
    def validar_cedula(cedula: str):
        """Valida el formato de una cédula dominicana."""
        # Permite formatos 000-0000000-0 o solo números
        import re
        patron = r'^(\d{3}-\d{7}-\d{1}|\d{11})$'
        return bool(re.match(patron, cedula))

    @staticmethod
    def validar_telefono(telefono: str):
        """Valida formato básico de teléfono dominicano."""
        import re
        patron = r'^(\d{3}-\d{3}-\d{4}|\d{10})$'
        return bool(re.match(patron, telefono))

    @staticmethod
    def validar_monto(monto):
        """Valida que el monto sea un número positivo."""
        try:
            return float(monto) >= 0
        except Exception:
            return False
