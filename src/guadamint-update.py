#!/usr/bin/env python3
import os
import shutil
import subprocess

#################################################
# 1. CONFIGURACIÓN DE IMÁGENES (Valores de du -k)
#################################################
BACKGROUNDS_CONFIG = {
    "EducaAndOSv2-background.png": {
        "du_kb": 16428,
        "source": "/opt/guadamint/images/EducaAndOSv2-background.png"
    },
    "EducaAndOSv2-background-dark.png": {
        "du_kb": 2012,
        "source": "/opt/guadamint/images/EducaAndOSv2-background-dark.png"
    },
    "EducaAndOSv2-login.png": {
        "du_kb": 1532,
        "source": "/opt/guadamint/images/EducaAndOSv2-login.png"
    }
}

TARGET_DIRECTORIES = [
    "/usr/share/backgrounds",
    "/usr/share/sar-artwork"
]

def check_and_replace_backgrounds():
    """Comprueba el peso du -k de cada imagen original y la sustituye si coincide."""
    for directory in TARGET_DIRECTORIES:
        if not os.path.isdir(directory):
            continue

        for filename, info in BACKGROUNDS_CONFIG.items():
            target_path = os.path.join(directory, filename)
            source_path = info["source"]

            if os.path.isfile(target_path) and os.path.isfile(source_path):
                try:
                    current_du_kb = os.path.getsize(target_path) // 1024

                    if current_du_kb == info["du_kb"]:
                        shutil.copy2(source_path, target_path)
                        os.chmod(target_path, 0o644)
                        print(f"[GuadaMint] Fondo reemplazado: {target_path}")
                except Exception as error:
                    print(f"[GuadaMint] Error al procesar {target_path}: {error}")

#################################################
# 2. BLOQUE PRINCIPAL DE EJECUCIÓN
#################################################
if __name__ == "__main__":
    # Primero: Verifica y reemplaza las imágenes si son las originales
    check_and_replace_backgrounds()
    
    # Segundo: Aquí continúa tu código habitual (git pull, setup.sh, etc.)

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
REPO_BRANCH = "eos" 

import os
import shutil
import subprocess

REPO_DIR = "/opt/guadamint/repo"  # O la ruta donde clonas tu repositorio local/git

# Lista de archivos a sincronizar automáticamente en cada actualización de Git
ARCHIVOS_A_SINCRONIZAR = [
    # Actualizador principal y Tienda
    ("src/guadamint-update.py", "/usr/bin/guadamint-update.py", 0o755),
    ("src/apps-guadamint.py", "/usr/bin/apps-guadamint.py", 0o755),
    ("src/zz-guadamint-update", "/etc/sudoers.d/zz-guadamint-update", 0o440),
    ("src/guadamint-update.desktop", "/etc/xdg/autostart/guadamint-update.desktop", 0o644),
    ("src/apps-guadamint.desktop", "/usr/share/applications/apps-guadamint.desktop", 0o644),

    # --- CONMUTADOR (TOGGLE) ---
    ("src/guadamint-toggle-updates.py", "/usr/bin/guadamint-toggle-updates.py", 0o755),
    ("src/zz-guadamint-toggle-updates", "/etc/sudoers.d/zz-guadamint-toggle-updates", 0o440),
    # CORREGIDO: Usamos el nombre real del archivo en src/
    ("src/guadamint-autoupdate-switch.desktop", "/etc/xdg/autostart/guadamint-autoupdate-switch.desktop", 0o644),
]

def desplegar_actualizaciones():
    """Copia los archivos del repositorio Git a sus destinos en el sistema."""
    for origen_rel, destino_abs, permisos in ARCHIVOS_A_SINCRONIZAR:
        origen_abs = os.path.join(REPO_DIR, origen_rel)
        if os.path.exists(origen_abs):
            try:
                # Copiar archivo preservando metadatos
                shutil.copy2(origen_abs, destino_abs)
                os.chmod(destino_abs, permisos)
                
                # Regla de seguridad obligatoria de Linux: los archivos en sudoers.d DEBEN pertenecer a root:root
                if "/etc/sudoers.d/" in destino_abs:
                    shutil.chown(destino_abs, user="root", group="root")
                    
                print(f"[OK] Sincronizado: {origen_rel} -> {destino_abs}")
            except Exception as e:
                print(f"[ERROR] No se pudo copiar {origen_rel} a {destino_abs}: {e}")

SCRIPT_BIN_PATH = "/usr/bin/guadamint-update.py"

# LISTA DE HERRAMIENTAS BASE OBLIGATORIAS
APPS_OBLIGATORIAS = [
    "git",
    "gir1.2-appindicator3-0.1",
    "gir1.2-gtk-3.0",
    "dbus-x11"
]

# Crear directorio de logs si no existe
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
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
    mensaje_git = ""
    es_reinicio = '--restarted' in sys.argv
    
    # 1. Clonar o Actualizar el Repositorio en /opt
    if not os.path.exists(REPO_DIR):
        log_y_print(f">>> Clonando repositorio en {REPO_DIR}...")
        try:
            subprocess.run(["git", "clone", "-b", REPO_BRANCH, REPO_URL, REPO_DIR], check=True)
            hay_cambios_git = True
            mensaje_git = "Se ha descargado el sistema base por primera vez."
        except Exception as e:
            log_y_print(f"!!! Error al clonar: {e}")
            mostrar_aviso("Error de Red", "No se pudo conectar con GitHub.", "error")
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
                
                try:
                    resumen_completo = subprocess.check_output(["git", "log", "--pretty=format:• %s", f"{local_hash}..{remote_hash}"], text=True).strip()
                    lineas = resumen_completo.split('\n')
                    if len(lineas) > 3:
                        resumen = '\n'.join(lineas[:3]) + '\n... y más cambios.'
                    else:
                        resumen = resumen_completo
                except:
                    resumen = "Nuevos archivos sincronizados."
                    
                subprocess.run(["git", "reset", "--hard", f"origin/{REPO_BRANCH}"], check=True)
                hay_cambios_git = True
                mensaje_git = f"{resumen}"
            else:
                log_y_print(">>> Git: El repositorio está al día.")
        except Exception as e:
            log_y_print(f"!!! Error git: {e}")
            mostrar_aviso("Error", "Fallo al comprobar actualizaciones.", "error")
            return

    # --- AVISO GRÁFICO (NOTIFICACIÓN DE ESCRITORIO NO INVASIVA) ---
    if hay_cambios_git:
        mostrar_aviso("GuadaMint Actualizado", mensaje_git)
    elif not es_reinicio:
        mostrar_aviso("Sistema al día", "No hay actualizaciones nuevas.")

    # 2. Sincronizar archivos al sistema (ROBUSTO)
    se_requiere_reinicio = False
    
    for item in ARCHIVOS_A_SINCRONIZAR:
        # CORRECCIÓN: Acceso correcto a la tupla mediante índices enteros (0, 1, 2)
        origen_rel = item[0]
        ruta_destino = item[1]
        permisos = item[2]
        
        ruta_origen = os.path.join(REPO_DIR, origen_rel)
        
        try:
            if os.path.exists(ruta_origen):
                # Verificar si falta en destino o si los contenidos difieren
                falta_destino = not os.path.exists(ruta_destino)
                diferente = not falta_destino and not filecmp.cmp(ruta_origen, ruta_destino, shallow=False)
                
                if hay_cambios_git or falta_destino or diferente:
                    log_y_print(f">>> Desplegando archivo: {os.path.basename(ruta_destino)}")
                    
                    # Asegurar que el directorio padre existe antes de copiar
                    dir_padre = os.path.dirname(ruta_destino)
                    if dir_padre:
                        os.makedirs(dir_padre, exist_ok=True)

                    shutil.copy2(ruta_origen, ruta_destino)
                    os.chmod(ruta_destino, permisos)
                    
                    # Seguridad en sudoers.d: obligatoriamente root:root
                    if "/etc/sudoers.d/" in ruta_destino:
                        shutil.chown(ruta_destino, user="root", group="root")
                    
                    if ruta_destino == SCRIPT_BIN_PATH and (diferente or hay_cambios_git):
                        se_requiere_reinicio = True
            else:
                log_y_print(f"!!! Aviso: Archivo fuente no encontrado en repo: {origen_rel}")
        except Exception as e:
            log_y_print(f"!!! Error sincronizando {ruta_destino}: {e}")
            
    # 3. Reiniciar si el propio script cambió
    if se_requiere_reinicio:
        log_y_print(">>> EL ACTUALIZADOR SE HA ACTUALIZADO. REINICIANDO PROCESO...")
        try:
            if TRAY_PROCESS: cerrar_tray_icon()
            time.sleep(1)
            argumentos = sys.argv[:]
            if '--restarted' not in argumentos:
                argumentos.append('--restarted')
            os.execv(sys.executable, ['python3'] + argumentos)
        except Exception as e:
            log_y_print(f"!!! Error crítico reinicio: {e}")

# ==============================================================================
# FUNCIONES DE INTERFAZ Y SISTEMA
# ==============================================================================

def obtener_entorno_usuario(usuario):
    env_vars = {'DISPLAY': ':0'}
    try:
        uid = subprocess.check_output(["id", "-u", usuario], text=True).strip()
        env_vars['XDG_RUNTIME_DIR'] = f"/run/user/{uid}"
        env_vars['DBUS_SESSION_BUS_ADDRESS'] = f"unix:path=/run/user/{uid}/bus"
        
        pids = subprocess.check_output(["pgrep", "-u", usuario, "-f", "gnome-session|gnome-shell|session"], text=True).split()
        for pid in pids:
            try:
                with open(f"/proc/{pid}/environ", "rb") as f:
                    content = f.read().decode("utf-8", errors="ignore")
                for item in content.split('\0'):
                    if item.startswith("DISPLAY="):
                        env_vars['DISPLAY'] = item.split("=", 1)[1]
                        break
            except:
                continue
    except Exception as e:
        pass
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
    if not usuario or usuario == 'root':
        try:
            usuario = subprocess.check_output(
                ["loginctl", "list-sessions"], text=True
            ).split("\n")[1].split()[2]
        except:
            usuario = "administrador"

    icono_notif = ICONO_DEFECTO if os.path.exists(ICONO_DEFECTO) else "dialog-information"
    if icono == "error":
        icono_notif = "dialog-error"

    try:
        cmd = [
            'systemd-run',
            f'--machine={usuario}@.host',
            '--user',
            'notify-send',
            '-a', 'GuadaMint',
            '-i', icono_notif,
            titulo,
            mensaje
        ]
        subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
    except Exception as e:
        log_y_print(f"!!! Error al lanzar notificación: {e}")
        
def detectar_escritorio():
    if os.path.exists("/usr/bin/gnome-shell"): return "GNOME"
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

def verificar_e_instalar_apps():
    faltantes = [app for app in APPS_OBLIGATORIAS if subprocess.run(["dpkg", "-s", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0]
    if faltantes:
        log_y_print(f">>> Faltan {len(faltantes)} herramientas base.")
        actualizar_tray('trabajando', f"Instalando {len(faltantes)} herramienta...")
        mostrar_aviso("Mantenimiento", f"Instalando herramientas base:\n{', '.join(faltantes)}")
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
        auto_actualizar_desde_git()
        
        escritorio = detectar_escritorio()
        log_y_print(f">>> Escritorio: {escritorio}")
        
        verificar_e_instalar_apps()
        
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
