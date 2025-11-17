import os
import subprocess
from PyQt6.QtWidgets import QMessageBox

def abrir_conduce_adjunto(self, conduce_adjunto_path):
    """
    Abre el archivo del conduce adjunto usando el visualizador del sistema.
    conduce_adjunto_path: str (ejemplo: '2025/10/00456.pdf')
    """
    if not conduce_adjunto_path:
        QMessageBox.warning(self, "Sin archivo", "No existe un archivo adjunto para este alquiler.")
        return

    # Obtén la carpeta base desde la config
    base_dir = self.config.get('dropbox_base_path', './adjuntos')
    archivo_absoluto = os.path.abspath(os.path.join(base_dir, conduce_adjunto_path))

    if not os.path.isfile(archivo_absoluto):
        QMessageBox.critical(self, "Error", f"El archivo no existe:\n{archivo_absoluto}")
        return

    try:
        # Abrir con el visualizador predeterminado según sistema operativo
        if os.name == 'nt':  # Windows
            os.startfile(archivo_absoluto)
        elif os.name == 'posix':
            subprocess.Popen(['xdg-open', archivo_absoluto])
        else:
            QMessageBox.information(self, "Info", "No se puede abrir automáticamente en este sistema.")
    except Exception as e:
        QMessageBox.critical(self, "Error", f"No se pudo abrir el archivo:\n{e}")
