#!/usr/bin/env python3
import os
import shutil
import subprocess
import logging

# ==============================================================================
# 1. CONFIGURACIÓN DE SISTEMA Y LOGS
# ==============================================================================
LOG_FILE = "/var/log/guadamint/update.log"
os.makedirs("/var/log/guadamint", exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Salida paralela a consola (para pruebas manuales)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger("").addHandler(console)

# ==============================================================================
# 2. RUTAS Y ARCHIVOS OBJETIVO
# ==============================================================================
INSTALL_DIR = "/opt/guadamint"
DEST_BIN = "/usr/bin/guadamint-update.py"
REPO_URL = "https://github.com/TU_USUARIO/TU_REPO.git"  # <-- Cambia esto por tu URL real de GitHub
BRANCH = "eos"

# Tamaño exacto reportado por 'du -k' en EducaAndOSv2 original
BACKGROUNDS_CONFIG = {
    "EducaAndOSv2-background.png": {
        "du_kb": 16428,
        "source": os.path.join(INSTALL_DIR, "images/EducaAndOSv2-background.png")
    },
    "EducaAndOSv2-background-dark.png": {
        "du_kb": 2012,
        "source": os.path.join(INSTALL_DIR, "images/EducaAndOSv2-background-dark.png")
    },
    "EducaAndOSv2-login.png": {
        "du_kb": 1532,
        "source": os.path.join(INSTALL_DIR, "images/EducaAndOSv2-login.png")
    }
}

TARGET_DIRECTORIES = [
    "/usr/share/backgrounds",
    "/usr/share/sar-artwork"
]

# ==============================================================================
# 3. FUNCIONES AUXILIARES
# ==============================================================================
def get_disk_usage_kb(file_path):
    """Obtiene el tamaño exacto en disco simulando 'du -k'."""
    try:
        output = subprocess.check_output(["du", "-k", file_path]).decode().split()
        return int(output[0])
    except Exception as e:
        logging.error(f"Error midiendo {file_path}: {e}")
        return os.path.getsize(file_path) // 1024

def check_and_replace_backgrounds():
    """Verifica el tamaño original del sistema y sustituye por los fondos propios."""
    logging.info("--- Iniciando comprobación de fondos de pantalla ---")
    for directory in TARGET_DIRECTORIES:
        if not os.path.isdir(directory):
            continue

        for filename, info in BACKGROUNDS_CONFIG.items():
            target_path = os.path.join(directory, filename)
            source_path = info["source"]

            # Comprobar que existen el destino y el reemplazo en /opt/guadamint/images/
            if os.path.isfile(target_path) and os.path.isfile(source_path):
                try:
                    current_du_kb = get_disk_usage_kb(target_path)

                    if current_du_kb == info["du_kb"]:
                        logging.info(f"Fondo original detectado ({current_du_kb} KB). Reemplazando {filename} en {directory}...")
                        shutil.copy2(source_path, target_path)
                        os.chmod(target_path, 0o644)
                        logging.info(f"¡Sustitución con éxito en {target_path}!")
                    else:
                        logging.debug(f"{target_path} no requiere cambios (peso actual: {current_du_kb} KB).")
                except Exception as error:
                    logging.error(f"Error al procesar {target_path}: {error}")
            else:
                if not os.path.isfile(source_path):
                    logging.warning(f"No se encuentra el archivo fuente: {source_path}")

def update_from_git():
    """Mantiene el proyecto al día via Git y auto-actualiza el propio ejecutable."""
    logging.info("--- Iniciando actualización por Git ---")
    
    # 1. Clonar si es el primer arranque o hacer pull si ya existe
    if not os.path.exists(os.path.join(INSTALL_DIR, ".git")):
        logging.info("Primer inicio detectado: Clonando repositorio...")
        res = subprocess.run(["git", "clone", "-b", BRANCH, REPO_URL, INSTALL_DIR], capture_output=True, text=True)
        logging.info(f"Salida Git Clone: {res.stdout.strip()}")
    else:
        logging.info("Buscando cambios en GitHub (git pull)...")
        res = subprocess.run(["git", "-C", INSTALL_DIR, "pull"], capture_output=True, text=True)
        logging.info(f"Salida Git Pull: {res.stdout.strip()}")

    # 2. Auto-copiarse a /usr/bin/ si ha cambiado el archivo en el repositorio
    src_script = os.path.join(INSTALL_DIR, "src/guadamint-update.py")
    if os.path.isfile(src_script) and os.path.isfile(DEST_BIN):
        try:
            shutil.copy2(src_script, DEST_BIN)
            os.chmod(DEST_BIN, 0o755)
            logging.info("Ejecutable /usr/bin/guadamint-update.py actualizado correctamente.")
        except Exception as e:
            logging.error(f"Error auto-actualizando el ejecutable binario: {e}")

# ==============================================================================
# 4. PUNTO DE ENTRADA
# ==============================================================================
if __name__ == "__main__":
    logging.info("=== INICIO DE PROCESO GUADAMINT UPDATE ===")
    try:
        update_from_git()
        check_and_replace_backgrounds()
    except Exception as global_error:
        logging.critical(f"Fallo no controlado en la ejecución: {global_error}")
    logging.info("=== FIN DE PROCESO GUADAMINT UPDATE ===")
