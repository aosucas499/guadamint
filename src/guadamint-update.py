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

logging.basicConfig(
    filename=LOG_FILE, 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ==============================================================================
# FUNCIONES
# ==============================================================================

def log_y_print(mensaje):
    print(mensaje, flush=True)
    logging.info(mensaje)

def obtener_usuario_grafico():
    """Detecta qué usuario está usando la pantalla (SUDO o ID 1000)."""
    user = os.environ.get('SUDO_USER')
    if user: return user
    try:
        return subprocess.check_output(["id", "-un", "1000"], text=True).strip()
    except:
        return None

def obtener_entorno_grafico_real(usuario):
    """
    MAGIA: Escanea los procesos del usuario para encontrar las variables 
    DISPLAY y XAUTHORITY reales, estén donde estén.
    """
    # Procesos que seguro tienen la configuración gráfica correcta
    procesos_objetivo = ["cinnamon-session", "xfce4-session", "xfwm4", "cinnamon-launcher", "session"]

    display_encontrado = ":0" # Valor por defecto
    xauth_encontrado = None

    try:
        # Obtenemos los PIDs (números de proceso) del usuario
        pids = subprocess.check_output(["pgrep", "-u", usuario], text=True).split()
        
        for pid in pids:
            try:
                # Leemos qué comando es
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmdline = f.read().decode("utf-8", errors="ignore").replace('\0', ' ')
                
                # Si el proceso es uno de los buscados...
                if any(proc in cmdline for proc in procesos_objetivo):
                    # ...leemos sus variables de entorno
                    with open(f"/proc/{pid}/environ", "rb") as f:
                        env_content = f.read().decode("utf-8", errors="ignore")
                    
                    # Parseamos las variables
                    for item in env_content.split('\0'):
                        if item.startswith("DISPLAY="):
                            display_encontrado = item.split("=", 1)[1]
                        elif item.startswith("XAUTHORITY="):
                            xauth_encontrado = item.split("=", 1)[1]
                    
                    # Si encontramos XAUTHORITY, paramos de buscar. ¡Ya lo tenemos!
                    if xauth_encontrado:
                        return display_encontrado, xauth_encontrado
            except:
                continue 
    except Exception as e:
        log_y_print(f">>> Aviso: No se pudo escanear entorno ({e})")

    # FALLBACK: Si no encontramos nada escaneando procesos, probamos rutas típicas
    log_y_print(">>> No se detectó entorno en procesos activos. Probando rutas estándar...")
    
    rutas_posibles = [
        f"/home/{usuario}/.Xauthority",
        f"/run/user/1000/gdm/Xauthority",
        f"/run/user/1000/X11/displayauth",
        f"/run/user/1000/.mutter-Xwaylandauth"
    ]
    
    for ruta in rutas_posibles:
        if os.path.exists(ruta):
            return display_encontrado, ruta

    return display_encontrado, None

def mostrar_ventana_grafica(titulo, mensaje):
    """Muestra la ventana Zenity usando el entorno robado."""
    
    if not shutil.which("zenity"):
        log_y_print(">>> ERROR: 'zenity' no instalado.")
        return

    usuario = obtener_usuario_grafico()
    if not usuario:
        log_y_print(">>> AVISO: No se detectó usuario.")
        return

    # AQUÍ ESTÁ EL CAMBIO CLAVE: Obtenemos los datos reales
    display_real, xauth_real = obtener_entorno_grafico_real(usuario)
    
    if not xauth_real:
        log_y_print(f">>> AVISO: Imposible encontrar archivo XAUTHORITY para {usuario}.")
        return

    log_y_print(f">>> Entorno gráfico detectado: DISPLAY={display_real}, XAUTH={xauth_real}")

    cmd = [
        'sudo', '-u', usuario,
        'env', 
        f'DISPLAY={display_real}', 
        f'XAUTHORITY={xauth_real}',
        'zenity', '--info', 
        '--title', titulo,
        '--text', f"<span size='large'><b>{mensaje}</b></span>",
        '--width', '400',
        '--timeout', '10'
    ]
    
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            log_y_print(">>> ÉXITO: Ventana mostrada.")
        else:
            log_y_print(f">>> ERROR ZENITY (Cod {res.returncode}):\n    {res.stderr}")
    except Exception as e:
        log_y_print(f">>> EXCEPCIÓN: {e}")

def detectar_escritorio():
    log_y_print("--- Analizando entorno ---")
    es_cinnamon = os.path.exists("/usr/bin/cinnamon-session")
    es_xfce = os.path.exists("/usr/bin/xfce4-session")
    
    escritorio = "Desconocido"
    if es_cinnamon: escritorio = "CINNAMON"
    elif es_xfce:   escritorio = "XFCE"
    
    log_y_print(f">>> VARIABLE DETECTADA: {escritorio}")
    mostrar_ventana_grafica("GuadaMint", f"Escritorio detectado: {escritorio}")

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    if os.geteuid() != 0:
        print("!!! ERROR: Ejecuta con SUDO.")
        sys.exit(1)

    log_y_print("\n=== INICIO ===")
    detectar_escritorio()
    log_y_print("=== FIN ===")

if __name__ == "__main__":
    main()
