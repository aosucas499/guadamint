#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
import subprocess
import os
import sys
import threading
import shutil
import grp
import time
import datetime

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
ICONO_APP = "/usr/share/icons/guadamintuz.svg"
TITULO_APP = "Centro de Software GuadaMint"

# Configuración de Logs
if os.geteuid() == 0:
    LOG_FILE = "/var/log/guadamint/tienda.log"
else:
    LOG_FILE = f"/tmp/guadamint-tienda-{os.getuid()}.log"

# Asegurar directorio de logs si somos root
if os.geteuid() == 0 and not os.path.exists(os.path.dirname(LOG_FILE)):
    try: os.makedirs(os.path.dirname(LOG_FILE))
    except: pass

# --- CATÁLOGO DE APLICACIONES ---
CATALOGO = [
    {
        "categoria": "Educación Infantil y Primaria",
        "apps": [
            {"id": "gcompris-qt", "nombre": "GCompris", "desc": "Suite educativa (2-10 años)", "icono": "gcompris-qt"},
            {"id": "tuxtype", "nombre": "Tux Typing", "desc": "Mecanografía infantil", "icono": "tuxtype"},
            {"id": "tuxmath", "nombre": "Tux Math", "desc": "Matemáticas arcade", "icono": "tuxmath"},
            {"id": "tuxpaint", "nombre": "Tux Paint", "desc": "Dibujo para niños", "icono": "tuxpaint"},
            {"id": "kanagram", "nombre": "Kanagram", "desc": "Anagramas y vocabulario", "icono": "kanagram"},
            {"id": "khangman", "nombre": "KHangMan", "desc": "Juego del ahorcado", "icono": "khangman"},
        ]
    },
    {
        "categoria": "Educación Secundaria y Bachillerato",
        "apps": [
            {"id": "geogebra", "nombre": "GeoGebra", "desc": "Matemáticas dinámicas", "icono": "geogebra"},
            {"id": "stellarium", "nombre": "Stellarium", "desc": "Planetario virtual", "icono": "stellarium"},
            {"id": "kalzium", "nombre": "Kalzium", "desc": "Tabla periódica", "icono": "kalzium"},
            {"id": "step", "nombre": "Step", "desc": "Simulador físico", "icono": "step"},
            {"id": "marble", "nombre": "Marble", "desc": "Globo terráqueo virtual", "icono": "marble"},
            {"id": "kgeography", "nombre": "KGeography", "desc": "Geografía mundial", "icono": "kgeography"},
            {"id": "kwordquiz", "nombre": "KWordQuiz", "desc": "Tarjetas de vocabulario", "icono": "kwordquiz"},
            {"id": "celestia", "nombre": "Celestia", "desc": "Simulador espacial 3D", "icono": "celestia"},
        ]
    },
    {
        "categoria": "Programación y Robótica",
        "apps": [
            {"id": "scratch", "nombre": "Scratch", "desc": "Programación visual", "icono": "scratch"},
            {"id": "kturtle", "nombre": "KTurtle", "desc": "Programación Logo", "icono": "kturtle"},
            {"id": "thonny", "nombre": "Thonny", "desc": "Python para principiantes", "icono": "thonny"},
            {"id": "minetest", "nombre": "Minetest", "desc": "Mundo abierto (Minecraft libre)", "icono": "minetest"},
            {"id": "fritzing", "nombre": "Fritzing", "desc": "Diseño de circuitos", "icono": "fritzing"},
            {"id": "arduino", "nombre": "Arduino IDE", "desc": "Programación Arduino", "icono": "arduino"},
        ]
    },
    {
        "categoria": "Creatividad y Multimedia",
        "apps": [
            {"id": "audacity", "nombre": "Audacity", "desc": "Editor de audio", "icono": "audacity"},
            {"id": "inkscape", "nombre": "Inkscape", "desc": "Diseño vectorial", "icono": "inkscape"},
            {"id": "blender", "nombre": "Blender", "desc": "Animación 3D", "icono": "blender"},
            {"id": "kdenlive", "nombre": "Kdenlive", "desc": "Editor de vídeo", "icono": "kdenlive"},
            {"id": "obs-studio", "nombre": "OBS Studio", "desc": "Grabación de pantalla", "icono": "obs"},
            {"id": "lmms", "nombre": "LMMS", "desc": "Producción musical", "icono": "lmms"},
        ]
    },
    {
        "categoria": "Utilidades y Navegadores",
        "apps": [
            {"id": "google-chrome-stable", "nombre": "Google Chrome", "desc": "Navegador oficial Google", "icono": "google-chrome", "script_install": "instalar_chrome.sh"},
            {"id": "klavaro", "nombre": "Klavaro", "desc": "Curso de mecanografía", "icono": "klavaro"},
            {"id": "gnome-network-displays", "nombre": "Pantallas Wifi", "desc": "Proyección inalámbrica", "icono": "preferences-desktop-display"},
            {"id": "vlc", "nombre": "VLC", "desc": "Reproductor multimedia", "icono": "vlc"},
            {"id": "chromium-browser", "nombre": "Chromium", "desc": "Navegador libre", "icono": "chromium-browser"},
            {"id": "gbrainy", "nombre": "GBrainy", "desc": "Juegos de lógica", "icono": "gbrainy"},
            {"id": "filezilla", "nombre": "FileZilla", "desc": "Cliente FTP", "icono": "filezilla"},
        ]
    }
]

# --- AUTO-UPDATE CONFIG ---
REPO_DIR = "/opt/guadamint"
REPO_URL = "https://github.com/aosucas499/guadamint.git"
REPO_BRANCH = "main"
SCRIPT_SRC = os.path.join(REPO_DIR, "src/apps-guadamint.py")
SCRIPT_BIN = "/usr/bin/apps-guadamint.py"
RUTA_SCRIPTS_REPO = "/opt/guadamint/src/scripts"

# ==============================================================================
# SISTEMA DE LOGS (REEMPLAZA A PRINT)
# ==============================================================================
def log(msg):
    """Escribe en el archivo de log en lugar de la terminal."""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except: pass # Si falla el log, no rompemos la app

# Redirigimos stdout y stderr al log para capturar todo
# (Opcional, pero ayuda si alguna librería hace print)
# sys.stdout = open(LOG_FILE, 'a')
# sys.stderr = open(LOG_FILE, 'a')

# ==============================================================================
# SEGURIDAD Y PERMISOS
# ==============================================================================
def es_administrador():
    try:
        if os.geteuid() == 0: return True
        gid_list = os.getgroups()
        for gid in gid_list:
            nombre = grp.getgrgid(gid).gr_name
            if nombre == 'sudo' or nombre == 'admin': return True
        return False
    except: return False

def elevar_a_root():
    if os.geteuid() != 0:
        log("Elevando privilegios con pkexec...")
        usuario_real = os.environ.get('USER', 'usuario')
        env = os.environ.copy()
        if 'XAUTHORITY' not in env:
            possible_auth = f"/home/{usuario_real}/.Xauthority"
            if os.path.exists(possible_auth):
                env['XAUTHORITY'] = possible_auth
        
        args = ['pkexec', 'env', f'DISPLAY={env.get("DISPLAY", ":0")}', 
                f'XAUTHORITY={env.get("XAUTHORITY", "")}', 
                sys.executable] + sys.argv
        try:
            os.execvpe('pkexec', args, env)
        except Exception as e:
            log(f"Error elevación: {e}")
            sys.exit(1)

def hay_bloqueo_apt():
    locks = ["/var/lib/dpkg/lock-frontend", "/var/lib/dpkg/lock"]
    for lock in locks:
        if subprocess.run(["fuser", lock], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return True
    return False

# ==============================================================================
# AUTO-UPDATE
# ==============================================================================
def auto_update():
    if not os.access(SCRIPT_BIN, os.W_OK): return
    try:
        if not os.path.exists(REPO_DIR):
            subprocess.run(["git", "clone", "-b", REPO_BRANCH, REPO_URL, REPO_DIR], check=True)
        else:
            os.chdir(REPO_DIR)
            subprocess.run(["git", "fetch", "origin"], check=True, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "reset", "--hard", f"origin/{REPO_BRANCH}"], check=True, stderr=subprocess.DEVNULL)
        
        if os.path.exists(SCRIPT_SRC) and os.path.realpath(__file__) != os.path.realpath(SCRIPT_SRC):
            with open(SCRIPT_SRC, 'rb') as f1, open(SCRIPT_BIN, 'rb') as f2:
                if f1.read() != f2.read():
                    log("Actualizando script de la tienda...")
                    shutil.copy2(SCRIPT_SRC, SCRIPT_BIN)
                    os.chmod(SCRIPT_BIN, 0o755)
                    os.execv(sys.executable, [sys.executable] + sys.argv)
    except: pass

# ==============================================================================
# INTERFAZ GRÁFICA
# ==============================================================================
class FilaApp(Gtk.ListBoxRow):
    def __init__(self, app_data, ventana_padre):
        super().__init__()
        self.app_data = app_data
        self.ventana_padre = ventana_padre
        self.pkg_name = app_data["id"]

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_border_width(10)
        
        icon = Gtk.Image()
        icon.set_pixel_size(48)
        icono_nombre = app_data["icono"]
        if os.path.isabs(icono_nombre) and os.path.exists(icono_nombre):
             icon.set_from_file(icono_nombre)
        elif Gtk.IconTheme.get_default().has_icon(icono_nombre):
            icon.set_from_icon_name(icono_nombre, Gtk.IconSize.DIALOG)
        else:
            icon.set_from_icon_name("system-software-install", Gtk.IconSize.DIALOG)
        box.pack_start(icon, False, False, 0)

        vbox_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_name = Gtk.Label(xalign=0)
        lbl_name.set_markup(f"<b>{app_data['nombre']}</b>")
        lbl_desc = Gtk.Label(label=app_data['desc'], xalign=0)
        lbl_desc.get_style_context().add_class("dim-label")
        lbl_desc.set_max_width_chars(40)
        lbl_desc.set_line_wrap(True)
        vbox_text.pack_start(lbl_name, True, True, 0)
        vbox_text.pack_start(lbl_desc, True, True, 0)
        box.pack_start(vbox_text, True, True, 0)

        self.switch = Gtk.Switch()
        self.switch.set_valign(Gtk.Align.CENTER)
        self.handler_id = self.switch.connect("state-set", self.on_switch_activated)
        
        self.spinner = Gtk.Spinner()
        
        box.pack_end(self.switch, False, False, 0)
        box.pack_end(self.spinner, False, False, 10)
        
        self.add(box)
        threading.Thread(target=self.check_installed).start()

    def check_installed(self):
        try:
            res = subprocess.run(
                ["dpkg-query", "-W", "-f='${Status}'", self.pkg_name], 
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
            )
            is_installed = "install ok installed" in res.stdout
        except:
            is_installed = False
        GLib.idle_add(self.update_switch_state, is_installed)

    def update_switch_state(self, state):
        self.switch.handler_block(self.handler_id)
        self.switch.set_active(state)
        self.switch.handler_unblock(self.handler_id)
        return False

    def on_switch_activated(self, switch, state):
        self.switch.set_sensitive(False)
        self.spinner.start()
        
        if hay_bloqueo_apt():
            self.mostrar_error("Sistema ocupado (APT bloqueado).\nInténtalo en un minuto.")
            self.spinner.stop()
            self.switch.set_sensitive(True)
            self.switch.handler_block(self.handler_id)
            self.switch.set_active(not state)
            self.switch.handler_unblock(self.handler_id)
            return True 

        action = "install" if state else "remove"
        threading.Thread(target=self.run_apt_action, args=(action,)).start()
        return True

    def mostrar_error(self, mensaje):
        dialog = Gtk.MessageDialog(parent=self.ventana_padre, flags=Gtk.DialogFlags.MODAL, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text="Aviso")
        dialog.format_secondary_text(mensaje)
        dialog.run()
        dialog.destroy()

    def run_apt_action(self, action):
        log(f"Iniciando acción: {action} {self.pkg_name}")
        error_msg = ""
        success = False
        cmd = []
        
        if action == "install" and "script_install" in self.app_data:
            nombre_script = self.app_data["script_install"]
            ruta_script = os.path.join(RUTA_SCRIPTS_REPO, nombre_script)
            if os.path.exists(ruta_script):
                os.chmod(ruta_script, 0o755)
                cmd = ["/bin/bash", ruta_script]
            else:
                error_msg = f"Script no encontrado: {ruta_script}"
        else:
            cmd = ["env", "DEBIAN_FRONTEND=noninteractive", "/usr/bin/apt-get", action, "-y", "-o", "Dpkg::Options::=--force-confdef", "-o", "Dpkg::Options::=--force-confold", self.pkg_name]

        if cmd:
            try:
                # Ejecutamos redirigiendo stdout/stderr a PIPE para escribirlos luego en el log
                # NO usamos print aquí para evitar que salga en terminal
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True
                )
                
                # Leemos la salida y la mandamos al log
                full_log = ""
                for line in process.stdout:
                    log(f"[APT] {line.strip()}") # Escribe en el archivo
                    full_log += line
                
                process.wait()
                
                if process.returncode == 0:
                    success = True
                    log("Acción completada con éxito.")
                else:
                    log(f"Error (Código {process.returncode})")
                    if "Unable to locate" in full_log: error_msg = f"Paquete no encontrado."
                    elif "lock" in full_log: error_msg = "Bloqueo APT."
                    else: error_msg = "Error en la ejecución. Ver logs."
            except Exception as e:
                log(f"Excepción Python: {e}")
                error_msg = str(e)

        GLib.idle_add(self.finish_action, success, action == "install", error_msg)

    def finish_action(self, success, intended_state, error_msg=""):
        self.spinner.stop()
        self.switch.set_sensitive(True)
        self.switch.handler_block(self.handler_id)
        
        if success:
            self.switch.set_active(intended_state)
            user = os.environ.get('SUDO_USER', os.environ.get('USER'))
            subprocess.Popen(['sudo', '-u', user, 'notify-send', '-i', 'system-software-update', 'GuadaMint Store', f'Operación completada: {self.app_data["nombre"]}'])
            threading.Thread(target=self.check_installed).start()
        else:
            self.switch.set_active(not intended_state)
            if error_msg: self.mostrar_error(error_msg)
            else: self.mostrar_error("Operación fallida. Revise los logs.")
        
        self.switch.handler_unblock(self.handler_id)
        return False

class GuadaStoreWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=TITULO_APP)
        self.set_default_size(600, 700)
        self.set_border_width(0)
        if os.path.exists(ICONO_APP): self.set_icon_from_file(ICONO_APP)

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title(TITULO_APP)
        header.set_subtitle("Instalador de Software Escolar (Modo Admin)")
        self.set_titlebar(header)
        
        btn_refresh = Gtk.Button()
        icon_refresh = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        btn_refresh.add(icon_refresh)
        btn_refresh.connect("clicked", self.refresh_all)
        header.pack_start(btn_refresh)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add(scrolled)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_box.set_border_width(15)
        scrolled.add(self.main_box)

        self.rows = []
        for seccion in CATALOGO:
            lbl_sec = Gtk.Label(label=seccion["categoria"], xalign=0)
            lbl_sec.get_style_context().add_class("h3")
            lbl_sec.set_margin_top(15)
            lbl_sec.set_margin_bottom(5)
            self.main_box.pack_start(lbl_sec, False, False, 0)
            
            listbox = Gtk.ListBox()
            listbox.set_selection_mode(Gtk.SelectionMode.NONE)
            listbox.get_style_context().add_class("frame") 
            
            for app in seccion["apps"]:
                row = FilaApp(app, self)
                listbox.add(row)
                self.rows.append(row)
            
            self.main_box.pack_start(listbox, False, False, 0)

    def refresh_all(self, widget):
        for row in self.rows:
            threading.Thread(target=row.check_installed).start()

def main():
    if not es_administrador():
        dialog = Gtk.MessageDialog(parent=None, flags=Gtk.DialogFlags.MODAL, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text="Acceso Restringido")
        dialog.format_secondary_text("Esta aplicación es solo para administradores.\n\nContacte con su administrador/a TDE para instalar aplicaciones.")
        dialog.set_title("GuadaMint Store")
        if os.path.exists(ICONO_APP): dialog.set_icon_from_file(ICONO_APP)
        dialog.run()
        dialog.destroy()
        sys.exit(0)

    elevar_a_root()
    try: auto_update()
    except: pass
    
    win = GuadaStoreWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
