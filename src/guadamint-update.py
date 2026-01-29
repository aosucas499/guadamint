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

# Icono personalizado (si existe) o uno genérico del sistema
ICONO_DEFECTO = "/usr/share/icons/guadamintuz.svg"

# LISTA DE APPS QUE DEBEN ESTAR INSTALADAS SÍ O SÍ
APPS_OBLIGATORIAS = [
    # Utilidades sistema
    "zram-tools", 
    
    # Suite Tux (Infantil/Primaria)
    "tuxtype", "tuxmath", "tuxpaint", 
    
    # Suite KDE-Edu (Lengua/Geografía)
    "kgeography", "kwordquiz", "klettres", "khangman", "kanagram", 
    
    # Ciencia y Lógica
    "stellarium", "kalzium", "step", "gbrainy", "marble",
    
    # Programación
    "scratch", "kturtle", "thonny", "minetest",
    
    # Multimedia y Creatividad
    "gcompris-qt", "childsplay", "audacity", "pinta",
    
    # Mecanografía formal
    "klavaro"
]

# Configuración de Logging
logging.basicConfig(
    filename=LOG_FILE, 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Variable global para controlar el proceso del icono
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

def obtener_entorno_usuario(usuario):
    """
    Recupera las variables de entorno críticas (DISPLAY y DBUS) del usuario.
    Esto es necesario para que el icono se ancle en la barra de tareas.
    """
    env_vars = {'DISPLAY': ':0'} # Valor por defecto

    try:
        # Buscamos el PID del gestor de sesión del usuario
        # Buscamos procesos clave: cinnamon-session, xfce4-session
        pids = subprocess.check_output(["pgrep", "-u", usuario, "-f", "session"], text=True).split()
        
        for pid in pids:
            try:
                with open(f"/proc/{pid}/environ", "rb") as f:
                    contenido = f.read().decode("utf-8", errors="ignore")
                    
                # Extraemos las variables que nos interesan
                for item in contenido.split('\0'):
                    if item.startswith("DBUS_SESSION_BUS_ADDRESS="):
                        env_vars['DBUS_SESSION_BUS_ADDRESS'] = item.split("=", 1)[1]
                    elif item.startswith("DISPLAY="):
                        env_vars['DISPLAY'] = item.split("=", 1)[1]
                
                # Si encontramos el DBUS, nos damos por satisfechos
                if 'DBUS_SESSION_BUS_ADDRESS' in env_vars:
                    break
            except: continue
    except Exception as e:
        log_y_print(f"Aviso: No se pudo obtener entorno completo ({e})")
    
    return env_vars

# ==============================================================================
# GESTIÓN DEL ICONO DE BANDEJA (SYSTEM TRAY)
# ==============================================================================

def iniciar_tray_icon():
    """Inicia el icono en la barra de tareas en modo escucha."""
    global TRAY_PROCESS
    usuario = obtener_usuario_real()
    if not usuario: return

    # Obtenemos el entorno real para poder conectar con la barra de tareas
    entorno_grafico = os.environ.copy()
    datos_sesion = obtener_entorno_usuario(usuario)
    entorno_grafico.update(datos_sesion)

    # Icono inicial
    icono_inicial = ICONO_DEFECTO if os.path.exists(ICONO_DEFECTO) else "system-software-update"

    cmd = [
        'sudo', '-u', usuario,
        'zenity', '--notification',
        '--listen', # Modo escucha
        f'--window-icon={icono_inicial}'
        # NOTA: Quitamos --text inicial para que no salga burbuja, solo icono
    ]

    try:
        TRAY_PROCESS = subprocess.Popen(
            cmd, 
            env=entorno_grafico, 
            stdin=subprocess.PIPE, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            text=True
        )
        # Enviamos tooltip inicial silencioso
        actualizar_tray('inicio', "GuadaMint Iniciando...")
        log_y_print(">>> Icono de bandeja iniciado.")
    except Exception as e:
        log_y_print(f"Error al iniciar icono tray: {e}")

def actualizar_tray(estado, mensaje=""):
    """
    Cambia el icono y el texto de la bandeja.
    """
    global TRAY_PROCESS
    if not TRAY_PROCESS or TRAY_PROCESS.poll() is not None:
        return

    iconos = {
        'inicio': 'preferences-system',
        'trabajando': 'system-software-install',
        'ok': 'security-high',
        'error': 'dialog-error'
    }
    
    icono_nombre = iconos.get(estado, 'info')
    if estado == 'inicio' and os.path.exists(ICONO_DEFECTO):
        icono_nombre = ICONO_DEFECTO

    try:
        if mensaje:
            TRAY_PROCESS.stdin.write(f"tooltip: GuadaMint - {mensaje}\n")
        
        TRAY_PROCESS.stdin.write(f"icon: {icono_nombre}\n")
        TRAY_PROCESS.stdin.flush()
    except Exception:
        pass

def cerrar_tray_icon():
    """Cierra el icono de la bandeja."""
    global TRAY_PROCESS
    if TRAY_PROCESS:
        try:
            TRAY_PROCESS.terminate()
            TRAY_PROCESS = None
        except: pass

# ==============================================================================
# FUNCIONES GRÁFICAS Y SISTEMA
# ==============================================================================

def mostrar_aviso(titulo, mensaje, icono="info"):
    """Muestra una ventana Zenity (popup)."""
    usuario = obtener_usuario_real()
    if not usuario: return

    entorno_grafico = os.environ.copy()
    entorno_grafico.update(obtener_entorno_usuario(usuario))

    cmd = [
        'sudo', '-u', usuario,
        'zenity', '--info',
        '--title', titulo,
        '--text', mensaje,
        '--width', '400',
        '--timeout', '10'
    ]
    if icono: cmd.append(f'--window-icon={icono}')

    try:
        subprocess.Popen(cmd, env=entorno_grafico, stderr=subprocess.DEVNULL)
    except Exception as e:
        log_y_print(f"Error al mostrar ventana: {e}")

def detectar_escritorio():
    if os.path.exists("/usr/bin/cinnamon-session"): return "CINNAMON"
    elif os.path.exists("/usr/bin/xfce4-session"): return "XFCE"
    else: return "DESCONOCIDO"

def ejecutar_comando(comando, visible=False):
    try:
        env = os.environ.copy()
        env['DEBIAN_FRONTEND'] = 'noninteractive'
        
        if visible:
            subprocess.run(comando, text=True, env=env, check=True)
        else:
            subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, check=True)
            
        log_y_print(f"OK: {' '.join(comando)}")
        return True
    except subprocess.CalledProcessError as e:
        log_y_print(f"ERROR: {' '.join(comando)}")
        if not visible:
            logging.error(f"STDERR: {e.stderr}")
        return False

# --- FUNCIÓN PARA APPS ---
def verificar_e_instalar_apps():
    """Comprueba la lista de apps obligatorias e instala las que falten."""
    faltantes = []
    
    actualizar_tray('inicio', "Verificando aplicaciones...")
    log_y_print("--- Verificando aplicaciones obligatorias ---")
    
    for app in APPS_OBLIGATORIAS:
        resultado = subprocess.run(
            ["dpkg", "-s", app], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        if resultado.returncode != 0:
            log_y_print(f">>> Falta la aplicación: {app}")
            faltantes.append(app)
    
    if len(faltantes) > 0:
        log_y_print(f">>> Instalando {len(faltantes)} aplicaciones faltantes...")
        
        actualizar_tray('trabajando', f"Instalando {len(faltantes)} apps...")
        mostrar_aviso("Mantenimiento GuadaMint", f"Instalando {len(faltantes)} aplicaciones educativas nuevas...")
        
        ejecutar_comando(['apt-get', 'update'], visible=True)
        comando_install = ['apt-get', 'install', '-y'] + faltantes
        
        if ejecutar_comando(comando_install, visible=True):
            log_y_print(">>> Aplicaciones instaladas correctamente.")
            actualizar_tray('ok', "Instalación completada")
            mostrar_aviso("GuadaMint", "Software educativo actualizado correctamente.")
        else:
            log_y_print("!!! Error al instalar aplicaciones.")
            actualizar_tray('error', "Error en instalación")
            mostrar_aviso("Error", "Fallo al instalar algunas aplicaciones.", icono="error")
    else:
        log_y_print(">>> Todas las aplicaciones están instaladas.")
        actualizar_tray('ok', "Sistema al día")

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
        # 1. DETECCIÓN
        tipo_escritorio = detectar_escritorio()
        log_y_print(f">>> Entorno detectado: {tipo_escritorio}")

        # 2. APPS
        verificar_e_instalar_apps()

        # 3. FUTURO
        if tipo_escritorio == "XFCE": pass 
        elif tipo_escritorio == "CINNAMON": pass 

        # 4. ESPERA DE SEGURIDAD
        wait_time = random.randint(5, 10)
        log_y_print(f">>> Esperando {wait_time} segundos antes de terminar...")
        time.sleep(wait_time)

        # 5. LOCK FILE
        try:
            with open(LOCK_FILE, 'w') as f: f.write("running")
        except: pass

        if os.path.exists(LOCK_FILE):
            try: os.remove(LOCK_FILE)
            except: pass
            
    finally:
        cerrar_tray_icon()
    
    log_y_print("=== FIN DEL SERVICIO ===")

if __name__ == "__main__":
    main()
