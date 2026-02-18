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

# ==============================================================================
# CONFIGURACIÓN VISUAL
# ==============================================================================
ICONO_APP = "/usr/share/icons/guadamintuz.svg"
TITULO_APP = "Centro de Software GuadaMint"

# --- CATÁLOGO DE APLICACIONES ---
# Nota: He quitado 'anydesk' porque no está en los repositorios oficiales y da error.
# Solo dejamos paquetes que seguro existen en Linux Mint / Ubuntu.
CATALOGO = [
    {
        "categoria": "Educación",
        "apps": [
            {"id": "geogebra", "nombre": "GeoGebra", "desc": "Matemáticas dinámicas", "icono": "geogebra"},
            {"id": "stellarium", "nombre": "Stellarium", "desc": "Planetario virtual", "icono": "stellarium"},
            {"id": "scratch", "nombre": "Scratch", "desc": "Aprender a programar", "icono": "scratch"},
            {"id": "gcompris-qt", "nombre": "GCompris", "desc": "Suite educativa infantil", "icono": "gcompris-qt"},
            {"id": "klavaro", "nombre": "Klavaro", "desc": "Tutor de mecanografía", "icono": "klavaro"},
            {"id": "tuxpaint", "nombre": "Tux Paint", "desc": "Dibujo para niños", "icono": "tuxpaint"},
        ]
    },
    {
        "categoria": "Creatividad",
        "apps": [
            {"id": "blender", "nombre": "Blender", "desc": "Modelado y animación 3D", "icono": "blender"},
            {"id": "inkscape", "nombre": "Inkscape", "desc": "Editor de gráficos vectoriales", "icono": "inkscape"},
            {"id": "audacity", "nombre": "Audacity", "desc": "Editor de audio", "icono": "audacity"},
            {"id": "obs-studio", "nombre": "OBS Studio", "desc": "Grabación y streaming", "icono": "obs"},
        ]
    },
    {
        "categoria": "Utilidades",
        "apps": [
            {"id": "vlc", "nombre": "VLC", "desc": "Reproductor multimedia", "icono": "vlc"},
            {"id": "chromium", "nombre": "Chromium", "desc": "Navegador web libre", "icono": "chromium-browser"},
            {"id": "gnome-network-displays", "nombre": "Pantallas Inalámbricas", "desc": "Conectar a proyectores Wifi", "icono": "preferences-desktop-display"},
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
            nombre = grp.getgrgid(gid).gr_name
            if nombre == 'sudo' or nombre == 'admin': return True
        return False
    except: return False

def hay_bloqueo_apt():
    """Comprueba si apt/dpkg están siendo usados por otro proceso."""
    locks = ["/var/lib/dpkg/lock-frontend", "/var/lib/dpkg/lock"]
    for lock in locks:
        # Fuser devuelve 0 si el archivo está en uso
        if subprocess.run(["fuser", lock], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return True
    return False

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
        
        # Icono
        icon = Gtk.Image()
        icon.set_pixel_size(48)
        
        # Lógica de iconos robusta
        icono_nombre = app_data["icono"]
        if os.path.isabs(icono_nombre) and os.path.exists(icono_nombre):
             icon.set_from_file(icono_nombre)
        elif Gtk.IconTheme.get_default().has_icon(icono_nombre):
            icon.set_from_icon_name(icono_nombre, Gtk.IconSize.DIALOG)
        else:
            icon.set_from_icon_name("system-software-install", Gtk.IconSize.DIALOG)
            
        box.pack_start(icon, False, False, 0)

        # Texto
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

        # Controles
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
        # Bloquear UI
        self.switch.set_sensitive(False)
        self.spinner.start()
        
        # Comprobar bloqueo de APT antes de pedir contraseña
        if hay_bloqueo_apt():
            self.mostrar_error("El sistema de actualizaciones está ocupado.\nEspere a que termine el icono de la barra.")
            self.spinner.stop()
            self.switch.set_sensitive(True)
            return True # Cancelar cambio visual

        action = "install" if state else "remove"
        threading.Thread(target=self.run_apt_action, args=(action,)).start()
        return True

    def mostrar_error(self, mensaje):
        dialog = Gtk.MessageDialog(
            parent=self.ventana_padre,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error"
        )
        dialog.format_secondary_text(mensaje)
        dialog.run()
        dialog.destroy()

    def run_apt_action(self, action):
        print(f">>> Acción: {action} {self.pkg_name}")
        error_msg = ""
        success = False
        
        # 1. SCRIPT PERSONALIZADO
        if action == "install" and "script_install" in self.app_data:
            nombre_script = self.app_data["script_install"]
            ruta_script = os.path.join(RUTA_SCRIPTS_REPO, nombre_script)
            
            if os.path.exists(ruta_script):
                os.chmod(ruta_script, 0o755)
                # pkexec pide la contraseña
                cmd = ["pkexec", "/bin/bash", ruta_script]
                try:
                    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if res.returncode == 0:
                        success = True
                    else:
                        error_msg = f"Error del script:\n{res.stderr}"
                except Exception as e:
                    error_msg = f"Excepción script: {e}"
            else:
                error_msg = f"No se encuentra el script:\n{nombre_script}\n(¿Está subido a GitHub en la carpeta scripts?)"
        
        # 2. MODO APT-GET ESTÁNDAR
        else:
            # Comando blindado
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
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0:
                    success = True
                else:
                    # Analizar error común
                    if "Unable to locate package" in res.stderr:
                        error_msg = f"No se encuentra el paquete '{self.pkg_name}' en los repositorios."
                    elif "Could not get lock" in res.stderr:
                        error_msg = "El sistema de actualizaciones está ocupado. Inténtelo de nuevo."
                    else:
                        error_msg = f"Error de APT:\n{res.stderr}"
            except Exception as e:
                error_msg = f"Excepción interna: {e}"

        GLib.idle_add(self.finish_action, success, action == "install", error_msg)

    def finish_action(self, success, intended_state, error_msg=""):
        self.spinner.stop()
        self.switch.set_sensitive(True)
        
        if success:
            self.switch.set_state(intended_state)
            subprocess.Popen(['notify-send', '-i', 'system-software-update', 'GuadaMint Store', f'Operación completada: {self.app_data["nombre"]}'])
            threading.Thread(target=self.check_installed).start()
        else:
            # Revertir interruptor
            self.switch.set_state(not intended_state)
            # Mostrar ventana de error explicativa
            if error_msg:
                self.mostrar_error(error_msg)
            else:
                self.mostrar_error("La operación falló o fue cancelada.")
        return False

class GuadaStoreWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=TITULO_APP)
        self.set_default_size(600, 700)
        self.set_border_width(0)
        
        if os.path.exists(ICONO_APP):
            self.set_icon_from_file(ICONO_APP)

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
