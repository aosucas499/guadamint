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

def enviar_notificacion(titulo, mensaje):
    """
    Intenta enviar una notificación visual al usuario.
    Nota: Desde systemd esto es complejo porque no hay 'pantalla' asociada al servicio.
    Intentamos forzar la pantalla :0.
    """
    try:
        # Definimos el entorno para que sepa dónde mostrar la ventana
        env = os.environ.copy()
        env['DISPLAY'] = ':0'
        env['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=/run/user/1000/bus' # Asume usuario ID 1000 (el primer usuario creado)
        
        # Ejecutamos notify-send
        subprocess.run(
            ['notify-send', '-u', 'normal', '-t', '5000', titulo, mensaje],
            env=env,
            stderr=subprocess.DEVNULL
        )
        # También lo mandamos a la terminal por si se ejecuta manual
        print(f"AVISO: {titulo} - {mensaje}")
        
    except Exception as e:
        logging.error(f"No se pudo enviar notificación visual: {e}")

def detectar_escritorio():
    """Comprueba si es Cinnamon o XFCE y avisa."""
    logging.info("--- Detectando Entorno de Escritorio ---")
    
    es_cinnamon = os.path.exists("/usr/bin/cinnamon-session")
    es_xfce = os.path.exists("/usr/bin/xfce4-session")
    
    if es_cinnamon:
        msj = "Se ha detectado el escritorio CINNAMON."
        logging.info("DETECTADO: Cinnamon")
        enviar_notificacion("GuadaMint Info", msj)
        
    elif es_xfce:
        msj = "Se ha detectado el escritorio XFCE."
        logging.info("DETECTADO: XFCE")
        enviar_notificacion("GuadaMint Info", msj)
        
    else:
        msj = "No se ha identificado un escritorio estándar (ni XFCE ni Cinnamon)."
        logging.warning("DETECTADO: Desconocido")
        enviar_notificacion("GuadaMint Info", msj)

def ejecutar_comando(comando):
    """Ejecuta comando apt de forma silenciosa y segura."""
    try:
        env = os.environ.copy()
        env['DEBIAN_FRONTEND'] = 'noninteractive'
        subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, check=True)
        logging.info(f"OK: {' '.join(comando)}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"FALLO: {' '.join(comando)} -> {e.stderr}")
        return False

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    if os.geteuid() != 0:
        print("Este script debe ejecutarse como ROOT.")
        # Si lo ejecutas como usuario normal para probar, intentará notificar igual
        detectar_escritorio()
        sys.exit(1)

    logging.info("=== INICIO SERVICIO ===")
    
    # 1. Detectar y Avisar
    detectar_escritorio()

    # 2. Espera de seguridad (para no saturar red al arrancar)
    wait = random.randint(10, 60)
    logging.info(f"Esperando {wait} segundos...")
    time.sleep(wait)

    # Crear lock
    with open(LOCK_FILE, 'w') as f: f.write("updating")

    # 3. Actualizar
    try:
        logging.info("Actualizando repositorios...")
        if ejecutar_comando(['apt-get', 'update']):
            logging.info("Instalando actualizaciones...")
            cmd = [
                'apt-get', 'dist-upgrade', '-y',
                '-o', 'Dpkg::Options::=--force-confdef',
                '-o', 'Dpkg::Options::=--force-confold'
            ]
            if ejecutar_comando(cmd):
                ejecutar_comando(['apt-get', 'autoremove', '-y'])
                ejecutar_comando(['apt-get', 'autoclean'])
    except Exception as e:
        logging.critical(f"Error fatal: {e}")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        logging.info("=== FIN ===")

if __name__ == "__main__":
    main()
