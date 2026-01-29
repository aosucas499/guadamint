#!/usr/bin/env python3
import subprocess
import logging
import os
import sys
import time
import random

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
LOG_FILE = "/var/log/guadamint/actualizador.log"
LOCK_FILE = "/tmp/guadamint-updating.lock"

# Icono personalizado
ICONO_DEFECTO = "/usr/share/icons/guadamintuz.svg"

# LISTA DE APPS OBLIGATORIAS (ACTUALIZADA)
APPS_OBLIGATORIAS = [
    # Utilidades sistema
    "zram-tools", "gnome-network-displays", 
    
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

# Configuración de Logging
logging.basicConfig(
    filename=LOG_FILE, 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Variable global para el proceso del icono
TRAY_PROCESS = None

# ==============================================================================
# FUNCIONES DE ENTORNO
# ==============================================================================

def log_y_print(mensaje):
    """Escribe en log y terminal."""
    print(mensaje, flush=True)
    logging.info(mensaje)

def obtener_usuario_real():
    return os.environ.get('SUDO_USER')

def obtener_entorno_usuario(usuario):
    """Recupera DISPLAY y DBUS del usuario para conectar Zenity."""
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

# ==============================================================================
# GESTIÓN DE NOTIFICACIONES (BURBUJAS)
# ==============================================================================

def iniciar_tray_icon():
    """Inicia Zenity en modo escucha."""
    global TRAY_PROCESS
    usuario = obtener_usuario_real()
    if not usuario: return

    entorno = os.environ.copy()
    entorno.update(obtener_entorno_usuario(usuario))

    icono_inicial = ICONO_DEFECTO if os.path.exists(ICONO_DEFECTO) else "system-software-update"

    # --listen hace que se quede esperando comandos
    cmd = [
        'sudo', '-u', usuario,
        'zenity', '--notification',
        '--listen', 
        f'--window-icon={icono_inicial}'
    ]

    try:
        TRAY_PROCESS = subprocess.Popen(
            cmd, 
            env=entorno, 
            stdin=subprocess.PIPE, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            text=True
        )
        actualizar_tray('inicio', "GuadaMint: Servicio iniciado")
    except Exception as e:
        log_y_print(f"Error tray: {e}")

def actualizar_tray(estado, mensaje=""):
    """
    Envía comandos a Zenity para cambiar icono o mostrar burbuja.
    """
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
        # CAMBIO CLAVE: Usamos 'message:' para forzar la burbuja
        if mensaje:
            TRAY_PROCESS.stdin.write(f"message: {mensaje}\n")
        
        TRAY_PROCESS.stdin.write(f"icon: {icono}\n")
        TRAY_PROCESS.stdin.flush()
    except: pass

def cerrar_tray_icon():
    global TRAY_PROCESS
    if TRAY_PROCESS:
        try:
            TRAY_PROCESS.terminate()
            TRAY_PROCESS = None
        except: pass

# ==============================================================================
# RESTO DE LÓGICA
# ==============================================================================

def mostrar_aviso(titulo, mensaje, icono="info"):
    """Muestra ventana central (popup) para avisos importantes."""
    usuario = obtener_usuario_real()
    if not usuario: return
    entorno = os.environ.copy()
    entorno.update(obtener_entorno_usuario(usuario))

    cmd = ['sudo', '-u', usuario, 'zenity', '--info', '--title', titulo, '--text', mensaje, 
           '--width=400', '--timeout=10', f'--window-icon={icono}']
    try: subprocess.Popen(cmd, env=entorno, stderr=subprocess.DEVNULL)
    except: pass

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
        if not visible: logging.error(f"STDERR: {e.stderr}")
        return False

def verificar_e_instalar_apps():
    faltantes = []
    actualizar_tray('inicio', "Verificando software educativo...")
    
    for app in APPS_OBLIGATORIAS:
        res = subprocess.run(["dpkg", "-s", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0:
            faltantes.append(app)
    
    if len(faltantes) > 0:
        log_y_print(f">>> Faltan {len(faltantes)} apps.")
        
        # Burbuja de aviso
        actualizar_tray('trabajando', f"Instalando {len(faltantes)} aplicaciones...")
        
        # Ventana central (opcional, si quieres asegurar que lo lean)
        mostrar_aviso("Mantenimiento", f"Instalando apps faltantes:\n{', '.join(faltantes)}")
        
        ejecutar_comando(['apt-get', 'update'], visible=True)
        if ejecutar_comando(['apt-get', 'install', '-y'] + faltantes, visible=True):
            actualizar_tray('ok', "Software actualizado correctamente")
        else:
            actualizar_tray('error', "Error al instalar software")
    else:
        log_y_print(">>> Todo en orden.")
        actualizar_tray('ok', "Sistema actualizado y listo")

def detectar_escritorio():
    if os.path.exists("/usr/bin/cinnamon-session"): return "CINNAMON"
    elif os.path.exists("/usr/bin/xfce4-session"): return "XFCE"
    return "DESCONOCIDO"

def main():
    if os.geteuid() != 0: sys.exit(1)
    
    iniciar_tray_icon()
    try:
        escritorio = detectar_escritorio()
        log_y_print(f">>> Escritorio: {escritorio}")
        
        verificar_e_instalar_apps()
        
        wait = random.randint(5, 10)
        time.sleep(wait)
        
        # Gestión Lock
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
