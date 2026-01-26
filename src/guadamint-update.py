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
    if os.geteuid() != 0:
        print("!!! ERROR: Debes ejecutar este script como ROOT (sudo).")
        sys.exit(1)

    log_y_print("=== INICIO SERVICIO GUADAMINT ===")
    
    # 1. DETECCIÓN DE ESCRITORIO
    tipo_escritorio = detectar_escritorio()
    log_y_print(f">>> Entorno detectado: {tipo_escritorio}")

    # --- TU CÓDIGO FUTURO AQUÍ ---
    if tipo_escritorio == "XFCE":
        pass 
    elif tipo_escritorio == "CINNAMON":
        pass 
    # -----------------------------

    # 2. ESPERA DE SEGURIDAD (10-60 segundos)
    wait_time = random.randint(10, 60)
    log_y_print(f">>> Esperando {wait_time} segundos antes de actualizar...")
    time.sleep(wait_time)

    # 3. GESTIÓN DE LOCK FILE
    try:
        with open(LOCK_FILE, 'w') as f: f
