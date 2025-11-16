import time
from datetime import datetime, timedelta

class TimeUtils:
    """Utilidad para operaciones con fechas y horas."""

    @staticmethod
    def ahora():
        """Retorna la fecha y hora actual como string ISO."""
        return datetime.now().isoformat()

    @staticmethod
    def formatear_fecha(fecha, formato="%Y-%m-%d %H:%M:%S"):
        """Formatea un objeto datetime o string como fecha."""
        if isinstance(fecha, datetime):
            return fecha.strftime(formato)
        try:
            dt = datetime.fromisoformat(fecha)
            return dt.strftime(formato)
        except Exception:
            return str(fecha)

    @staticmethod
    def sumar_dias(fecha, dias):
        """Suma días a una fecha dada (datetime o string ISO)."""
        try:
            if isinstance(fecha, datetime):
                nueva = fecha + timedelta(days=dias)
            else:
                nueva = datetime.fromisoformat(fecha) + timedelta(days=dias)
            return nueva.isoformat()
        except Exception:
            return str(fecha)

    @staticmethod
    def diferencia_en_dias(fecha1, fecha2):
        """Calcula la diferencia en días entre dos fechas (datetime o string ISO)."""
        try:
            if not isinstance(fecha1, datetime):
                fecha1 = datetime.fromisoformat(fecha1)
            if not isinstance(fecha2, datetime):
                fecha2 = datetime.fromisoformat(fecha2)
            return abs((fecha2 - fecha1).days)
        except Exception:
            return None

    @staticmethod
    def esperar(segundos):
        """Espera el número de segundos indicados."""
        try:
            time.sleep(segundos)
            return True
        except Exception:
            return False
