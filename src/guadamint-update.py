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
    """
    Detecta quién es el usuario que inició la sesión gráfica.
    Es vital porque el script corre como ROOT (sudo) y necesitamos saber
    quién es el humano para mostrarle la ventana en su pantalla.
    """
    return os.environ.get('SUDO_USER')

def mostrar_aviso(titulo, mensaje, icono="info"):
    """
    Muestra una ventana Zenity en la pantalla del usuario.
    Truco: Se ejecuta como el usuario alumno (sudo -u) para que sea visible.
    """
    usuario = obtener_usuario_real()
    
    # Si no detectamos usuario (ej. corriendo en cron), no hacemos nada
    if not usuario:
        return

    # Comando para ejecutar zenity COMO el usuario alumno
    cmd = [
        'sudo', '-u', usuario,     # Cambiamos identidad al usuario
        'zenity', '--info',
        '--title', titulo,
        '--text', mensaje,
        '--width', '400',
        '--timeout', '10'          # Se cierra sola a los 10s
    ]
    
    # Añadimos el icono si se especifica
    if icono:
        cmd.append(f'--window-icon={icono}')

    # Preparamos el entorno gráfico apuntando a la pantalla principal :0
    env = os.environ.copy()
    env['DISPLAY'] = ':0'
    
    try:
        # Ejecutamos sin bloquear el script (stderr a DEVNULL para no ensuciar)
        subprocess.Popen(cmd, env=env, stderr=subprocess.DEVNULL)
    except Exception as e:
        log_y_print(f"Error al mostrar ventana: {e}")

def detectar_escritorio():
    """
    Comprueba qué entorno está instalado.
    Retorna: 'CINNAMON', 'XFCE' o 'DESCONOCIDO'
    """
    if os.path.exists("/usr/bin/cinnamon-session"):
        return "CINNAMON"
    elif os.path.exists("/usr/bin/xfce4-session"):
        return "XFCE"
    else:
        return "DESCONOCIDO"

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

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    # Comprobación de seguridad: El script DEBE ser root para funcionar
    # (El .desktop se encarga de llamar a sudo)
    if os.geteuid() != 0:
        print("!!! ERROR: Debes ejecutar este script como ROOT (sudo).")
        sys.exit(1)

    log_y_print("=== INICIO SERVICIO GUADAMINT ===")
    
    # 1. DETECCIÓN DE ESCRITORIO
    tipo_escritorio = detectar_escritorio()
    log_y_print(f">>> Entorno detectado: {tipo_escritorio}")

    # --- PRUEBA ZENITY ---
    # Esto confirma que el sistema gráfico funciona
    mostrar_aviso("GuadaMint Info", f"Entorno de escritorio detectado: <b>{tipo_escritorio}</b>")
    # ---------------------

    # --- ZONA DE LÓGICA FUTURA ---
    if tipo_escritorio == "XFCE":
        pass 
    elif tipo_escritorio == "CINNAMON":
        pass 
    # -----------------------------

    # 2. ESPERA DE SEGURIDAD (10-60 segundos)
    # Evita saturar la red si todos los PCs arrancan a la vez
    wait_time = random.randint(5, 10)
    log_y_print(f">>> Esperando {wait_time} segundos antes de actualizar...")
    time.sleep(wait_time)

    # 3. GESTIÓN DE LOCK FILE
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write("updating")
    except: pass

# --- LIMPIEZA FINAL (AÑADIDO) ---
    # Es buena práctica borrar el archivo lock al terminar
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except: pass
    
    log_y_print("=== FIN DEL SERVICIO ===")

if __name__ == "__main__":
    main()
