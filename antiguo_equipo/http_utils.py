import requests

class HTTPUtils:
    """Utilidad para realizar solicitudes HTTP básicas."""

    @staticmethod
    def get(url, params=None, headers=None, timeout=10):
        """Realiza una solicitud GET y retorna la respuesta."""
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error en solicitud GET: {e}")
            return None

    @staticmethod
    def post(url, data=None, json_data=None, headers=None, timeout=10):
        """Realiza una solicitud POST y retorna la respuesta."""
        try:
            response = requests.post(url, data=data, json=json_data, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error en solicitud POST: {e}")
            return None

    @staticmethod
    def descargar_archivo(url, nombre_archivo, headers=None, timeout=20):
        """Descarga un archivo desde una URL y lo guarda localmente."""
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            with open(nombre_archivo, "wb") as f:
                f.write(response.content)
            return True
        except Exception as e:
            print(f"Error descargando archivo: {e}")
            return False
