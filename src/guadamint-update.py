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
    "gcompris-qt", "audacity",
    
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

# ==============================================================================
# GESTIÓN DEL ICONO DE BANDEJA (SYSTEM TRAY)
# ==============================================================================

def iniciar_tray_icon():
    """Inicia el icono en la barra de tareas en modo escucha."""
    global TRAY_PROCESS
    usuario = obtener_usuario_real()
    if not usuario: return

    # Icono inicial: Usamos el personalizado si existe, si no uno de sistema
    icono_inicial = ICONO_DEFECTO if os.path.exists(ICONO_DEFECTO) else "system-software-update"

    cmd = [
        'sudo', '-u', usuario,
        'zenity', '--notification',
        '--listen', # Modo escucha: permite cambiar el icono dinámicamente
        f'--window-icon={icono_inicial}',
        '--text=GuadaMint: Iniciando...'
    ]

    env = os.environ.copy()
    env['DISPLAY'] = ':0'

    try:
        # Iniciamos el proceso y guardamos la referencia para enviarle comandos
        TRAY_PROCESS = subprocess.Popen(
            cmd, 
            env=env, 
            stdin=subprocess.PIPE, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            text=True
        )
        log_y_print(">>> Icono de bandeja iniciado.")
    except Exception as e:
        log_y_print(f"Error al iniciar icono tray: {e}")

def actualizar_tray(estado, mensaje=""):
    """
    Cambia el icono y el texto de la bandeja según el estado.
    Estados: 'trabajando', 'ok', 'error', 'info'
    """
    global TRAY_PROCESS
    if not TRAY_PROCESS or TRAY_PROCESS.poll() is not None:
        return # El icono no está corriendo

    # Definimos iconos estándar del tema (funcionan en Mint/XFCE)
    iconos = {
        'inicio': 'preferences-system',
        'trabajando': 'system-software-install', # O 'process-working'
        'ok': 'security-high',                  # O 'emblem-default'
        'error': 'dialog-error'
    }
    
    icono_nombre = iconos.get(estado, 'info')
    
    # Si tenemos el SVG personalizado y es el estado inicio, intentamos usarlo
    if estado == 'inicio' and os.path.exists(ICONO_DEFECTO):
        icono_nombre = ICONO_DEFECTO

    try:
        # Enviamos comandos a Zenity a través de su entrada estándar (stdin)
        if mensaje:
            TRAY_PROCESS.stdin.write(f"tooltip: GuadaMint - {mensaje}\n")
        
        # Cambiamos el icono
        TRAY_PROCESS.stdin.write(f"icon: {icono_nombre}\n")
        TRAY_PROCESS.stdin.flush()
    except Exception as e:
        log_y_print(f"No se pudo actualizar el icono: {e}")

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
    """Muestra una ventana Zenity (popup) en la pantalla del usuario."""
    usuario = obtener_usuario_real()
    if not usuario: return

    cmd = [
        'sudo', '-u', usuario,
        'zenity', '--info',
        '--title', titulo,
        '--text', mensaje,
        '--width', '400',
        '--timeout', '10'
    ]
    if icono: cmd.append(f'--window-icon={icono}')

    env = os.environ.copy()
    env['DISPLAY'] = ':0'
    
    try:
        subprocess.Popen(cmd, env=env, stderr=subprocess.DEVNULL)
    except Exception as e:
        log_y_print(f"Error al mostrar ventana: {e}")

def detectar_escritorio():
    """Retorna: 'CINNAMON', 'XFCE' o 'DESCONOCIDO'."""
    if os.path.exists("/usr/bin/cinnamon-session"): return "CINNAMON"
    elif os.path.exists("/usr/bin/xfce4-session"): return "XFCE"
    else: return "DESCONOCIDO"

def ejecutar_comando(comando, visible=False):
    """Ejecuta comandos apt."""
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
        
        # Cambiamos icono a "Trabajando"
        actualizar_tray('trabajando', f"Instalando {len(faltantes)} apps...")
        
        # Aviso visual en ventana también
        mostrar_aviso("Mantenimiento GuadaMint", f"Instalando {len(faltantes)} aplicaciones educativas nuevas...")
        
        # 1. Update
        ejecutar_comando(['apt-get', 'update'], visible=True)
        
        # 2. Install
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
        log_y_print(">>> Todas las aplicaciones obligatorias están instaladas.")
        actualizar_tray('ok', "Sistema al día")

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    if os.geteuid() != 0:
        print("!!! ERROR: Debes ejecutar este script como ROOT (sudo).")
        sys.exit(1)

    log_y_print("=== INICIO SERVICIO GUADAMINT ===")
    
    # Iniciar icono en la barra (se quedará ahí hasta que termine el script)
    iniciar_tray_icon()
    
    try:
        # 1. DETECCIÓN
        tipo_escritorio = detectar_escritorio()
        log_y_print(f">>> Entorno detectado: {tipo_escritorio}")

        # 2. COMPROBACIÓN DE APPS
        verificar_e_instalar_apps()

        # 3. ZONA DE LÓGICA FUTURA
        if tipo_escritorio == "XFCE":
            pass 
        elif tipo_escritorio == "CINNAMON":
            pass 

        # 4. ESPERA DE SEGURIDAD
        wait_time = random.randint(5, 10)
        log_y_print(f">>> Esperando {wait_time} segundos antes de terminar...")
        actualizar_tray('ok', "Finalizando...")
        time.sleep(wait_time)

        # 5. GESTIÓN DE LOCK FILE
        try:
            with open(LOCK_FILE, 'w') as f:
                f.write("running")
        except: pass

        # LIMPIEZA FINAL
        if os.path.exists(LOCK_FILE):
            try: os.remove(LOCK_FILE)
            except: pass
            
    finally:
        # Importante: Cerrar el icono al salir para que no se quede "zombie" en la barra
        cerrar_tray_icon()
    
    log_y_print("=== FIN DEL SERVICIO ===")

if __name__ == "__main__":
    main()
