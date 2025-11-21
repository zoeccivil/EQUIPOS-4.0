import uuid

class UUIDUtils:
    """Utilidad para generar y validar identificadores UUID."""

    @staticmethod
    def generar_uuid():
        """Genera un UUID versión 4 (aleatorio)."""
        return str(uuid.uuid4())

    @staticmethod
    def validar_uuid(valor):
        """Valida si una cadena corresponde a un UUID válido."""
        try:
            uuid_obj = uuid.UUID(valor, version=4)
            return str(uuid_obj) == valor
        except Exception:
            return False
