from txt_utils import TXTUtils
from html_utils import HTMLUtils
from doc_utils import DocUtils
from image_utils import ImageUtils
from zip_utils import ZipUtils
from tar_utils import TarUtils
from rar_utils import RARUtils
from csv_utils import CSVUtils
from uuid_utils import UUIDUtils
from time_utils import TimeUtils
from env_utils import EnvUtils
from hash_utils import HashUtils
from shell_utils import ShellUtils
from logger_utils import LoggerUtils
from http_utils import HTTPUtils

def probar_txt():
    print("== TXT ==")
    TXTUtils.escribir_txt("prueba.txt", "Texto de prueba desde consola.")
    print(TXTUtils.leer_txt("prueba.txt"))

def probar_html():
    print("== HTML ==")
    TXTUtils.escribir_txt("prueba.html", "<html><body><h1>Hola HTML</h1><p>Prueba HTML.</p></body></html>")
    soup = HTMLUtils.leer_html("prueba.html")
    print("Texto extraído:", HTMLUtils.extraer_texto(soup))

def probar_docx():
    print("== DOCX ==")
    DocUtils.escribir_docx("prueba.docx", ["Línea uno", "Línea dos"], titulo="Título DOCX")
    print(DocUtils.leer_docx("prueba.docx"))

def probar_imagen():
    print("== Imagen ==")
    try:
        img = ImageUtils.abrir_imagen("imagen.jpg")
        gris = ImageUtils.convertir_a_grises(img)
        ImageUtils.guardar_imagen(gris, "imagen_gris.jpg")
        redim = ImageUtils.redimensionar_imagen(img, 50, 50)
        ImageUtils.guardar_imagen(redim, "imagen_redim.jpg")
        print("Imagen procesada y guardada.")
    except Exception as e:
        print("Error imagen:", e)

def probar_zip():
    print("== ZIP ==")
    ZipUtils.comprimir_archivos("prueba.zip", ["prueba.txt", "prueba.html"])
    print("Contenido ZIP:", ZipUtils.listar_contenido("prueba.zip"))
    ZipUtils.descomprimir_archivo("prueba.zip", "descomprimido_zip")

def probar_tar():
    print("== TAR ==")
    TarUtils.comprimir_archivos("prueba.tar.gz", ["prueba.txt", "prueba.html"])
    print("Contenido TAR:", TarUtils.listar_contenido("prueba.tar.gz"))
    TarUtils.descomprimir_archivo("prueba.tar.gz", "descomprimido_tar")

def probar_rar():
    print("== RAR ==")
    try:
        print("Contenido RAR:", RARUtils.listar_contenido("prueba.rar"))
        RARUtils.extraer_archivo("prueba.rar", "descomprimido_rar")
    except Exception as e:
        print("Error RAR:", e)

def probar_csv():
    print("== CSV ==")
    datos = [{"nombre": "Juan", "edad": 22}, {"nombre": "Maria", "edad": 28}]
    CSVUtils.escribir_csv("prueba.csv", datos, ["nombre", "edad"])
    print("Datos CSV:", CSVUtils.leer_csv("prueba.csv"))

def probar_uuid():
    print("== UUID ==")
    uuid = UUIDUtils.generar_uuid()
    print("UUID generado:", uuid)
    print("UUID válido:", UUIDUtils.validar_uuid(uuid))

def probar_time():
    print("== Time ==")
    ahora = TimeUtils.ahora()
    print("Fecha ahora:", ahora)
    print("Formateada:", TimeUtils.formatear_fecha(ahora))
    print("Sumar 2 días:", TimeUtils.sumar_dias(ahora, 2))
    print("Dif días:", TimeUtils.diferencia_en_dias(ahora, TimeUtils.sumar_dias(ahora, 2)))

def probar_env():
    print("== Env ==")
    EnvUtils.establecer_variable("MI_ENV", "valor123")
    print("MI_ENV:", EnvUtils.obtener_variable("MI_ENV"))
    EnvUtils.eliminar_variable("MI_ENV")
    print("Variables ejemplo:", list(EnvUtils.listar_variables().keys())[:5])

def probar_hash():
    print("== Hash ==")
    h = HashUtils.generar_hash("test123")
    print("Hash de 'test123':", h)
    print("Verificar hash:", HashUtils.verificar_hash("test123", h))
    print("Hash archivo:", HashUtils.hash_archivo("prueba.txt"))

def probar_shell():
    print("== Shell ==")
    res = ShellUtils.ejecutar_comando("echo Prueba desde shell")
    print("STDOUT:", res["stdout"].strip())

def probar_logger():
    print("== Logger ==")
    logger = LoggerUtils.configurar_logger()
    LoggerUtils.info(logger, "Mensaje info")
    LoggerUtils.error(logger, "Mensaje error")
    LoggerUtils.debug(logger, "Mensaje debug")

def probar_http():
    print("== HTTP ==")
    print("GET google:", HTTPUtils.get("https://www.google.com"))
    print("POST ejemplo:", HTTPUtils.post("https://httpbin.org/post", data={"campo": "valor"}))

def main():
    probar_txt()
    probar_html()
    probar_docx()
    probar_imagen()
    probar_zip()
    probar_tar()
    probar_rar()
    probar_csv()
    probar_uuid()
    probar_time()
    probar_env()
    probar_hash()
    probar_shell()
    probar_logger()
    probar_http()

if __name__ == "__main__":
    main()
