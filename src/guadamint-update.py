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

# LISTA DE APPS QUE DEBEN ESTAR INSTALADAS SÍ O SÍ
APPS_OBLIGATORIAS = [
    # Utilidades sistema
    "zram-tools", "git",
    
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

# ==============================================================================
# FUNCIONES
# ==============================================================================

def log_y_print(mensaje):
    """Escribe en log y terminal."""
    print(mensaje, flush=True)
    logging.info(mensaje)

def obtener_usuario_real():
    """Detecta quién es el usuario que inició la sesión gráfica."""
    return os.environ.get('SUDO_USER')

def mostrar_aviso(titulo, mensaje, icono="info"):
    """Muestra una ventana Zenity en la pantalla del usuario."""
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

def ejecutar_comando(comando):
    """Ejecuta comandos apt de forma silenciosa."""
    try:
        env = os.environ.copy()
        env['DEBIAN_FRONTEND'] = 'noninteractive'
        subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, check=True)
        log_y_print(f"OK: {' '.join(comando)}")
        return True
    except subprocess.CalledProcessError as e:
        log_y_print(f"ERROR: {' '.join(comando)}")
        logging.error(f"STDERR: {e.stderr}")
        return False

# --- FUNCIÓN PARA APPS ---
def verificar_e_instalar_apps():
    """Comprueba la lista de apps obligatorias e instala las que falten."""
    faltantes = []
    
    log_y_print("--- Verificando aplicaciones obligatorias ---")
    
    for app in APPS_OBLIGATORIAS:
        # dpkg -s devuelve 0 si está instalado, 1 si no
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
        
        mostrar_aviso("Mantenimiento GuadaMint", f"Instalando {len(faltantes)} aplicaciones educativas nuevas...")
        
        ejecutar_comando(['apt-get', 'update'])
        comando_install = ['apt-get', 'install', '-y'] + faltantes
        
        if ejecutar_comando(comando_install):
            log_y_print(">>> Aplicaciones instaladas correctamente.")
            mostrar_aviso("GuadaMint", "Software educativo actualizado correctamente.")
        else:
            log_y_print("!!! Error al instalar aplicaciones.")
            mostrar_aviso("Error", "Fallo al instalar algunas aplicaciones.", icono="error")
    else:
        log_y_print(">>> Todas las aplicaciones obligatorias están instaladas.")

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    if os.geteuid() != 0:
        print("!!! ERROR: Debes ejecutar este script como ROOT (sudo).")
        sys.exit(1)

    log_y_print("=== INICIO SERVICIO GUADAMINT ===")
    
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
    
    log_y_print("=== FIN DEL SERVICIO ===")

if __name__ == "__main__":
    main()
