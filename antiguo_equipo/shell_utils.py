import subprocess

class ShellUtils:
    """Utilidad para ejecutar comandos de terminal o shell."""

    @staticmethod
    def ejecutar_comando(comando, shell=True):
        """
        Ejecuta un comando en la terminal y retorna la salida (stdout, stderr, returncode).
        comando: string o lista de argumentos.
        shell: True para usar el shell, False para lista de argumentos.
        """
        try:
            resultado = subprocess.run(
                comando,
                shell=shell,
                capture_output=True,
                text=True
            )
            return {
                "stdout": resultado.stdout,
                "stderr": resultado.stderr,
                "returncode": resultado.returncode
            }
        except Exception as e:
            print(f"Error ejecutando comando: {e}")
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
