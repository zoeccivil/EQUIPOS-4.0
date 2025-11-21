import datetime

class Logger:
    """Registro simple de eventos y errores para la aplicación."""

    def __init__(self, archivo_log="app.log"):
        self.archivo_log = archivo_log

    def log(self, mensaje, tipo="INFO"):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linea = f"[{timestamp}] {tipo}: {mensaje}\n"
        with open(self.archivo_log, "a", encoding="utf-8") as f:
            f.write(linea)

    def log_error(self, mensaje):
        self.log(mensaje, tipo="ERROR")

    def log_evento(self, mensaje):
        self.log(mensaje, tipo="EVENTO")
