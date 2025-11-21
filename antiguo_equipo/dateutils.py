from datetime import datetime, date

class DateUtils:
    @staticmethod
    def hoy():
        return date.today()

    @staticmethod
    def str_to_date(fecha_str):
        try:
            return datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except Exception:
            return None

    @staticmethod
    def date_to_str(fecha_obj):
        if isinstance(fecha_obj, date):
            return fecha_obj.strftime("%Y-%m-%d")
        return ""
