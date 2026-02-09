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
# URL CORREGIDA: Apunta al repositorio 'guadamint'
REPO_URL = "https://github.com/aosucas499/guadamint.git"
REPO_DIR = "/opt/guadamint"
REPO_BRANCH = "main" 

# Rutas de archivos
SCRIPT_SRC_PATH = os.path.join(REPO_DIR, "src/guadamint-update.py")
SCRIPT_BIN_PATH = "/usr/bin/guadamint-update.py"

# LISTA DE APPS OBLIGATORIAS
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
        log_y_print(f">>> Directorio {REPO_DIR} no existe. Clonando...")
        try:
            # Clonado inicial con la URL correcta
            subprocess.run(["git", "clone", "-b", REPO_BRANCH, REPO_URL, REPO_DIR], check=True)
            
            if os.path.exists(SCRIPT_SRC_PATH):
                se_requiere_reinicio = True 
            else:
                log_y_print(f"!!! ALERTA: Repositorio clonado, pero NO SE ENCUENTRA: {SCRIPT_SRC_PATH}")
                log_y_print("!!! Verifica que la estructura de carpetas en GitHub es 'guadamint/src/guadamint-update.py'")
        except Exception as e:
            log_y_print(f"!!! Error al clonar: {e}")
            return 
    else:
        # 2. Actualizar si existe
        try:
            os.chdir(REPO_DIR)
            log_y_print(f">>> Sincronizando {REPO_DIR} con GitHub...")
            
            # Traemos cambios
            subprocess.run(["git", "fetch", "origin"], check=True)
            subprocess.run(["git", "checkout", REPO_BRANCH], check=True, stderr=subprocess.DEVNULL)
            
            # Comparamos Hashes para ver si hay cambios reales
            local_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
            remote_hash = subprocess.check_output(["git", "rev-parse", f"origin/{REPO_BRANCH}"], text=True).strip()
            
            log_y_print(f"   > Local (PC):  {local_hash[:7]}")
            log_y_print(f"   > Remoto (Web): {remote_hash[:7]}")

            if local_hash != remote_hash:
                log_y_print(f">>> ¡ACTUALIZACIÓN DETECTADA! Aplicando cambios...")
                subprocess.run(["git", "reset", "--hard", f"origin/{REPO_BRANCH}"], check=True)
                
                if os.path.exists(SCRIPT_SRC_PATH):
                    se_requiere_reinicio = True
                else:
                    log_y_print(f"!!! PELIGRO: Git actualizado, pero el archivo fuente ha desaparecido.")
            else:
                log_y_print(">>> El script está actualizado (Hashes coinciden).")
        except Exception as e:
            log_y_print(f"!!! Error git: {e}")

    # 3. Reinicio
    if se_requiere_reinicio:
        log_y_print(">>> ---------------------------------------------------")
        log_y_print(">>> ACTUALIZACIÓN EN CURSO: Reemplazando script local...")
        try:
            shutil.copy2(SCRIPT_SRC_PATH, SCRIPT_BIN_PATH)
            os.chmod(SCRIPT_BIN_PATH, 0o755)
            
            if TRAY_PROCESS: cerrar_tray_icon()
            
            log_y_print(">>> ¡ÉXITO! Reiniciando proceso en 3 segundos...")
            time.sleep(3)
            
            os.execv(sys.executable, ['python3'] + sys.argv)
        except Exception as e:
            log_y_print(f"!!! Error crítico update: {e}")

# ==============================================================================
# FUNCIONES AUXILIARES (Icono, Apps, etc)
# ==============================================================================

def obtener_entorno_usuario(usuario):
    env_vars = {'DISPLAY': ':0'}
    try:
        pids = subprocess.check_output(["pgrep", "-u", usuario, "-f", "session"], text=True).split()
        for pid in pids:
            try:
                with open(f"/proc/{pid}/environ", "rb") as f:
                    content = f.read().decode("utf-8", errors="ignore")
                for item in content.split('\0'):
                    if item.startswith("DBUS_SESSION_BUS_ADDRESS=") or item.startswith("DISPLAY="):
                        k, v = item.split("=", 1)
                        env_vars[k] = v
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
    try:
        TRAY_PROCESS = subprocess.Popen(['sudo', '-u', usuario, 'zenity', '--notification', '--listen', f'--window-icon={icono}'],
                                      env=entorno, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        actualizar_tray('inicio', "GuadaMint Iniciando...")
    except: pass

def actualizar_tray(estado, mensaje=""):
    global TRAY_PROCESS
    if not TRAY_PROCESS or TRAY_PROCESS.poll() is not None: return
    iconos = {'inicio': 'preferences-system', 'trabajando': 'system-software-install', 'ok': 'security-high', 'error': 'dialog-error'}
    
    # Si es estado inicial y tenemos icono personalizado, usémoslo
    if estado == 'inicio' and os.path.exists(ICONO_DEFECTO): 
        icono_nom = ICONO_DEFECTO
    else: 
        icono_nom = iconos.get(estado, 'info')
        
    try:
        if mensaje: TRAY_PROCESS.stdin.write(f"message: {mensaje}\n")
        TRAY_PROCESS.stdin.write(f"icon: {icono_nom}\n")
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
    try: subprocess.Popen(['sudo', '-u', usuario, 'zenity', '--info', '--title', titulo, '--text', mensaje, '--width=400', '--timeout=10', f'--window-icon={icono}'], env=entorno, stderr=subprocess.DEVNULL)
    except: pass

def detectar_escritorio():
    if os.path.exists("/usr/bin/cinnamon-session"): return "CINNAMON"
    elif os.path.exists("/usr/bin/xfce4-session"): return "XFCE"
    return "DESCONOCIDO"

def ejecutar_comando(comando, visible=False):
    try:
        env = os.environ.copy(); env['DEBIAN_FRONTEND'] = 'noninteractive'
        if visible: subprocess.run(comando, text=True, env=env, check=True)
        else: subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, check=True)
        log_y_print(f"OK: {' '.join(comando)}")
        return True
    except:
        log_y_print(f"ERROR: {' '.join(comando)}")
        return False

def verificar_e_instalar_apps():
    faltantes = []
    actualizar_tray('inicio', "Verificando software...")
    for app in APPS_OBLIGATORIAS:
        if subprocess.run(["dpkg", "-s", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
            faltantes.append(app)
    if faltantes:
        log_y_print(f">>> Faltan {len(faltantes)} apps.")
        actualizar_tray('trabajando', f"Instalando {len(faltantes)} apps...")
        mostrar_aviso("Mantenimiento", f"Instalando apps faltantes:\n{', '.join(faltantes)}")
        ejecutar_comando(['apt-get', 'update'], visible=True)
        if ejecutar_comando(['apt-get', 'install', '-y'] + faltantes, visible=True):
            actualizar_tray('ok', "Software actualizado")
        else:
            actualizar_tray('error', "Error al instalar")
    else:
        log_y_print(">>> Todo en orden.")
        actualizar_tray('ok', "Sistema listo")

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    if os.geteuid() != 0: sys.exit(1)
    
    iniciar_tray_icon()
    try:
        # 1. AUTO UPDATE
        auto_actualizar_desde_git()

        # 2. RESTO DE LÓGICA
        escritorio = detectar_escritorio()
        log_y_print(f">>> Escritorio: {escritorio}")
        verificar_e_instalar_apps()
        
        # 3. ESPERA Y CIERRE
        wait_time = random.randint(5, 10)
        time.sleep(wait_time)
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
