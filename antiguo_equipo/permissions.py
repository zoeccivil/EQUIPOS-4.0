class Permissions:
    """Gestor simple de permisos y roles para la aplicación."""

    ROLES = [
        "admin",
        "editor",
        "consulta"
    ]

    PERMISOS = {
        "admin": [
            "ver_dashboard",
            "gestionar_proyectos",
            "gestionar_clientes",
            "gestionar_operadores",
            "gestionar_equipos",
            "gestionar_gastos",
            "gestionar_mantenimientos",
            "exportar_reportes"
        ],
        "editor": [
            "ver_dashboard",
            "gestionar_clientes",
            "gestionar_operadores",
            "gestionar_equipos",
            "gestionar_gastos",
            "gestionar_mantenimientos"
        ],
        "consulta": [
            "ver_dashboard"
        ]
    }

    @staticmethod
    def tiene_permiso(rol, permiso):
        """Verifica si el rol tiene el permiso dado."""
        return permiso in Permissions.PERMISOS.get(rol, [])

    @staticmethod
    def es_admin(rol):
        return rol == "admin"
