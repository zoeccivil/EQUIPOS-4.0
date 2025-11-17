import xml.etree.ElementTree as ET

class XMLUtils:
    """Utilidad para manejar operaciones con archivos XML."""

    @staticmethod
    def leer_xml(nombre_archivo):
        """Lee un archivo XML y retorna el árbol raíz."""
        try:
            tree = ET.parse(nombre_archivo)
            return tree.getroot()
        except Exception as e:
            print(f"Error leyendo XML: {e}")
            return None

    @staticmethod
    def escribir_xml(nombre_archivo, root):
        """Escribe un árbol raíz en un archivo XML."""
        try:
            tree = ET.ElementTree(root)
            tree.write(nombre_archivo, encoding='utf-8', xml_declaration=True)
            return True
        except Exception as e:
            print(f"Error escribiendo XML: {e}")
            return False

    @staticmethod
    def buscar_elementos(root, tag):
        """Busca todos los elementos por tag en el XML."""
        return root.findall(tag) if root is not None else []
