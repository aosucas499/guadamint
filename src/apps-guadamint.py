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
import socket
import urllib.request

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
ICONO_APP = "/usr/share/icons/guadamintuz.svg"
TITULO_APP = "Centro de Software GuadaMint"

CON_ANDARED_PERMANENTE = "Andared_Corporativo_Permanente"
SSID_ANDARED = "Andared_Corporativo"

# Configuración de Logs
if os.geteuid() == 0:
    LOG_FILE = "/var/log/guadamint/tienda.log"
else:
    LOG_FILE = f"/tmp/guadamint-tienda-{os.getuid()}.log"

# Asegurar directorio de logs si somos root
if os.geteuid() == 0 and not os.path.exists(os.path.dirname(LOG_FILE)):
    try: os.makedirs(os.path.dirname(LOG_FILE))
    except: pass

# --- AUTO-UPDATE CONFIG Y RUTAS ---
REPO_DIR = "/opt/guadamint"
REPO_URL = "https://github.com/aosucas499/guadamint.git"
REPO_BRANCH = "testing"
SCRIPT_SRC = os.path.join(REPO_DIR, "src/apps-guadamint.py")
SCRIPT_BIN = "/usr/bin/apps-guadamint.py"
RUTA_SCRIPTS_REPO = os.path.join(REPO_DIR, "src/scripts")
RUTA_IMAGES_REPO = os.path.join(REPO_DIR, "images")

CATALOGO = [
    {
        "categoria": "Aplicaciones",
        "apps": [
            {
                "id": "openboard", 
                "nombre": "Openboard", 
                "desc": "Aplicación de pizarra interactiva", 
                "icono": "input-tablet"
            },
        ]
    },
    {
        "categoria": "Scripts y Configuraciones",
        "apps": [
            {
                "id": "andared-permanente",
                "nombre": "Andared corporativo permanente",
                "desc": "Configura permanentemente Andared_Corporativo para cuentas locales sin borrarse.",
                "icono": "network-wireless",
                "tipo": "wifi_sala"
            },
            {
                "id": "ubuntu-repos", 
                "nombre": "Repositorios Temporales de Ubuntu", 
                "desc": "Permite dependencias oficiales extra en RAM (/tmp). Se borran al reiniciar.", 
                "icono": os.path.join(RUTA_IMAGES_REPO, "ubuntu.svg"), 
                "script_install": "toggle-ubuntu-repos.sh"
            },
            {
                "id": "smart-product-drivers", 
                "nombre": "Drivers SMART Board", 
                "desc": "Controladores para pizarras interactivas", 
                "icono": os.path.join(RUTA_IMAGES_REPO, "smart.png"), 
                "script_install": "instalar_smartboard.sh"
            },
            {
                "id": "flatpak", 
                "nombre": "Soporte Flatpak y Flathub", 
                "desc": "Instala el motor Flatpak y lo integra automáticamente en el Centro de Software", 
                "icono": os.path.join(RUTA_IMAGES_REPO, "flatpak.svg"), 
                "script_install": "toggle-flatpak.sh"
            },
        ]
    }
]

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

def comprobar_conexion():
    """Comprueba si hay internet con socket y muestra un aviso GTK si falla."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        dialog = Gtk.MessageDialog(
            parent=None,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK,
            text="Sin conexión a Internet"
        )
        dialog.format_secondary_text(
            "No se ha detectado conexión a Internet.\n"
            "Si necesitas configurar la red del aula, activa la opción 'Andared corporativo permanente'."
        )
        if os.path.exists(ICONO_APP):
            dialog.set_icon_from_file(ICONO_APP)
        dialog.run()
        dialog.destroy()
        return False

# ==============================================================================
# GESTIÓN DE WI-FI ANDARED CORPORATIVO PERMANENTE
# ==============================================================================
def perfil_andared_permanente_existe():
    res = subprocess.run(
        ["nmcli", "-g", "NAME", "connection", "show", CON_ANDARED_PERMANENTE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return res.returncode == 0

def pedir_credenciales_andared(parent_window):
    """Muestra un cuadro de diálogo GTK 3 para pedir usuario de sala y contraseña."""
    dialog = Gtk.Dialog(
        title="Andared corporativo permanente",
        transient_for=parent_window,
        flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
    )
    dialog.set_default_size(430, 230)
    dialog.set_resizable(False)
    dialog.set_border_width(14)
    if os.path.exists(ICONO_APP):
        dialog.set_icon_from_file(ICONO_APP)

    dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
    btn_ok = dialog.add_button("Guardar y conectar", Gtk.ResponseType.OK)
    btn_ok.get_style_context().add_class("suggested-action")
    btn_ok.set_can_default(True)
    btn_ok.grab_default()

    area = dialog.get_content_area()
    area.set_spacing(12)

    lbl_titulo = Gtk.Label(xalign=0)
    lbl_titulo.set_markup(
        "<b>Andared corporativo permanente</b>\n"
        "<small>Introduce el usuario de sala y su contraseña. La conexión se guardará\n"
        "en NetworkManager disponible para todas las cuentas locales sin borrarse.</small>"
    )
    lbl_titulo.set_line_wrap(True)
    area.pack_start(lbl_titulo, False, False, 0)

    grid = Gtk.Grid(column_spacing=12, row_spacing=10)
    area.pack_start(grid, True, True, 4)

    lbl_user = Gtk.Label(label="Usuario de sala:", xalign=0)
    entry_user = Gtk.Entry()
    entry_user.set_placeholder_text("Ej. 2900XXXX-sala-01")
    entry_user.set_hexpand(True)
    entry_user.set_activates_default(True)
    grid.attach(lbl_user, 0, 0, 1, 1)
    grid.attach(entry_user, 1, 0, 1, 1)

    lbl_pass = Gtk.Label(label="Contraseña:", xalign=0)
    entry_pass = Gtk.Entry()
    entry_pass.set_visibility(False)
    entry_pass.set_hexpand(True)
    entry_pass.set_activates_default(True)
    grid.attach(lbl_pass, 0, 1, 1, 1)
    grid.attach(entry_pass, 1, 1, 1, 1)

    chk_ver = Gtk.CheckButton(label="Mostrar contraseña")
    chk_ver.connect("toggled", lambda w: entry_pass.set_visibility(w.get_active()))
    grid.attach(chk_ver, 1, 2, 1, 1)

    # Precargar identidad si ya existía una configuración previa
    res_id = subprocess.run(
        ["nmcli", "-g", "802-1x.identity", "connection", "show", CON_ANDARED_PERMANENTE],
        capture_output=True, text=True
    )
    if res_id.returncode == 0 and res_id.stdout.strip():
        entry_user.set_text(res_id.stdout.strip())

    dialog.show_all()

    while True:
        resp = dialog.run()
        if resp != Gtk.ResponseType.OK:
            dialog.destroy()
            return None

        usuario = entry_user.get_text().strip()
        password = entry_pass.get_text().strip()
        if usuario and password:
            dialog.destroy()
            return (usuario, password)

        aviso = Gtk.MessageDialog(
            parent=dialog,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK,
            text="Campos incompletos"
        )
        aviso.format_secondary_text("Debes introducir tanto el usuario de sala como la contraseña.")
        aviso.run()
        aviso.destroy()

def aplicar_andared_permanente(usuario, password):
    """Crea el perfil permanente en /etc/NetworkManager/system-connections/ y conecta."""
    subprocess.run(["nmcli", "radio", "wifi", "on"], capture_output=True)

    res_dev = subprocess.run(
        ["nmcli", "-t", "-f", "DEVICE,TYPE", "device"],
        capture_output=True, text=True
    )
    interfaz = next(
        (l.split(":")[0] for l in res_dev.stdout.splitlines() if l.endswith(":wifi")),
        ""
    )
    if not interfaz:
        return False, "No se ha detectado ninguna interfaz Wi-Fi activa en el equipo."

    subprocess.run(["nmcli", "connection", "delete", CON_ANDARED_PERMANENTE], capture_output=True)

    res_add = subprocess.run(
        [
            "nmcli", "connection", "add",
            "type", "wifi",
            "ifname", interfaz,
            "con-name", CON_ANDARED_PERMANENTE,
            "ssid", SSID_ANDARED,
        ],
        capture_output=True, text=True
    )
    if res_add.returncode != 0:
        return False, f"Error creando perfil en NetworkManager: {res_add.stderr.strip()}"

    res_mod = subprocess.run(
        [
            "nmcli", "connection", "modify", CON_ANDARED_PERMANENTE,
            "wifi-sec.key-mgmt", "wpa-eap",
            "802-1x.eap", "ttls",
            "802-1x.phase2-auth", "gtc",
            "802-1x.identity", usuario,
            "802-1x.password", password,
            "802-1x.ca-cert", "",
            "802-1x.system-ca-certs", "no",
            "802-1x.password-flags", "0",
            "connection.permissions", "",
            "connection.autoconnect", "yes",
            "connection.autoconnect-priority", "-10",
        ],
        capture_output=True, text=True
    )
    if res_mod.returncode != 0:
        return False, f"Error aplicando parámetros 802.1X: {res_mod.stderr.strip()}"

    ruta_nm = f"/etc/NetworkManager/system-connections/{CON_ANDARED_PERMANENTE}.nmconnection"
    if os.path.exists(ruta_nm):
        os.chmod(ruta_nm, 0o600)

    res_up = subprocess.run(
        ["nmcli", "--wait", "15", "connection", "up", CON_ANDARED_PERMANENTE],
        capture_output=True, text=True
    )
    if res_up.returncode != 0:
        err = res_up.stderr.strip() or "Verifica usuario, contraseña o cobertura Wi-Fi."
        return False, f"Perfil guardado en el sistema, pero falló la conexión:\n{err}"

    return True, ""

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
        icon.set_size_request(48, 48)
        icon.set_pixel_size(48)
        
        icono_nombre = app_data["icono"]
        cargado = False
        
        if os.path.exists(icono_nombre):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icono_nombre, 48, 48, True)
                icon.set_from_pixbuf(pixbuf)
                cargado = True
            except Exception as e:
                log(f"Error cargando archivo {icono_nombre}: {e}")

        if not cargado:
            theme = Gtk.IconTheme.get_default()
            if theme.has_icon(icono_nombre):
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
            if self.app_data.get("tipo") == "wifi_sala":
                is_installed = perfil_andared_permanente_existe()
            elif "script_install" in self.app_data:
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
        if self.app_data.get("tipo") == "wifi_sala":
            if state:
                credenciales = pedir_credenciales_andared(self.ventana_padre)
                if not credenciales:
                    self.update_switch_state(False)
                    return True
                self.switch.set_sensitive(False)
                self.spinner.start()
                self.switch.set_state(True)
                threading.Thread(
                    target=self.run_wifi_sala_action,
                    args=(True, credenciales[0], credenciales[1])
                ).start()
            else:
                self.switch.set_sensitive(False)
                self.spinner.start()
                self.switch.set_state(False)
                threading.Thread(
                    target=self.run_wifi_sala_action,
                    args=(False, "", "")
                ).start()
            return True

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

    def run_wifi_sala_action(self, activar, usuario, password):
        log(f"Iniciando configuración Andared corporativo permanente (activar={activar})...")
        if activar:
            ok, err = aplicar_andared_permanente(usuario, password)
            if ok:
                log(f"Perfil {CON_ANDARED_PERMANENTE} configurado y conectado correctamente.")
            else:
                log(f"Aviso configurando {CON_ANDARED_PERMANENTE}: {err}")
            estado_final = perfil_andared_permanente_existe()
            GLib.idle_add(self.finish_wifi_action, ok, estado_final, err)
        else:
            subprocess.run(["nmcli", "connection", "delete", CON_ANDARED_PERMANENTE], capture_output=True)
            log(f"Perfil {CON_ANDARED_PERMANENTE} eliminado.")
            GLib.idle_add(self.finish_wifi_action, True, False, "")

    def finish_wifi_action(self, ok, estado_real, error_msg=""):
        self.spinner.stop()
        self.switch.set_sensitive(True)
        self.update_switch_state(estado_real)

        if ok:
            self.notificar_escritorio(f"Operación completada: {self.app_data['nombre']}")
        elif error_msg:
            self.mostrar_error(error_msg)
        return False

    def mostrar_error(self, mensaje):
        dialog = Gtk.MessageDialog(parent=self.ventana_padre, flags=Gtk.DialogFlags.MODAL, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text="Aviso")
        dialog.format_secondary_text(mensaje)
        dialog.run()
        dialog.destroy()

    def notificar_escritorio(self, texto):
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
            texto
        ]
        subprocess.Popen(cmd, stderr=subprocess.DEVNULL)

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
            self.notificar_escritorio(f'Operación completada: {self.app_data["nombre"]}')
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

    # Avisar si no hay red, pero permitir abrir la tienda para poder configurar la Wi-Fi
    hay_red = comprobar_conexion()
        
    elevar_a_root()
    if hay_red:
        try: auto_update()
        except: pass
    
    win = GuadaStoreWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
