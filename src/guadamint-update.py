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
# Cambia a "testing" para pruebas, "main" para producción
REPO_BRANCH = "main" 

# Rutas de archivos (Origen en Repo -> Destino en Sistema)
SCRIPT_SRC_PATH = os.path.join(REPO_DIR, "src/guadamint-update.py")
SCRIPT_BIN_PATH = "/usr/bin/guadamint-update.py"

# LISTA DE APPS OBLIGATORIAS
APPS_OBLIGATORIAS = [
    # Utilidades sistema
    "zram-tools", "gnome-network-display", 
    
    # Suite Tux (Infantil/Primaria)
    "tuxtype", "tuxmath", "tuxpaint", 
    
    # Suite KDE-Edu (Lengua/Geografía)
    "kgeography", "kwordquiz", "klettres", "khangman", "kanagram", 
    
    # Ciencia y Lógica
    "stellarium", "kalzium", "step", "gbrainy", "marble",
    
    # Programación
    "scratch", "kturtle", "thonny", "minetest",
    
    # Multimedia y Creatividad
    "gcompris-qt", "audacity", "openboard",
    
    # Mecanografía formal
    "klavaro"
]

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
TRAY_PROCESS = None

# ==============================================================================
# FUNCIONES BÁSICAS
# ==============================================================================

def log_y_print(mensaje):
    """Escribe en log y terminal."""
    print(mensaje, flush=True)
    logging.info(mensaje)

def obtener_usuario_real():
    """Detecta quién es el usuario que inició la sesión gráfica."""
    return os.environ.get('SUDO_USER')

# ==============================================================================
# SISTEMA DE AUTO-ACTUALIZACIÓN (GIT)
# ==============================================================================

def auto_actualizar_desde_git():
    """
    Gestiona el clonado/actualización del repo y el reinicio del script si cambia.
    """
    log_y_print(f"--- Comprobando actualizaciones del repositorio (Rama: {REPO_BRANCH}) ---")
    se_requiere_reinicio = False

    # 1. Si no existe el directorio, clonamos de cero
    if not os.path.exists(REPO_DIR):
        log_y_print(f">>> Clonando repositorio en {REPO_DIR}...")
        try:
            subprocess.run(["git", "clone", "-b", REPO_BRANCH, REPO_URL, REPO_DIR], check=True)
            se_requiere_reinicio = True # Acabamos de instalar, seguro que es más nuevo
        except Exception as e:
            log_y_print(f"!!! Error al clonar: {e}")
            return 
    else:
        # 2. Si existe, comprobamos si hay cambios
        try:
            os.chdir(REPO_DIR)
            
            # Traemos info del remoto
            subprocess.run(["git", "fetch", "origin"], check=True, stderr=subprocess.DEVNULL)
            
            # Aseguramos estar en la rama correcta
            subprocess.run(["git", "checkout", REPO_BRANCH], check=True, stderr=subprocess.DEVNULL)
            
            # Comparamos hash local (HEAD) con remoto (origin/RAMA)
            local_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
            remote_hash = subprocess.check_output(["git", "rev-parse", f"origin/{REPO_BRANCH}"], text=True).strip()
            
            if local_hash != remote_hash:
                log_y_print(f">>> Actualización detectada ({local_hash[:7]} -> {remote_hash[:7]})")
                
                # Forzamos update limpio
                subprocess.run(["git", "reset", "--hard", f"origin/{REPO_BRANCH}"], check=True)
                
                se_requiere_reinicio = True
            else:
                log_y_print(">>> El script está actualizado.")
        
        except Exception as e:
            log_y_print(f"!!! Error al comprobar git: {e}")

    # 3. Si hubo cambios, copiamos el archivo y nos reiniciamos
    if se_requiere_reinicio:
        log_y_print(">>> Aplicando nueva versión del script...")
        try:
            if os.path.exists(SCRIPT_SRC_PATH):
                # Copiamos del repo (/opt) al sistema (/usr/bin)
                shutil.copy2(SCRIPT_SRC_PATH, SCRIPT_BIN_PATH)
                os.chmod(SCRIPT_BIN_PATH, 0o755)
                
                log_y_print(">>> REINICIANDO SCRIPT CON NUEVA VERSIÓN...")
                if TRAY_PROCESS: cerrar_tray_icon()
                
                # REINICIO MÁGICO
                os.execv(sys.executable, ['python3'] + sys.argv)
            else:
                log_y_print(f"!!! Error: No encuentro el archivo fuente en {SCRIPT_SRC_PATH}")
        except Exception as e:
            log_y_print(f"!!! Error crítico al auto-actualizarse: {e}")

# ==============================================================================
# FUNCIONES DE ICONO Y ENTORNO
# ==============================================================================

def obtener_entorno_usuario(usuario):
    """Recupera variables de entorno (DISPLAY, DBUS) del proceso de sesión."""
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
    icono_inicial = ICONO_DEFECTO if os.path.exists(ICONO_DEFECTO) else "system-software-update"

    cmd = ['sudo', '-u', usuario, 'zenity', '--notification', '--listen', f'--window-icon={icono_inicial}']
    try:
        TRAY_PROCESS = subprocess.Popen(cmd, env=entorno, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        actualizar_tray('inicio', "GuadaMint: Iniciando...")
    except: pass

def actualizar_tray(estado, mensaje=""):
    """Envía comandos al icono de la bandeja."""
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
        # message: fuerza la burbuja de notificación
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
    """Muestra una ventana Zenity (popup)."""
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
    """Ejecuta comandos apt (root directo porque el script es root)."""
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
    """Comprueba apps obligatorias e instala si faltan."""
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
        # 1. AUTO-UPDATE GIT
        auto_actualizar_desde_git()

        # 2. LÓGICA PRINCIPAL
        escritorio = detectar_escritorio()
        log_y_print(f">>> Escritorio: {escritorio}")
        
        verificar_e_instalar_apps()
        
        # 3. Lógica Futura (Condicionales)
        if escritorio == "XFCE": pass
        elif escritorio == "CINNAMON": pass

        # 4. Finalización
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
