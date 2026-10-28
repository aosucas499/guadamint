#!/usr/bin/env python3
import os
import shutil
import subprocess
import logging
import sys
import filecmp

# ==============================================================================
# 1. LOGS Y CONFIGURACIÓN BASE
# ==============================================================================
LOG_FILE = "/var/log/guadamint/update.log"
os.makedirs("/var/log/guadamint", exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

INSTALL_DIR = "/opt/guadamint"
REPO_URL = "https://github.com/aosucas499/guadamint.git"  # <-- URL actualizada
BRANCH = "eos"
SCRIPT_BIN_PATH = "/usr/bin/guadamint-update.py"

# ==============================================================================
# 2. LISTA DE ARCHIVOS A SINCRONIZAR EN EL SISTEMA
# ==============================================================================
ARCHIVOS_A_SINCRONIZAR = [
    # Actualizador principal y Tienda
    ("src/guadamint-update.py", "/usr/bin/guadamint-update.py", 0o755),
    ("src/apps-guadamint.py", "/usr/bin/apps-guadamint.py", 0o755),
    
    # Sudoers y Lanzadores
    ("src/zz-guadamint-update", "/etc/sudoers.d/zz-guadamint-update", 0o440),
    ("src/guadamint-update.desktop", "/etc/xdg/autostart/guadamint-update.desktop", 0o644),
    ("src/apps-guadamint.desktop", "/usr/share/applications/apps-guadamint.desktop", 0o644),
    
    # Conmutador / Toggle de actualizaciones
    ("src/guadamint-toggle-updates.py", "/usr/bin/guadamint-toggle-updates.py", 0o755),
    ("src/zz-guadamint-toggle-updates", "/etc/sudoers.d/zz-guadamint-toggle-updates", 0o440),
    ("src/guadamint-autoupdate-switch.desktop", "/etc/xdg/autostart/guadamint-autoupdate-switch.desktop", 0o644),
]

# Configuración de imágenes para sustitución por du -k
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

# ==============================================================================
# 3. FUNCIONES DE DESPLIEGUE Y FONDOS
# ==============================================================================
def get_disk_usage_kb(file_path):
    try:
        output = subprocess.check_output(["du", "-k", file_path]).decode().split()
        return int(output[0])
    except Exception:
        return os.path.getsize(file_path) // 1024

def check_and_replace_backgrounds():
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
                    logging.error(f"Error procesando fondo {target_path}: {error}")

def desplegar_actualizaciones():
    """Copia cada archivo actualizado desde /opt/guadamint a su ubicación real en el sistema."""
    logging.info("Sincronizando archivos del repositorio hacia las rutas del sistema...")
    se_requiere_reinicio = False

    for rel_src, abs_dest, mode in ARCHIVOS_A_SINCRONIZAR:
        src_path = os.path.join(INSTALL_DIR, rel_src)
        
        if os.path.isfile(src_path):
            try:
                os.makedirs(os.path.dirname(abs_dest), exist_ok=True)
                
                # Comprobar si difieren antes de copiar
                diferente = not os.path.exists(abs_dest) or not filecmp.cmp(src_path, abs_dest, shallow=False)
                
                if diferente:
                    shutil.copy2(src_path, abs_dest)
                    os.chmod(abs_dest, mode)
                    
                    if "/etc/sudoers.d/" in abs_dest:
                        shutil.chown(abs_dest, user="root", group="root")
                        
                    logging.info(f"Actualizado: {src_path} -> {abs_dest} (permisos: {oct(mode)})")
                    
                    if abs_dest == SCRIPT_BIN_PATH:
                        se_requiere_reinicio = True
            except Exception as e:
                logging.error(f"Error al copiar {src_path} a {abs_dest}: {e}")
        else:
            logging.warning(f"Archivo omitido (no existe en repo): {src_path}")

    return se_requiere_reinicio

def update_from_git():
    """Actualiza /opt/guadamint vía Git y ejecuta el despliegue de archivos."""
    git_dir = os.path.join(INSTALL_DIR, ".git")

    # Si la carpeta no existe O si existe pero NO tiene la carpeta .git (copia local de la ISO)
    if not os.path.exists(INSTALL_DIR) or not os.path.exists(git_dir):
        logging.info(f"Carpeta {INSTALL_DIR} no válida o sin .git. Limpiando y clonando de cero...")
        
        # 1. Eliminamos el directorio de forma radical para evitar el error de 'directorio no vacío'
        if os.path.exists(INSTALL_DIR):
            shutil.rmtree(INSTALL_DIR)
            
        # 2. Clonamos limpiamente la rama objetivo desde GitHub
        subprocess.run(["git", "clone", "-b", BRANCH, REPO_URL, INSTALL_DIR], check=False)
    else:
        logging.info("Sincronizando repositorio Git existente...")
        subprocess.run(["git", "-C", INSTALL_DIR, "fetch", "origin"], check=False)
        subprocess.run(["git", "-C", INSTALL_DIR, "reset", "--hard", f"origin/{BRANCH}"], check=False)

    # Tras actualizar el repositorio local, desplegamos los cambios al sistema
    se_requiere_reinicio = desplegar_actualizaciones()

    # Si se actualizó a sí mismo y no estamos ya en un subproceso reiniciado:
    if se_requiere_reinicio and '--restarted' not in sys.argv:
        logging.info("Reejecutando script con el nuevo código...")
        os.execv(sys.executable, [sys.executable, SCRIPT_BIN_PATH, '--restarted'])

# ==============================================================================
# 4. EJECUCIÓN PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    if os.geteuid() != 0:
        logging.error("El script debe ejecutarse como root/sudo.")
        sys.exit(1)

    logging.info("=== INICIO GUADAMINT UPDATE ===")
    update_from_git()
    check_and_replace_backgrounds()
    logging.info("=== FIN GUADAMINT UPDATE ===")
