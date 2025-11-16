import uuid
from PyQt6.QtWidgets import QMessageBox

def guardar_alquiler(self):
    datos = self.get_datos()
    db = self.db  # Tu objeto DatabaseManager o similar

    # 1. Obtener la cuenta principal del proyecto 8
    row = db.fetchone("SELECT cuenta_principal FROM proyectos WHERE id = 8")
    if not row:
        QMessageBox.critical(self, "Error", "No se encontró el proyecto 8 en la base de datos.")
        return
    cuenta_nombre = row['cuenta_principal']
    row_cuenta = db.fetchone("SELECT id FROM cuentas WHERE nombre = ?", (cuenta_nombre,))
    if not row_cuenta:
        QMessageBox.critical(self, "Error", f"No se encontró la cuenta '{cuenta_nombre}'.")
        return
    cuenta_id = row_cuenta['id']

    # 2. Obtener el id de la categoría "ALQUILERES"
    row_cat = db.fetchone("SELECT id FROM categorias WHERE UPPER(nombre) = 'ALQUILERES'")
    if not row_cat:
        QMessageBox.critical(self, "Error", "No se encontró la categoría 'ALQUILERES'.")
        return
    categoria_id = row_cat['id']

    # 3. Obtener el id de la subcategoría igual al equipo seleccionado
    equipo_nombre = self.equipo_combo.currentText()
    row_subcat = db.fetchone("SELECT id FROM subcategorias WHERE nombre = ?", (equipo_nombre,))
    if not row_subcat:
        QMessageBox.warning(self, "Error", f"No existe la subcategoría para el equipo '{equipo_nombre}'. Debes crearla primero en la tabla subcategorias.")
        return
    subcategoria_id = row_subcat['id']

    # 4. Descripción automática
    horas = datos['horas']
    cliente_nombre = self.cliente_combo.currentText()
    descripcion = f"{horas} horas de equipo {equipo_nombre}, Cliente {cliente_nombre}"

    # 5. Insertar en transacciones
    transac = {
        'id': uuid.uuid4().hex,  # id TEXT, usa UUID para compatibilidad
        'proyecto_id': 8,
        'cuenta_id': cuenta_id,
        'categoria_id': categoria_id,
        'subcategoria_id': subcategoria_id,
        'tipo': 'Ingreso',
        'descripcion': descripcion,
        'comentario': '',  # o lo que quieras poner
        'monto': datos['monto'],
        'fecha': datos['fecha'],
        'cliente_id': datos['cliente_id'],
        'operador_id': datos['operador_id'],
        'conduce': datos['conduce'],
        'ubicacion': datos['ubicacion'],
        'horas': datos['horas'],
        'precio_por_hora': datos['precio_por_hora'],
        'pagado': 0,
        'kilometros': 0,
        'equipo_id': datos['equipo_id'],
        'conduce_adjunto_path': datos['conduce_adjunto_path'],
    }

    db.execute("""
        INSERT INTO transacciones
        (id, proyecto_id, cuenta_id, categoria_id, subcategoria_id, tipo, descripcion, comentario,
         monto, fecha, cliente_id, operador_id, conduce, ubicacion, horas, precio_por_hora,
         pagado, kilometros, equipo_id, conduce_adjunto_path)
        VALUES
        (:id, :proyecto_id, :cuenta_id, :categoria_id, :subcategoria_id, :tipo, :descripcion, :comentario,
         :monto, :fecha, :cliente_id, :operador_id, :conduce, :ubicacion, :horas, :precio_por_hora,
         :pagado, :kilometros, :equipo_id, :conduce_adjunto_path)
    """, transac)

    # 6. Insertar en equipos_alquiler_meta
    db.execute("""
        INSERT INTO equipos_alquiler_meta
        (transaccion_id, proyecto_id, cliente_id, operador_id, horas, precio_por_hora,
         conduce, ubicacion, conduce_adjunto_path, equipo_id)
        VALUES
        (:transaccion_id, :proyecto_id, :cliente_id, :operador_id, :horas, :precio_por_hora,
         :conduce, :ubicacion, :conduce_adjunto_path, :equipo_id)
    """, {
        'transaccion_id': transac['id'],
        'proyecto_id': 8,
        'cliente_id': datos['cliente_id'],
        'operador_id': datos['operador_id'],
        'horas': datos['horas'],
        'precio_por_hora': datos['precio_por_hora'],
        'conduce': datos['conduce'],
        'ubicacion': datos['ubicacion'],
        'conduce_adjunto_path': datos['conduce_adjunto_path'],
        'equipo_id': datos['equipo_id'],
    })

    QMessageBox.information(self, "Éxito", "Alquiler registrado correctamente.")
    self.accept()