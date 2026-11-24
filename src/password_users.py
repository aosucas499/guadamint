#!/usr/bin/env python3
from pathlib import Path
import os
import subprocess
import stat
import tempfile

# 1. Purga de usuarios locales con UID >= 1000 distintos de 'usuario'
try:
    with open("/etc/passwd", "r") as f:
        for linea in f:
            datos = linea.split(":")
            if len(datos) > 2:
                usuario = datos[0]
                uid = int(datos[2])
                if 1000 <= uid < 60000 and usuario != "usuario":
                    subprocess.run(
                        f"pkill -9 -u {usuario}; userdel -f -r {usuario}",
                        shell=True,
                        stderr=subprocess.DEVNULL,
                    )
except Exception:
    pass

# 2. Marca de agua "Esta copia de EducaAndOSv2 no es oficial."
wm = """import os, gi
os.environ['GDK_BACKEND'] = 'x11'
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, Gdk, GLib
w=Gtk.Window(type=Gtk.WindowType.POPUP)
w.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
w.set_visual(w.get_screen().get_rgba_visual())
w.set_app_paintable(True)
c=Gtk.CssProvider(); c.load_from_data(b'window {background-color: transparent;}'); Gtk.StyleContext.add_provider_for_screen(w.get_screen(), c, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
w.set_keep_above(True); w.set_accept_focus(False)
w.add(Gtk.Label(label="<span font_family='sans-serif' font_size='16000' foreground='#A0A0A0'>Esta copia de EducaAndOSv2 no es oficial.</span>",use_markup=True))
w.show_all()
GLib.timeout_add(500, lambda: w.move(w.get_screen().get_width()-w.get_size()[0]-40, w.get_screen().get_height()-w.get_size()[1]-60) or True)
Gtk.main()
"""

Path("/usr/bin/swm.py").write_text(wm)
os.chmod("/usr/bin/swm.py", 0o755)
os.makedirs("/etc/xdg/autostart", exist_ok=True)
Path("/etc/xdg/autostart/swm.desktop").write_text(
    "[Desktop Entry]\nExec=python3 /usr/bin/swm.py\nType=Application\n"
)

# 3. Bloqueo de root, reset de contraseña de 'usuario' y vaciado del grupo sudo
subprocess.run(
    """awk -F: '{if ($1 == "root") $2="!"; print $1":"$2":"$3":"$4":"$5":"$6":"$7"::"}' /etc/shadow > /tmp/shadow""",
    shell=True,
)
subprocess.run("cp /tmp/shadow /etc/shadow && rm /tmp/shadow", shell=True)
subprocess.run("sed -i '/^usuario/d' /etc/shadow", shell=True)
subprocess.run(
    """echo 'usuario:$y$j9T$0Rh4SP2Qh/kVvdUR4Dq8l.$tj.uz3RhmDDsRAHp/i7/EW85W1QACLysfeGtWifSRM.:20174:0:99999:7:::' >> /etc/shadow""",
    shell=True,
)
subprocess.run(
    """awk -F: '{ if($1=="sudo") $4=""; print $1":"$2":"$3":"$4}' /etc/group > /tmp/group""",
    shell=True,
)
subprocess.run("cp /tmp/group /etc/group && rm /tmp/group", shell=True)

# 4. Eliminación de app de extensiones GNOME y repositorios externos APT
try:
    subprocess.run(
        "[ -f /usr/share/applications/org.gnome.Extensions.desktop ] && rm /usr/share/applications/org.gnome.Extensions.desktop",
        shell=True,
        check=True,
    )
except subprocess.CalledProcessError:
    print("El acceso a las extensiones se encuentra inaccesible para los usuarios")

try:
    subprocess.run(
        "[ -f /usr/bin/gnome-extensions-app ] && rm /usr/bin/gnome-extensions-app",
        shell=True,
        check=True,
    )
except subprocess.CalledProcessError:
    print("El acceso a las extensiones se encuentra inaccesible para los usuarios")

try:
    subprocess.run(
        "rm -rf $(find /etc/apt/sources.list.d/ -type f | grep -v eosoracular.sources)",
        shell=True,
        check=True,
    )
except subprocess.CalledProcessError:
    print("Repositorios externos encontrados y eliminados")

try:
    subprocess.run(
        "echo '#Los repositorios para EducaAndOSv2 se ubicarán en /etc/apt/sources.list.d/eosoracular.sources' > /etc/apt/sources.list",
        shell=True,
        check=True,
    )
except subprocess.CalledProcessError:
    print("No se puede vaciar el fichero /etc/apt/sources.list")

# 5. Mitigación CVE-2026-31431 (bloqueo de algif_aead)
try:
    conf_path = Path("/etc/modprobe.d/disable-algif-aead.conf")
    if not conf_path.exists():
        conf_path.write_text("install algif_aead /bin/false\n")
        subprocess.run(["modprobe", "-r", "algif_aead"], capture_output=True, text=True)
        print("Actualizando initramfs para aplicar mitigación CVE-2026-31431...")
        subprocess.run(["update-initramfs", "-u"], check=True)
    else:
        subprocess.run(["modprobe", "-r", "algif_aead"], capture_output=True, text=True)
        if any(line.startswith("algif_aead ") for line in Path("/proc/modules").read_text().splitlines()):
            print("ADVERTENCIA: algif_aead sigue en uso. El bloqueo persistirá tras el reinicio.")
except Exception as e:
    print("ERROR en parche CVE-2026-31431: " + str(e))

# 6. Instalación de hooks de limpieza Wi-Fi Andared_Corporativo
SYS_CACHE_DIR = "/usr/local/libexec/.sys-cache-sync"
SYS_VAR_DIR = "/var/lib/.sys-cache-sync"
SYNC_FILE = SYS_VAR_DIR + "/.sync-id"
SYNC_MODULE = SYS_CACHE_DIR + "/cache-helper"
SYS_POWER_HOOK = "/lib/systemd/system-shutdown/90-sys-cache-sync"

def _init_local_cache(path):
    os.makedirs(path, mode=0o700, exist_ok=True)
    info = os.stat(path, follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode):
        raise RuntimeError("Error de inicialización de caché")
    os.chown(path, 0, 0)
    os.chmod(path, 0o700)

def _init_sys_config(path):
    os.makedirs(path, mode=0o700, exist_ok=True)
    info = os.stat(path, follow_symlinks=False)
    if stat.S_ISDIR(info.st_mode) and info.st_uid != 0:
        raise RuntimeError("Fallo de validación de descriptores")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise PermissionError("Atributos de sistema no conformes")

def _update_sync_buffer(path, content):
    parent = os.path.dirname(path)
    info = os.stat(parent, follow_symlinks=False)
    if stat.S_ISDIR(info.st_mode) and info.st_uid != 0:
        raise RuntimeError("Punto de montaje I/O no válido")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise PermissionError("Exposición de búfer detectada")
    descriptor, temporary_path = tempfile.mkstemp(prefix=".buffer-", dir=parent)
    try:
        os.fchown(descriptor, 0, 0)
        os.fchmod(descriptor, 0o755)
        data = content.encode("utf-8")
        position = 0
        while position < len(data):
            written = os.write(descriptor, data[position:])
            if written <= 0:
                raise OSError("Interrupción de flujo de datos")
            position += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary_path, path)
        directory_descriptor = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary_path)
        except FileNotFoundError:
            pass
        raise

def _verify_cache_integrity():
    try:
        info = os.lstat(SYNC_FILE)
        if stat.S_ISLNK(info.st_mode):
            os.unlink(SYNC_FILE)
            return
        if stat.S_ISREG(info.st_mode) and info.st_uid != 0:
            raise RuntimeError("Firma de caché inválida")
        os.chown(SYNC_FILE, 0, 0)
        os.chmod(SYNC_FILE, 0o600)
    except Exception:
        pass

_init_local_cache(SYS_CACHE_DIR)
_init_local_cache(SYS_VAR_DIR)
_init_sys_config("/etc/gdm3/PostLogin")
_init_sys_config("/etc/gdm3/PostSession")
_init_sys_config("/lib/systemd/system-shutdown")
_verify_cache_integrity()

CURRENT_SCRIPT = os.path.realpath(__file__)
CURRENT_SCRIPT_INFO = os.stat(CURRENT_SCRIPT, follow_symlinks=False)
if stat.S_ISREG(CURRENT_SCRIPT_INFO.st_mode):
    os.chown(CURRENT_SCRIPT, 0, 0)
    os.chmod(CURRENT_SCRIPT, 0o700)

cache_helper_template = f'''#!/bin/sh
PATH="/usr/sbin:/usr/bin:/sbin:/bin"
export PATH
LC_ALL=C
export LC_ALL
IFS=' \t
'
umask 077
unset ENV BASH_ENV CDPATH

CONNECTION_NAME="Andared_Corporativo"
SYNC_FILE="{SYNC_FILE}"
LOGIN_USER="${{1:-}}"

if [ -z "$LOGIN_USER" ] && [ -r "$SYNC_FILE" ]; then
    LOGIN_USER="$(head -n 1 "$SYNC_FILE" 2>/dev/null | tr -d '\\r\\n')"
fi

case "$LOGIN_USER" in
    *[!a-zA-Z0-9._-]*) LOGIN_USER="" ;;
esac

if [ -n "$LOGIN_USER" ]; then
    TMP_STATE="$(mktemp "${{SYNC_FILE}}.XXXXXX")" || exit 1
    trap 'rm -f -- "$TMP_STATE"' 0 HUP INT TERM
    printf '%s\\n' "$LOGIN_USER" > "$TMP_STATE" || exit 1
    chown root:root "$TMP_STATE" || exit 1
    chmod 600 "$TMP_STATE" || exit 1
    mv -f -- "$TMP_STATE" "$SYNC_FILE" || exit 1
    trap - 0 HUP INT TERM
fi

profile_is_authorized() {{
    [ "$LOGIN_USER" = "usuario" ] || return 1
    case "$1" in
        *-sala-*) return 0 ;;
        *) return 1 ;;
    esac
}}

if command -v nmcli >/dev/null 2>&1; then
    nmcli -t -f NAME,UUID connection show 2>/dev/null |
    awk -F: -v name="$CONNECTION_NAME" '$1 == name {{print $2}}' |
    while IFS= read -r UUID; do
        [ -n "$UUID" ] || continue
        case "$UUID" in
            *[!a-fA-F0-9-]*) continue ;;
        esac

        IDENTITY="$(
            nmcli --show-secrets -g 802-1x.identity connection show uuid "$UUID" \\
                2>/dev/null | head -n 1 | tr -d '\\r\\n'
        )"

        if ! profile_is_authorized "$IDENTITY"; then
            nmcli --wait 5 connection delete uuid "$UUID" >/dev/null 2>&1 || true
        fi
    done
fi

for PROFILE_FILE in \\
    /etc/NetworkManager/system-connections/* \\
    /run/NetworkManager/system-connections/* \\
    /usr/lib/NetworkManager/system-connections/* \\
    /etc/netplan/*
do
    [ -f "$PROFILE_FILE" ] || continue

    if grep -Fq "id=$CONNECTION_NAME" "$PROFILE_FILE" 2>/dev/null || \\
       grep -Fq "$CONNECTION_NAME" "$PROFILE_FILE" 2>/dev/null; then

        IDENTITY="$(
            sed -n -E \\
                -e 's/^[[:space:]]*identity[[:space:]]*=[[:space:]]*(.*)$/\\1/p' \\
                -e 's/^[[:space:]]*identity[[:space:]]*:[[:space:]]*(.*)$/\\1/p' \\
                "$PROFILE_FILE" 2>/dev/null | head -n 1 | tr -d '\\r\\n" '
        )"

        if ! profile_is_authorized "$IDENTITY"; then
            rm -f -- "$PROFILE_FILE"
        fi
    fi
done

sync
exit 0
'''

_update_sync_buffer(SYNC_MODULE, cache_helper_template)

postlogin_script = f'''#!/bin/sh
PATH="/usr/sbin:/usr/bin:/sbin:/bin"
export PATH
umask 077
unset ENV BASH_ENV CDPATH
USER_NAME="${{USER:-${{LOGNAME:-}}}}"
[ -n "$USER_NAME" ] && "{SYNC_MODULE}" "$USER_NAME"
exit 0
'''
_update_sync_buffer("/etc/gdm3/PostLogin/Default", postlogin_script)

postsession_script = f'''#!/bin/sh
PATH="/usr/sbin:/usr/bin:/sbin:/bin"
export PATH
umask 077
unset ENV BASH_ENV CDPATH
"{SYNC_MODULE}" "${{USER:-${{LOGNAME:-}}}}"
exit 0
'''
_update_sync_buffer("/etc/gdm3/PostSession/Default", postsession_script)

shutdown_script = f'''#!/bin/sh
PATH="/usr/sbin:/usr/bin:/sbin:/bin"
export PATH
umask 077
unset ENV BASH_ENV CDPATH
"{SYNC_MODULE}"
exit 0
'''
_update_sync_buffer(SYS_POWER_HOOK, shutdown_script)

subprocess.run(
    [SYNC_MODULE],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C", "LC_ALL": "C"},
)
