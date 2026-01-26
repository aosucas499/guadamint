#!/usr/bin/env python3
import subprocess
import logging
import os
import sys
import shutil

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
LOG_FILE = "/var/log/guadamint/detector.log"

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
    """Muestra el mensaje en la terminal y lo guarda en el log."""
    print(mensaje, flush=True)
    logging.info(mensaje)

def obtener_usuario_grafico():
    """Detecta qué usuario está usando la pantalla."""
    # 1. Si lo ejecutas tú con sudo
    user = os.environ.get('SUDO_USER')
    if user: return user

    # 2. Si lo ejecuta el sistema, buscamos el usuario 1000
    try:
        return subprocess.check_output(["id", "-un", "1000"], text=True).strip()
    except:
        return None

def mostrar_ventana_grafica(titulo, mensaje):
    """Muestra la ventana Zenity saltándose la seguridad de Root."""
    
    # 0. Verificación de Zenity
    if not shutil.which("zenity"):
        log_y_print(">>> ERROR: 'zenity' no está instalado.")
        return

    usuario = obtener_usuario_grafico()
    
    if not usuario:
        log_y_print(">>> AVISO: No se detectó usuario gráfico.")
        return

    # Localizamos la llave de seguridad (.Xauthority)
    xauth = f"/home/{usuario}/.Xauthority"
    
    if not os.path.exists(xauth):
        log_y_print(f">>> AVISO: El usuario {usuario} no tiene archivo .Xauthority (¿Sin sesión gráfica?).")
        return

    # Construimos el comando ROBUSTO
    # Usamos 'env' dentro de sudo para inyectar las variables directamente al proceso final
    cmd = [
        'sudo', '-u', usuario,
        'env', 
        'DISPLAY=:0', 
        f'XAUTHORITY={xauth}',
        'zenity', '--info', 
        '--title', titulo,
        '--text', f"<span size='large'><b>{mensaje}</b></span>",
        '--width', '400',
        '--timeout', '10'
    ]
    
    log_y_print(f">>> Intentando mostrar ventana a usuario: {usuario}")
    
    try:
        # Capturamos stdout y stderr para ver qué pasa
        resultado = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if resultado.returncode == 0:
            log_y_print(">>> ÉXITO: Ventana mostrada correctamente.")
        else:
            log_y_print(f">>> ERROR AL MOSTRAR VENTANA (Código {resultado.returncode}):")
            log_y_print(f"    DETALLE TÉCNICO: {resultado.stderr}")

    except Exception as e:
        log_y_print(f">>> EXCEPCIÓN CRÍTICA: {e}")

def detectar_escritorio():
    """Detecta el escritorio y muestra el aviso."""
    log_y_print("--- Analizando entorno de escritorio ---")
    
    es_cinnamon = os.path.exists("/usr/bin/cinnamon-session")
    es_xfce = os.path.exists("/usr/bin/xfce4-session")
    
    nombre_escritorio = "Desconocido"

    if es_cinnamon:
        nombre_escritorio = "CINNAMON"
    elif es_xfce:
        nombre_escritorio = "XFCE"
    
    log_y_print(f">>> VARIABLE DETECTADA: {nombre_escritorio}")
    
    # Mensaje para la ventana
    msj = f"Bienvenido a GuadaMint.\nSe ha detectado el escritorio: {nombre_escritorio}"
    mostrar_ventana_grafica("Información del Sistema", msj)

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    if os.geteuid() != 0:
        print("!!! ERROR: Debes ejecutar este script como ROOT (sudo).")
        sys.exit(1)

    log_y_print("\n=== INICIO DE DETECCIÓN ===")
    
    # Detectar y Avisar
    detectar_escritorio()

    log_y_print("=== FIN DEL PROCESO ===")

if __name__ == "__main__":
    main()
