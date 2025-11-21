class Rol:
    def __init__(self, nombre, permisos=None):
        self.nombre = nombre
        self.permisos = permisos or []

    def agregar_permiso(self, permiso):
        if permiso not in self.permisos:
            self.permisos.append(permiso)

    def quitar_permiso(self, permiso):
        if permiso in self.permisos:
            self.permisos.remove(permiso)

    def tiene_permiso(self, permiso):
        return permiso in self.permisos
