import sqlite3

class DBManager:
    """Gestor básico para conexión y operaciones con base de datos SQLite."""

    def __init__(self, db_path="database.db"):
        self.db_path = db_path
        self.conn = None

    def conectar(self):
        """Realiza la conexión con la base de datos."""
        self.conn = sqlite3.connect(self.db_path)
        return self.conn

    def cerrar(self):
        """Cierra la conexión."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def ejecutar(self, query, params=None):
        """Ejecuta una consulta SQL."""
        if self.conn is None:
            self.conectar()
        cur = self.conn.cursor()
        if params is None:
            cur.execute(query)
        else:
            cur.execute(query, params)
        self.conn.commit()
        return cur

    def consultar(self, query, params=None):
        """Realiza una consulta y retorna los resultados."""
        if self.conn is None:
            self.conectar()
        cur = self.conn.cursor()
        if params is None:
            cur.execute(query)
        else:
            cur.execute(query, params)
        return cur.fetchall()
