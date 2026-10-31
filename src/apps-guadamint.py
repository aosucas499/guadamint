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
        "categoria": "Aplicaciones",
        "apps": [
            {"id": "vlc", "nombre": "VLC Media Player", "desc": "Reproductor multimedia de ejemplo", "icono": "vlc"},
            {"id": "openboard", "nombre": "Openboard", "desc": "Aplicación de pizarra interactiva", "icono": "openboard"},
        ]
    },
    {
        "categoria": "Scripts y Configuraciones",
        "apps": [
            {
                "id": "ubuntu-repos", 
                "nombre": "Repositorios Temporales de Ubuntu", 
                "desc": "Permite dependencias oficiales extra en RAM (/tmp). Se borran al reiniciar.", 
                "icono": "ubuntu-logo", 
                "script_install": "toggle-ubuntu-repos.sh"
            },
            {
                "id": "smart-product-drivers", 
                "nombre": "Drivers SMART Board", 
                "desc": "Controladores para pizarras interactivas", 
                "icono": "video-display", 
                "script_install": "instalar_smartboard.sh"
            },
            {
                "id": "flatpak", 
                "nombre": "Soporte Flatpak y Flathub", 
                "desc": "Instala el motor Flatpak y lo integra automáticamente en el Centro de Software", 
                "icono": "system-software-install", 
                "script_install": "toggle-flatpak.sh"
            },
        ]
    }
]

# --- AUTO-UPDATE CONFIG Y RUTAS ---
REPO_DIR = "/opt/guadamint"
REPO_URL = "https://github.com/aosucas499/guadamint.git"
REPO_BRANCH = "eos"
SCRIPT_SRC = os.path.join(REPO_DIR, "src/apps-guadamint.py")
SCRIPT_BIN = "/usr/bin/apps-guadamint.py"
RUTA_SCRIPTS_REPO = "/opt/guadamint/src/scripts"

# ==============================================================================
# SISTEMA DE LOGS
# ==============================================================================
def log(msg):
    try:
        print(msg)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except: pass

# ==============================================================================
# SEGURIDAD Y PERMISOS
# ==============================================================================
def es_administrador():
    try:
        if os.geteuid() == 0: return True
        gid_list = os.getgroups()
        for gid in gid_list:
            nombre = grp.getgrgid(gid).gr_name
            if nombre == 'sudo' or nombre == 'admin' or nombre == 'tde': return True
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
        git_dir = os.path.join(REPO_DIR, ".git")
        if not os.path.exists(REPO_DIR) or not os.path.exists(git_dir):
            if os.path.exists(REPO_DIR): shutil.rmtree(REPO_DIR)
            subprocess.run(["git", "clone", "-b", REPO_BRANCH, REPO_URL, REPO_DIR], check=True)
        else:
            subprocess.run(["git", "-C", REPO_DIR, "fetch", "origin"], check=True, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "-C", REPO_DIR, "reset", "--hard", f"origin/{REPO_BRANCH}"], check=True, stderr=subprocess.DEVNULL)
        
        if os.path.exists(SCRIPT_SRC) and os.path.realpath(__file__) != os.path.realpath(SCRIPT_SRC):
            with open(SCRIPT_SRC, 'rb') as f1, open(SCRIPT_BIN, 'rb') as f2:
                if f1.read() != f2.read():
                    log("Actualizando script de la tienda...")
                    shutil.copy2(SCRIPT_SRC, SCRIPT_BIN)
                    os.chmod(SCRIPT_BIN, 0o755)
                    os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        log(f"Error en auto_update: {e}")

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
        is_installed = False
        try:
            if "script_install" in self.app_data:
                ruta_script = os.path.join(RUTA_SCRIPTS_REPO, self.app_data["script_install"])
                if os.path.exists(ruta_script):
                    res = subprocess.run(["/bin/bash", ruta_script, "status"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    is_installed = (res.returncode == 0)
            else:
                res = subprocess.run(
                    ["dpkg-query", "-W", "--showformat=${Status}", self.pkg_name], 
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

        self.switch.set_state(state)

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
        
        if "script_install" in self.app_data:
            nombre_script = self.app_data["script_install"]
            ruta_script = os.path.join(RUTA_SCRIPTS_REPO, nombre_script)
            if os.path.exists(ruta_script):
                os.chmod(ruta_script, 0o755)
                param = "enable" if action == "install" else "disable"
                cmd = ["/bin/bash", ruta_script, param]
            else:
                error_msg = f"Script no encontrado: {ruta_script}"
        else:
            cmd = ["env", "DEBIAN_FRONTEND=noninteractive", "/usr/bin/apt-get", action, "-y", "-o", "Dpkg::Options::=--force-confdef", "-o", "Dpkg::Options::=--force-confold", self.pkg_name]

        if cmd:
            try:
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True
                )
                
                full_log = ""
                for line in process.stdout:
                    log(f"[EXEC] {line.strip()}")
                    full_log += line
                
                process.wait()
                
                if process.returncode == 0:
                    success = True
                    log("Comando completado con éxito.")
                else:
                    log(f"Error (Código {process.returncode})")
                    if "Unable to locate" in full_log: error_msg = f"Paquete no encontrado."
                    elif "lock" in full_log: error_msg = "Bloqueo APT."
                    else: error_msg = "Error en la ejecución. Ver logs."
            except Exception as e:
                log(f"Excepción Python: {e}")
                error_msg = str(e)

        GLib.idle_add(self.finish_action, success, (action == "install"), error_msg)

    def finish_action(self, success, intended_state, error_msg=""):
        self.spinner.stop()
        self.switch.set_sensitive(True)
        
        if success:
            user = os.environ.get('SUDO_USER', os.environ.get('USER'))
            if not user or user == 'root':
                try:
                    user = subprocess.check_output(
                        ["loginctl", "list-sessions"], text=True
                    ).split("\n")[1].split()[2]
                except:
                    user = "administrador"

            cmd = [
                'systemd-run',
                f'--machine={user}@.host',
                '--user',
                'notify-send',
                '-a', 'GuadaMint Store',
                '-i', 'system-software-update',
                'GuadaMint Store',
                f'Operación completada: {self.app_data["nombre"]}'
            ]
            subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
        else:
            self.switch.handler_block(self.handler_id)
            self.switch.set_active(not intended_state)
            self.switch.handler_unblock(self.handler_id)
            
            if error_msg: self.mostrar_error(error_msg)
            else: self.mostrar_error("Operación fallida. Revise los logs.")
        
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

        # --- CATÁLOGO DE APLICACIONES ---
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
    # Asignar el nombre del programa para que el Dock de Ubuntu lo identifique
    GLib.set_prgname("apps-guadamint.py")
    GLib.set_application_name(TITULO_APP)
    
    if os.path.exists(ICONO_APP):
        Gtk.Window.set_default_icon_from_file(ICONO_APP)

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
