#!/usr/bin/env python3
import subprocess
import logging
import os
import sys
import time
import shutil
import random
import filecmp

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
LOG_FILE = "/var/log/guadamint/actualizador.log"
LOCK_FILE = "/tmp/guadamint-updating.lock"
ICONO_DEFECTO = "/usr/share/icons/guadamintuz.svg"

# --- CONFIGURACIÓN GIT ---
REPO_URL = "https://github.com/aosucas499/guadamint.git"
REPO_DIR = "/opt/guadamint"
REPO_BRANCH = "main" 

# --- ARCHIVOS QUE SE DEBEN ACTUALIZAR DESDE GITHUB ---
# Mapeo: Dónde está en el repo -> Dónde va en el sistema
ARCHIVOS_A_SINCRONIZAR = [
    {
        "origen": "src/guadamint-update.py", 
        "destino": "/usr/bin/guadamint-update.py"
    },
    {
        "origen": "src/apps-guadamint.py",   
        "destino": "/usr/bin/apps-guadamint.py"
    }
]

# El script actual (para saber si nos hemos actualizado a nosotros mismos y reiniciar)
SCRIPT_BIN_PATH = "/usr/bin/guadamint-update.py"

# LISTA DE APPS OBLIGATORIAS (Mantenimiento)
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
# SISTEMA DE AUTO-ACTUALIZACIÓN (GIT MULTI-ARCHIVO)
# ==============================================================================

def auto_actualizar_desde_git():
    log_y_print(f"--- Comprobando actualizaciones del repositorio (Rama: {REPO_BRANCH}) ---")
    
    hay_cambios_git = False
    
    # 1. Clonar o Actualizar el Repositorio en /opt
    if not os.path.exists(REPO_DIR):
        log_y_print(f">>> Clonando repositorio en {REPO_DIR}...")
        try:
            subprocess.run(["git", "clone", "-b", REPO_BRANCH, REPO_URL, REPO_DIR], check=True)
            hay_cambios_git = True
        except Exception as e:
            log_y_print(f"!!! Error al clonar: {e}")
            return 
    else:
        try:
            os.chdir(REPO_DIR)
            subprocess.run(["git", "fetch", "origin"], check=True, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "checkout", REPO_BRANCH], check=True, stderr=subprocess.DEVNULL)
            
            local_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
            remote_hash = subprocess.check_output(["git", "rev-parse", f"origin/{REPO_BRANCH}"], text=True).strip()
            
            if local_hash != remote_hash:
                log_y_print(f">>> Git: Actualización detectada ({local_hash[:7]} -> {remote_hash[:7]})")
                subprocess.run(["git", "reset", "--hard", f"origin/{REPO_BRANCH}"], check=True)
                hay_cambios_git = True
            else:
                log_y_print(">>> Git: El repositorio está al día.")
        except Exception as e:
            log_y_print(f"!!! Error git: {e}")

    # 2. Sincronizar archivos al sistema (Si hubo cambios en git o si faltan/son distintos)
    # Recorremos la lista de archivos (actualizador y tienda)
    se_requiere_reinicio = False
    
    for item in ARCHIVOS_A_SINCRONIZAR:
        ruta_origen = os.path.join(REPO_DIR, item["origen"])
        ruta_destino = item["destino"]
        
        try:
            if os.path.exists(ruta_origen):
                # Comprobamos si hay que actualizar (si son distintos o destino no existe)
                # O si hubo cambios en git, forzamos la copia por seguridad
                if hay_cambios_git or not os.path.exists(ruta_destino) or \
                   not filecmp.cmp(ruta_origen, ruta_destino, shallow=False):
                    
                    log_y_print(f">>> Actualizando archivo: {os.path.basename(ruta_destino)}")
                    shutil.copy2(ruta_origen, ruta_destino)
                    os.chmod(ruta_destino, 0o755)
                    
                    # Si hemos actualizado ESTE mismo script, necesitamos reiniciar
                    if ruta_destino == SCRIPT_BIN_PATH:
                        se_requiere_reinicio = True
            else:
                log_y_print(f"!!! Aviso: Archivo fuente no encontrado en repo: {item['origen']}")
        except Exception as e:
            log_y_print(f"!!! Error sincronizando {ruta_destino}: {e}")

    # 3. Reiniciar si el propio script cambió
    if se_requiere_reinicio:
        log_y_print(">>> EL ACTUALIZADOR SE HA ACTUALIZADO. REINICIANDO PROCESO...")
        try:
            if TRAY_PROCESS: cerrar_tray_icon()
            time.sleep(1)
            os.execv(sys.executable, ['python3'] + sys.argv)
        except Exception as e:
            log_y_print(f"!!! Error crítico reinicio: {e}")

# ==============================================================================
# FUNCIONES DE INTERFAZ Y SISTEMA
# ==============================================================================
# ... (El resto de funciones se mantienen idénticas) ...

def obtener_entorno_usuario(usuario):
    env_vars = {'DISPLAY': ':0'}
    try:
        pids = subprocess.check_output(["pgrep", "-u", usuario, "-f", "session"], text=True).split()
        for pid in pids:
            try:
                with open(f"/proc/{pid}/environ", "rb") as f: content = f.read().decode("utf-8", errors="ignore")
                for item in content.split('\0'):
                    if item.startswith("DBUS") or item.startswith("DISPLAY"):
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
    iconos = {'inicio': ICONO_DEFECTO if os.path.exists(ICONO_DEFECTO) else 'preferences-system', 'trabajando': 'system-software-install', 'ok': 'security-high', 'error': 'dialog-error'}
    try:
        if mensaje: TRAY_PROCESS.stdin.write(f"message: {mensaje}\n")
        TRAY_PROCESS.stdin.write(f"icon: {iconos.get(estado, 'info')}\n")
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
    if os.path.exists("/usr/bin/xfce4-session"): return "XFCE"
    return "DESCONOCIDO"

def ejecutar_comando(comando, visible=False):
    try:
        env = os.environ.copy(); env['DEBIAN_FRONTEND'] = 'noninteractive'
        if visible: subprocess.run(comando, text=True, env=env, check=True)
        else: subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, check=True)
        log_y_print(f"OK: {' '.join(comando)}")
        return True
    except: return False

def verificar_crear_usuario_alumno():
    try: subprocess.run(["id", "-u", "usuario"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        log_y_print(">>> Creando usuario 'usuario'...")
        try:
            subprocess.run(["useradd", "-m", "-s", "/bin/bash", "-c", "Usuario", "-U", "usuario"], check=True)
            proc = subprocess.Popen(["chpasswd"], stdin=subprocess.PIPE, text=True)
            proc.communicate(input="usuario:usuario")
        except: pass

def ocultar_lista_usuarios_login():
    try:
        if not os.path.exists("/etc/lightdm/lightdm.conf.d"): os.makedirs("/etc/lightdm/lightdm.conf.d")
        with open("/etc/lightdm/lightdm.conf.d/99-guadamint-privacy.conf", 'w') as f:
            f.write("[Seat:*]\ngreeter-hide-users=true\nallow-guest=false\n")
    except: pass

def verificar_e_instalar_apps():
    faltantes = [app for app in APPS_OBLIGATORIAS if subprocess.run(["dpkg", "-s", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0]
    if faltantes:
        log_y_print(f">>> Faltan {len(faltantes)} apps.")
        actualizar_tray('trabajando', f"Instalando {len(faltantes)} apps...")
        mostrar_aviso("Mantenimiento", f"Instalando apps faltantes:\n{', '.join(faltantes)}")
        ejecutar_comando(['apt-get', 'update'], visible=True)
        if ejecutar_comando(['apt-get', 'install', '-y'] + faltantes, visible=True):
            actualizar_tray('ok', "Software actualizado")
        else: actualizar_tray('error', "Error al instalar")
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
        # 1. AUTO-UPDATE (Ahora incluye la tienda)
        auto_actualizar_desde_git()
        
        escritorio = detectar_escritorio()
        log_y_print(f">>> Escritorio: {escritorio}")
        
        # Mantenimiento
        verificar_crear_usuario_alumno()
        ocultar_lista_usuarios_login()
        verificar_e_instalar_apps()
        
        if escritorio == "XFCE": pass
        elif escritorio == "CINNAMON": pass
        
        time.sleep(random.randint(5, 10))
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
