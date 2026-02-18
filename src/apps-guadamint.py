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

# ==============================================================================
# CONFIGURACIÓN VISUAL
# ==============================================================================
ICONO_APP = "/usr/share/icons/guadamintuz.svg"
TITULO_APP = "Centro de Software GuadaMint"

# --- CATÁLOGO DE APLICACIONES ---
CATALOGO = [
    {
        "categoria": "Educación",
        "apps": [
            {"id": "geogebra", "nombre": "GeoGebra", "desc": "Matemáticas dinámicas", "icono": "geogebra"},
            {"id": "stellarium", "nombre": "Stellarium", "desc": "Planetario virtual", "icono": "stellarium"},
            {"id": "scratch", "nombre": "Scratch", "desc": "Aprender a programar", "icono": "scratch"},
            {"id": "gcompris-qt", "nombre": "GCompris", "desc": "Suite educativa infantil", "icono": "gcompris-qt"},
            {"id": "klavaro", "nombre": "Klavaro", "desc": "Tutor de mecanografía", "icono": "klavaro"},
        ]
    },
    {
        "categoria": "Creatividad",
        "apps": [
            {"id": "blender", "nombre": "Blender", "desc": "Modelado y animación 3D", "icono": "blender"},
            {"id": "inkscape", "nombre": "Inkscape", "desc": "Editor de gráficos vectoriales", "icono": "inkscape"},
            {"id": "audacity", "nombre": "Audacity", "desc": "Editor de audio", "icono": "audacity"},
            {"id": "obs-studio", "nombre": "OBS Studio", "desc": "Grabación y streaming", "icono": "com.obsproject.Studio"},
        ]
    },
    {
        "categoria": "Utilidades",
        "apps": [
            {"id": "vlc", "nombre": "VLC", "desc": "Reproductor multimedia", "icono": "vlc"},
            {"id": "anydesk", "nombre": "AnyDesk", "desc": "Control remoto", "icono": "anydesk"},
            {"id": "chromium", "nombre": "Chromium", "desc": "Navegador web libre", "icono": "chromium-browser"},
        ]
    }
]

# --- AUTO-UPDATE CONFIG ---
REPO_DIR = "/opt/guadamint"
REPO_URL = "https://github.com/aosucas499/guadamint.git"
REPO_BRANCH = "main"
SCRIPT_SRC = os.path.join(REPO_DIR, "src/apps-guadamint.py")
SCRIPT_BIN = "/usr/bin/apps-guadamint.py"
RUTA_SCRIPTS_REPO = "/opt/guadamint/scripts"

# ==============================================================================
# SEGURIDAD Y PERMISOS
# ==============================================================================
def es_administrador():
    """Comprueba si el usuario actual pertenece al grupo sudo o es root."""
    try:
        if os.geteuid() == 0: return True
        gid_list = os.getgroups()
        for gid in gid_list:
            if grp.getgrgid(gid).gr_name == 'sudo': return True
        return False
    except: return False

# ==============================================================================
# LÓGICA DE AUTO-ACTUALIZACIÓN
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
                    shutil.copy2(SCRIPT_SRC, SCRIPT_BIN)
                    os.chmod(SCRIPT_BIN, 0o755)
                    os.execv(sys.executable, ['python3'] + sys.argv)
    except: pass

# ==============================================================================
# INTERFAZ GRÁFICA (GTK)
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
        if Gtk.IconTheme.get_default().has_icon(app_data["icono"]):
            icon.set_from_icon_name(app_data["icono"], Gtk.IconSize.DIALOG)
        else:
            icon.set_from_icon_name("system-software-install", Gtk.IconSize.DIALOG)
        box.pack_start(icon, False, False, 0)

        vbox_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_name = Gtk.Label(xalign=0)
        lbl_name.set_markup(f"<b>{app_data['nombre']}</b>")
        lbl_desc = Gtk.Label(label=app_data['desc'], xalign=0)
        lbl_desc.get_style_context().add_class("dim-label")
        vbox_text.pack_start(lbl_name, True, True, 0)
        vbox_text.pack_start(lbl_desc, True, True, 0)
        box.pack_start(vbox_text, True, True, 0)

        self.switch = Gtk.Switch()
        self.switch.set_valign(Gtk.Align.CENTER)
        self.switch.connect("state-set", self.on_switch_activated)
        
        self.spinner = Gtk.Spinner()
        
        box.pack_end(self.switch, False, False, 0)
        box.pack_end(self.spinner, False, False, 10)
        
        self.add(box)
        threading.Thread(target=self.check_installed).start()

    def check_installed(self):
        res = subprocess.run(["dpkg", "-s", self.pkg_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        is_installed = (res.returncode == 0)
        GLib.idle_add(self.update_switch_state, is_installed)

    def update_switch_state(self, state):
        self.switch.set_active(state)
        return False

    def on_switch_activated(self, switch, state):
        self.switch.set_sensitive(False)
        self.spinner.start()
        action = "install" if state else "remove"
        threading.Thread(target=self.run_apt_action, args=(action,)).start()
        return True

    def run_apt_action(self, action):
        """Ejecuta la instalación/desinstalación de forma robusta."""
        print(f">>> Acción solicitada: {action} {self.pkg_name}")
        
        # 1. SCRIPT PERSONALIZADO
        if action == "install" and "script_install" in self.app_data:
            nombre_script = self.app_data["script_install"]
            ruta_script = os.path.join(RUTA_SCRIPTS_REPO, nombre_script)
            
            if os.path.exists(ruta_script):
                os.chmod(ruta_script, 0o755)
                # pkexec env ... para pasar entorno si fuera necesario, aunque scripts bash suelen ir bien
                cmd = ["pkexec", "/bin/bash", ruta_script]
            else:
                print(f"Error: Script {ruta_script} no encontrado.")
                GLib.idle_add(self.finish_action, False, True)
                return
        
        # 2. MODO APT-GET ESTÁNDAR (Mejorado)
        else:
            # Construimos el comando pkexec blindado:
            # - env DEBIAN_FRONTEND=noninteractive: Para que apt no pregunte
            # - /usr/bin/apt-get: Ruta absoluta
            # - Opciones Dpkg: Para forzar configuraciones por defecto
            cmd = [
                "pkexec", 
                "env", "DEBIAN_FRONTEND=noninteractive",
                "/usr/bin/apt-get", 
                action, 
                "-y", 
                "-o", "Dpkg::Options::=--force-confdef",
                "-o", "Dpkg::Options::=--force-confold",
                self.pkg_name
            ]

        try:
            # Ejecutamos y capturamos errores
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if res.returncode == 0:
                print(f">>> Éxito: {action} {self.pkg_name}")
                success = True
            else:
                print(f"!!! Error en {action}: {res.stderr}")
                # Si falla por el LOCK, avisamos diferente? (difícil desde aquí sin complicar)
                success = False
        except Exception as e:
            print(f"!!! Excepción python: {e}")
            success = False

        GLib.idle_add(self.finish_action, success, action == "install")

    def finish_action(self, success, intended_state):
        self.spinner.stop()
        self.switch.set_sensitive(True)
        if success:
            self.switch.set_state(intended_state)
            subprocess.Popen(['notify-send', '-i', 'system-software-update', 'GuadaMint Store', f'Operación completada: {self.app_data["nombre"]}'])
            threading.Thread(target=self.check_installed).start()
        else:
            self.switch.set_state(not intended_state)
            subprocess.Popen(['notify-send', '-u', 'critical', 'Error', f'No se pudo modificar {self.app_data["nombre"]}. ¿Hay otra actualización en curso?'])
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
        header.set_subtitle("Instalador de Software Escolar")
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

    try: auto_update()
    except: pass

    win = GuadaStoreWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
