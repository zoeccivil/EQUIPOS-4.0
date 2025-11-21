import logging

class LoggerUtils:
    """Utilidad para configuración y uso de logging."""

    @staticmethod
    def configurar_logger(nombre_logger="appLogger", nivel=logging.INFO, archivo=None):
        """
        Configura el logger principal.
        nombre_logger: nombre del logger.
        nivel: nivel de logging (ej. logging.DEBUG, logging.INFO).
        archivo: si se indica, escribe los logs en el archivo.
        """
        logger = logging.getLogger(nombre_logger)
        logger.setLevel(nivel)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        if archivo:
            fh = logging.FileHandler(archivo, encoding="utf-8")
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        else:
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            logger.addHandler(ch)
        return logger

    @staticmethod
    def info(logger, mensaje):
        """Escribe un mensaje de info en el logger."""
        logger.info(mensaje)

    @staticmethod
    def error(logger, mensaje):
        """Escribe un mensaje de error en el logger."""
        logger.error(mensaje)

    @staticmethod
    def debug(logger, mensaje):
        """Escribe un mensaje de debug en el logger."""
        logger.debug(mensaje)
