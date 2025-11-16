import json
import os

CONFIG_FILE = 'equipos_config.json'  # El nombre fijo del archivo de configuración

def guardar_configuracion(config: dict):
    """Guarda la configuración en un archivo JSON."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

def cargar_configuracion() -> dict:
    """Carga la configuración desde el archivo JSON."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)
