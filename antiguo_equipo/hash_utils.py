import hashlib

class HashUtils:
    """Utilidad para generar y verificar hashes."""

    @staticmethod
    def generar_hash(texto, algoritmo="sha256"):
        """Genera un hash de un string utilizando el algoritmo indicado."""
        try:
            h = hashlib.new(algoritmo)
            h.update(texto.encode("utf-8"))
            return h.hexdigest()
        except Exception as e:
            print(f"Error generando hash: {e}")
            return None

    @staticmethod
    def verificar_hash(texto, hash_valor, algoritmo="sha256"):
        """Verifica si el hash de un texto corresponde al valor dado."""
        try:
            return HashUtils.generar_hash(texto, algoritmo) == hash_valor
        except Exception as e:
            print(f"Error verificando hash: {e}")
            return False

    @staticmethod
    def hash_archivo(nombre_archivo, algoritmo="sha256"):
        """Genera el hash de un archivo completo."""
        try:
            h = hashlib.new(algoritmo)
            with open(nombre_archivo, "rb") as f:
                for bloque in iter(lambda: f.read(4096), b""):
                    h.update(bloque)
            return h.hexdigest()
        except Exception as e:
            print(f"Error generando hash de archivo: {e}")
            return None
