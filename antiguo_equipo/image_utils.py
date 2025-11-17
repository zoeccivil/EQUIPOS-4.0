from PIL import Image

class ImageUtils:
    """Utilidad para operaciones básicas con archivos de imagen."""

    @staticmethod
    def abrir_imagen(nombre_archivo):
        """Abre una imagen y retorna el objeto Image."""
        try:
            return Image.open(nombre_archivo)
        except Exception as e:
            print(f"Error abriendo imagen: {e}")
            return None

    @staticmethod
    def redimensionar_imagen(imagen, ancho, alto):
        """Redimensiona una imagen al tamaño especificado."""
        try:
            return imagen.resize((ancho, alto))
        except Exception as e:
            print(f"Error redimensionando imagen: {e}")
            return None

    @staticmethod
    def guardar_imagen(imagen, nombre_archivo):
        """Guarda el objeto Image como archivo."""
        try:
            imagen.save(nombre_archivo)
            return True
        except Exception as e:
            print(f"Error guardando imagen: {e}")
            return False

    @staticmethod
    def convertir_a_grises(imagen):
        """Convierte la imagen a escala de grises."""
        try:
            return imagen.convert("L")
        except Exception as e:
            print(f"Error convirtiendo imagen a grises: {e}")
            return None
