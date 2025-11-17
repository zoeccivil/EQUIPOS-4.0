import csv

class CSVUtils:
    """Utilidad para manejar archivos CSV."""

    @staticmethod
    def leer_csv(nombre_archivo):
        """Lee un archivo CSV y retorna una lista de dicts."""
        datos = []
        with open(nombre_archivo, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                datos.append(row)
        return datos

    @staticmethod
    def escribir_csv(nombre_archivo, datos, campos):
        """Escribe una lista de dicts en un archivo CSV."""
        with open(nombre_archivo, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            for row in datos:
                writer.writerow(row)
        return nombre_archivo
