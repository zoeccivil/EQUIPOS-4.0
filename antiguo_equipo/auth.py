import hashlib

class Auth:
    """Gestor simple de autenticación de usuarios."""

    def __init__(self, usuarios=None):
        # usuarios es un dict: {usuario: {"password": ..., "rol": ...}}
        self.usuarios = usuarios or {}

    def hash_password(self, password):
        """Devuelve el hash SHA256 del password."""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def registrar_usuario(self, usuario, password, rol="consulta"):
        """Registra un nuevo usuario."""
        if usuario in self.usuarios:
            return False
        self.usuarios[usuario] = {
            "password": self.hash_password(password),
            "rol": rol
        }
        return True

    def autenticar(self, usuario, password):
        """Verifica usuario y password, retorna rol si válido."""
        datos = self.usuarios.get(usuario)
        if not datos:
            return None
        if datos["password"] == self.hash_password(password):
            return datos["rol"]
        return None

    def cambiar_password(self, usuario, password_nuevo):
        if usuario in self.usuarios:
            self.usuarios[usuario]["password"] = self.hash_password(password_nuevo)
            return True
        return False
