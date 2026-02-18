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
CATALOGO = [
    {
        "categoria": "Educación Extra",
        "apps": [
            {"id": "geogebra", "nombre": "GeoGebra", "desc": "Matemáticas dinámicas complejas", "icono": "geogebra"},
            {"id": "fritzing", "nombre": "Fritzing", "desc": "Diseño de circuitos electrónicos", "icono": "fritzing"},
            {"id": "arduino", "nombre": "Arduino IDE", "desc": "Programación de placas Arduino", "icono": "arduino"},
            {"id": "celestia", "nombre": "Celestia", "desc": "Simulador espacial 3D", "icono": "celestia"},
        ]
    },
    {
        "categoria": "Creatividad Avanzada",
        "apps": [
            {"id": "blender", "nombre": "Blender", "desc": "Modelado y animación 3D profesional", "icono": "blender"},
            {"id": "inkscape", "nombre": "Inkscape", "desc": "Diseño vectorial (Illustrator libre)", "icono": "inkscape"},
            {"id": "kdenlive", "nombre": "Kdenlive", "desc": "Editor de vídeo profesional", "icono": "kdenlive"},
            {"id": "obs-studio", "nombre": "OBS Studio", "desc": "Grabación y streaming de pantalla", "icono": "obs"},
            {"id": "lmms", "nombre": "LMMS", "desc": "Producción musical (DAW)", "icono": "lmms"},
        ]
    },
    {
        "categoria": "Utilidades y Navegadores",
        "apps": [
            {"id": "vlc", "nombre": "VLC", "desc": "El reproductor que lo abre todo", "icono": "vlc"},
            {"id": "chromium-browser", "nombre": "Chromium", "desc": "Navegador web libre (Base Chrome)", "icono": "chromium-browser"},
            {"id": "gnome-boxes", "nombre": "Cajas (Boxes)", "desc": "Máquinas virtuales sencillas", "icono": "gnome-boxes"},
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
RUTA_SCRIPTS_REPO = "/opt/guadamint/scripts"

# ==============================================================================
# SEGURIDAD Y PERMISOS (AUTO-ELEVACIÓN)
# ==============================================================================
def elevar_a_root():
    """Si no somos root, nos reiniciamos usando pkexec para pedir pass una vez."""
    if os.geteuid() != 0:
        # Buscamos el usuario real para conservar su display
        usuario_real = os.environ.get('USER', 'usuario')
        
        # Preparamos el entorno para que la ventana gráfica se muestre siendo root
        env = os.environ.copy()
        
        # Intentamos recuperar la XAUTHORITY del usuario si no está definida
        if 'XAUTHORITY' not in env:
            possible_auth = f"/home/{usuario_real}/.Xauthority"
            if os.path.exists(possible_auth):
                env['XAUTHORITY'] = possible_auth
        
        # Comando para re-lanzarnos a nosotros mismos
        args = ['pkexec', 'env', f'DISPLAY={env.get("DISPLAY", ":0")}', 
                f'XAUTHORITY={env.get("XAUTHORITY", "")}', 
                sys.executable] + sys.argv
        
        try:
            # Reemplazamos el proceso actual con el nuevo elevado
            os.execvpe('pkexec', args, env)
        except Exception as e:
            print(f"Error al elevar privilegios: {e}")
            sys.exit(1)

def hay_bloqueo_apt():
    """Comprueba si apt/dpkg están siendo usados por otro proceso."""
    locks = ["/var/lib/dpkg/lock-frontend", "/var/lib/dpkg/lock"]
    for lock in locks:
        if subprocess.run(["fuser", lock], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return True
    return False

# ==============================================================================
# LÓGICA DE AUTO-ACTUALIZACIÓN
# ==============================================================================
def auto_update():
    # Como ya somos root, podemos escribir en /usr/bin sin problemas
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
                    os.execv(sys.executable, [sys.executable] + sys.argv)
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
        self.handler_id = self.switch.connect("state-set", self.on_switch_activated)
        
        self.spinner = Gtk.Spinner()
        
        box.pack_end(self.switch, False, False, 0)
        box.pack_end(self.spinner, False, False, 10)
        
        self.add(box)
        threading.Thread(target=self.check_installed).start()

    def check_installed(self):
        # Comprobamos estado real
        res = subprocess.run(["dpkg", "-s", self.pkg_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        is_installed = (res.returncode == 0)
        GLib.idle_add(self.update_switch_state, is_installed)

    def update_switch_state(self, state):
        # Actualizamos sin disparar eventos
        self.switch.handler_block(self.handler_id)
        self.switch.set_active(state)
        self.switch.handler_unblock(self.handler_id)
        return False

    def on_switch_activated(self, switch, state):
        self.switch.set_sensitive(False)
        self.spinner.start()
        
        if hay_bloqueo_apt():
            self.mostrar_error("El sistema de actualizaciones está ocupado.\n\nEspere unos minutos.")
            self.spinner.stop()
            self.switch.set_sensitive(True)
            # Revertir visualmente
            self.switch.handler_block(self.handler_id)
            self.switch.set_active(not state)
            self.switch.handler_unblock(self.handler_id)
            return True 

        action = "install" if state else "remove"
        threading.Thread(target=self.run_apt_action, args=(action,)).start()
        return True

    def mostrar_error(self, mensaje):
        dialog = Gtk.MessageDialog(
            parent=self.ventana_padre,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Aviso"
        )
        dialog.format_secondary_text(mensaje)
        dialog.run()
        dialog.destroy()

    def run_apt_action(self, action):
        print(f">>> Acción (ROOT): {action} {self.pkg_name}")
        error_msg = ""
        success = False
        
        # 1. SCRIPT PERSONALIZADO
        if action == "install" and "script_install" in self.app_data:
            nombre_script = self.app_data["script_install"]
            ruta_script = os.path.join(RUTA_SCRIPTS_REPO, nombre_script)
            
            if os.path.exists(ruta_script):
                os.chmod(ruta_script, 0o755)
                # Ejecutamos directo (ya somos root)
                cmd = ["/bin/bash", ruta_script]
                try:
                    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if res.returncode == 0: success = True
                    else: error_msg = f"Error del script:\n{res.stderr}"
                except Exception as e: error_msg = f"Excepción script: {e}"
            else:
                error_msg = f"Script no encontrado: {nombre_script}"
        
        # 2. MODO APT-GET ESTÁNDAR
        else:
            # Ejecutamos directo sin pkexec
            cmd = [
                "env", "DEBIAN_FRONTEND=noninteractive",
                "/usr/bin/apt-get", 
                action, "-y", 
                "-o", "Dpkg::Options::=--force-confdef",
                "-o", "Dpkg::Options::=--force-confold",
                self.pkg_name
            ]
            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0: success = True
                else:
                    if "Unable to locate" in res.stderr: error_msg = f"Paquete no encontrado: {self.pkg_name}"
                    elif "lock" in res.stderr: error_msg = "Conflicto de bloqueo APT."
                    else: error_msg = f"Error APT: {res.stderr}"
            except Exception as e: error_msg = f"Excepción: {e}"

        GLib.idle_add(self.finish_action, success, action == "install", error_msg)

    def finish_action(self, success, intended_state, error_msg=""):
        self.spinner.stop()
        self.switch.set_sensitive(True)
        
        self.switch.handler_block(self.handler_id)
        if success:
            # Forzamos el estado visual al que queríamos
            self.switch.set_active(intended_state)
            
            # Notificación al usuario real (no a root)
            user = os.environ.get('SUDO_USER', os.environ.get('USER'))
            subprocess.Popen(['sudo', '-u', user, 'notify-send', 
                            '-i', 'system-software-update', 
                            'GuadaMint Store', 
                            f'Operación completada: {self.app_data["nombre"]}'])
        else:
            # Revertimos al estado contrario
            self.switch.set_active(not intended_state)
            if error_msg: self.mostrar_error(error_msg)
            else: self.mostrar_error("Operación fallida.")
        
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
    # 1. AUTO-ELEVACIÓN A ROOT (Pide contraseña gráfica UNA VEZ)
    elevar_a_root()

    # 2. Auto-Update (Ahora sí puede escribir en /usr/bin)
    try: auto_update()
    except: pass

    # 3. Iniciar Interfaz
    win = GuadaStoreWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
