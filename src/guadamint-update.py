#!/usr/bin/env python3
import os
import shutil
import subprocess
import logging

# 1. LOGS
LOG_FILE = "/var/log/guadamint/update.log"
os.makedirs("/var/log/guadamint", exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 2. CONFIGURACIÓN Y RUTAS
INSTALL_DIR = "/opt/guadamint"
DEST_BIN = "/usr/bin/guadamint-update.py"
REPO_URL = "https://github.com/aosucas499/guadamint"  
BRANCH = "eos"

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

TARGET_DIRECTORIES = ["/usr/share/backgrounds", "/usr/share/sar-artwork"]

def get_disk_usage_kb(file_path):
    """Mide el tamaño exacto del archivo simulando du -k."""
    try:
        output = subprocess.check_output(["du", "-k", file_path]).decode().split()
        return int(output[0])
    except Exception:
        return os.path.getsize(file_path) // 1024

def check_and_replace_backgrounds():
    """Sustituye imágenes originales si coincide el tamaño du -k."""
    for directory in TARGET_DIRECTORIES:
        if not os.path.isdir(directory):
            continue

        for filename, info in BACKGROUNDS_CONFIG.items():
            target_path = os.path.join(directory, filename)
            source_path = info["source"]

            if os.path.isfile(target_path) and os.path.isfile(source_path):
                try:
                    current_du_kb = get_disk_usage_kb(target_path)

                    if current_du_kb == info["du_kb"]:
                        logging.info(f"Reemplazando {filename} en {directory}...")
                        shutil.copy2(source_path, target_path)
                        os.chmod(target_path, 0o644)
                except Exception as error:
                    logging.error(f"Error procesando {target_path}: {error}")

def update_from_git():
    """Mantiene /opt/guadamint actualizado vía Git y se auto-copia a /usr/bin/."""
    if not os.path.exists(os.path.join(INSTALL_DIR, ".git")):
        logging.info("Clonando repositorio por primera vez...")
        subprocess.run(["git", "clone", "-b", BRANCH, REPO_URL, INSTALL_DIR], check=False)
    else:
        logging.info("Ejecutando git pull...")
        subprocess.run(["git", "-C", INSTALL_DIR, "pull"], check=False)

    # Copiar última versión a /usr/bin/
    src_script = os.path.join(INSTALL_DIR, "src/guadamint-update.py")
    if os.path.isfile(src_script) and os.path.isfile(DEST_BIN):
        shutil.copy2(src_script, DEST_BIN)
        os.chmod(DEST_BIN, 0o755)

if __name__ == "__main__":
    logging.info("=== INICIO GUADAMINT UPDATE ===")
    update_from_git()
    check_and_replace_backgrounds()
    logging.info("=== FIN GUADAMINT UPDATE ===")
