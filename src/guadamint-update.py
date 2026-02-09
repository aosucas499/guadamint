#!/usr/bin/env python3
import subprocess
import logging
import os
import sys
import time
import shutil
import random

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
LOG_FILE = "/var/log/guadamint/actualizador.log"
LOCK_FILE = "/tmp/guadamint-updating.lock"
ICONO_DEFECTO = "/usr/share/icons/guadamintuz.svg"

# --- CONFIGURACIÓN GIT ---
REPO_URL = "https://github.com/aosucas499/guadalinex.git"
REPO_DIR = "/opt/guadamint"
REPO_BRANCH = "main" 

# Rutas de archivos
SCRIPT_SRC_PATH = os.path.join(REPO_DIR, "src/guadamint-update.py")
SCRIPT_BIN_PATH = "/usr/bin/guadamint-update.py"

# LISTA DE APPS OBLIGATORIAS
# Corregido: 'gnome-network-displays' (en plural)
APPS_OBLIGATORIAS = [
    "zram-tools", "gnome-network-displays", 
    "tuxtype", "tuxmath", "tuxpaint", 
    "kgeography", "kwordquiz", "klettres", "khangman", "kanagram", 
    "stellarium", "kalzium", "step", "gbrainy", "marble",
    "scratch", "kturtle", "thonny", "minetest",
    "gcompris-qt", "audacity", "openboard", "klavaro"
]

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
TRAY_PROCESS = None

# ==============================================================================
# FUNCIONES BÁSICAS
# ==============================================================================

def log_y_print(mensaje):
    print(mensaje, flush=True)
    logging.info(mensaje)

def obtener_usuario_real():
    return os.environ.get('SUDO_USER')

# ==============================================================================
# SISTEMA DE AUTO-ACTUALIZACIÓN (GIT)
# ==============================================================================

def auto_actualizar_desde_git():
    log_y_print(f"--- Comprobando actualizaciones del repositorio (Rama: {REPO_BRANCH}) ---")
    se_requiere_reinicio = False

    # 1. Clonar si no existe
    if not os.path.exists(REPO_DIR):
        log_y_print(f">>> Clonando repositorio en {REPO_DIR}...")
        try:
            subprocess.run(["git", "clone", "-b", REPO_BRANCH, REPO_URL, REPO_DIR], check=True)
            # Solo pedimos reinicio SI el archivo realmente existe en lo que acabamos de bajar
            if os.path.exists(SCRIPT_SRC_PATH):
                se_requiere_reinicio = True 
            else:
                log_y_print(">>> Repositorio clonado, pero el script no está en el origen. Se usará la versión local.")
        except Exception as e:
            log_y_print(f"!!! Error al clonar: {e}")
            return 
    else:
        # 2. Actualizar si existe
        try:
            os.chdir(REPO_DIR)
            subprocess.run(["git", "fetch", "origin"], check=True, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "checkout", REPO_BRANCH], check=True, stderr=subprocess.DEVNULL)
            
            local_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
            remote_hash = subprocess.check_output(["git", "rev-parse", f"origin/{REPO_BRANCH}"], text=True).strip()
            
            if local_hash != remote_hash:
                log_y_print(f">>> Actualización detectada ({local_hash[:7]} -> {remote_hash[:7]})")
                subprocess.run(["git", "reset", "--hard", f"origin/{REPO_BRANCH}"], check=True)
                
                # Solo marcamos para reinicio si el script existe en el repo
                if os.path.exists(SCRIPT_SRC_PATH):
                    se_requiere_reinicio = True
            else:
                log_y_print(">>> El script está actualizado.")
        except Exception as e:
            log_y_print(f"!!! Error git: {e}")

    # 3. Aplicar cambios
    if se_requiere_reinicio:
        log_y_print(">>> Aplicando nueva versión...")
        try:
            shutil.copy2(SCRIPT_SRC_PATH, SCRIPT_BIN_PATH)
            os.chmod(SCRIPT_BIN_PATH, 0o755)
            
            if TRAY_PROCESS: cerrar_tray_icon()
            
            log_y_print(">>> REINICIANDO PROCESO...")
            os.execv(sys.executable, ['python3'] + sys.argv)
        except Exception as e:
            log_y_print(f"!!! Error al actualizarse a sí mismo: {e}")

# ==============================================================================
# FUNCIONES DE INTERFAZ
# ==============================================================================

def obtener_entorno_usuario(usuario):
    env_vars = {'DISPLAY': ':0'}
    try:
        pids = subprocess.check_output(["pgrep", "-u", usuario, "-f", "session"], text=True).split()
        for pid in pids:
            try:
                with open(f"/proc/{pid}/environ", "rb") as f:
                    contenido = f.read().decode("utf-8", errors="ignore")
                for item in contenido.split('\0'):
                    if item.startswith("DBUS_SESSION_BUS_ADDRESS="):
                        env_vars['DBUS_SESSION_BUS_ADDRESS'] = item.split("=", 1)[1]
                    elif item.startswith("DISPLAY="):
                        env_vars['DISPLAY'] = item.split("=", 1)[1]
                if 'DBUS_SESSION_BUS_ADDRESS' in env_vars: break
            except: continue
    except: pass
    return env_vars

def iniciar_tray_icon():
    global TRAY_PROCESS
    usuario = obtener_usuario_real()
    if not usuario: return
    entorno = os.environ.copy()
    entorno.update(obtener_entorno_usuario(usuario))
    
    icono = ICONO_DEFECTO if os.path.exists(ICONO_DEFECTO) else "system-software-update"
    cmd = ['sudo', '-u', usuario, 'zenity', '--notification', '--listen', f'--window-icon={icono}']
    
    try:
        TRAY_PROCESS = subprocess.Popen(cmd, env=entorno, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        actualizar_tray('inicio', "GuadaMint Iniciando...")
    except: pass

def actualizar_tray(estado, mensaje=""):
    global TRAY_PROCESS
    if not TRAY_PROCESS or TRAY_PROCESS.poll() is not None: return
    
    iconos = {
        'inicio': ICONO_DEFECTO if os.path.exists(ICONO_DEFECTO) else 'preferences-system',
        'trabajando': 'system-software-install',
        'ok': 'security-high',
        'error': 'dialog-error'
    }
    icono = iconos.get(estado, 'info')
    
    try:
        if mensaje: TRAY_PROCESS.stdin.write(f"message: {mensaje}\n")
        TRAY_PROCESS.stdin.write(f"icon: {icono}\n")
        TRAY_PROCESS.stdin.flush()
    except: pass

def cerrar_tray_icon():
    global TRAY_PROCESS
    if TRAY_PROCESS:
        try: TRAY_PROCESS.terminate(); TRAY_PROCESS = None
        except: pass

def mostrar_aviso(titulo, mensaje, icono="info"):
    usuario = obtener_usuario_real()
    if not usuario: return
    entorno = os.environ.copy()
    entorno.update(obtener_entorno_usuario(usuario))
    cmd = ['sudo', '-u', usuario, 'zenity', '--info', '--title', titulo, '--text', mensaje, '--width=400', '--timeout=10', f'--window-icon={icono}']
    try: subprocess.Popen(cmd, env=entorno, stderr=subprocess.DEVNULL)
    except: pass

def detectar_escritorio():
    if os.path.exists("/usr/bin/cinnamon-session"): return "CINNAMON"
    elif os.path.exists("/usr/bin/xfce4-session"): return "XFCE"
    return "DESCONOCIDO"

def ejecutar_comando(comando, visible=False):
    try:
        env = os.environ.copy()
        env['DEBIAN_FRONTEND'] = 'noninteractive'
        if visible: subprocess.run(comando, text=True, env=env, check=True)
        else: subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, check=True)
        log_y_print(f"OK: {' '.join(comando)}")
        return True
    except subprocess.CalledProcessError as e:
        log_y_print(f"ERROR: {' '.join(comando)}")
        return False

def verificar_e_instalar_apps():
    faltantes = []
    actualizar_tray('inicio', "Verificando software educativo...")
    
    for app in APPS_OBLIGATORIAS:
        res = subprocess.run(["dpkg", "-s", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0: faltantes.append(app)
    
    if len(faltantes) > 0:
        log_y_print(f">>> Faltan {len(faltantes)} apps.")
        actualizar_tray('trabajando', f"Instalando {len(faltantes)} aplicaciones...")
        mostrar_aviso("Mantenimiento", f"Instalando apps faltantes:\n{', '.join(faltantes)}")
        
        ejecutar_comando(['apt-get', 'update'], visible=True)
        if ejecutar_comando(['apt-get', 'install', '-y'] + faltantes, visible=True):
            actualizar_tray('ok', "Software actualizado correctamente")
        else:
            actualizar_tray('error', "Error al instalar software")
    else:
        log_y_print(">>> Todo en orden.")
        actualizar_tray('ok', "Sistema actualizado y listo")

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    if os.geteuid() != 0:
        print("!!! ERROR: Debes ejecutar este script como ROOT (sudo).")
        sys.exit(1)

    log_y_print("=== INICIO SERVICIO GUADAMINT ===")
    
    iniciar_tray_icon()
    try:
        auto_actualizar_desde_git()

        escritorio = detectar_escritorio()
        log_y_print(f">>> Escritorio: {escritorio}")
        
        verificar_e_instalar_apps()
        
        if escritorio == "XFCE": pass
        elif escritorio == "CINNAMON": pass

        wait = random.randint(5, 10)
        time.sleep(wait)
        
        try:
            with open(LOCK_FILE, 'w') as f: f.write("running")
        except: pass
        if os.path.exists(LOCK_FILE):
            try: os.remove(LOCK_FILE)
            except: pass

    finally:
        cerrar_tray_icon()
    
    log_y_print("=== FIN ===")

if __name__ == "__main__":
    main()
