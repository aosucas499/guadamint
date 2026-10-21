#!/usr/bin/env python3
import os
import sys
import subprocess
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib

EXEC_PATH = "/usr/local/bin/educaandos-update"
BACKUP_PATH = "/usr/local/bin/educaandos-update.backup"

class UpdateSwitchApp:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            "guadamint-autoupdate-switch",
            "security-high",
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        self.menu = Gtk.Menu()
        
        self.item_status = Gtk.MenuItem(label="Estado: Comprobando...")
        self.item_status.set_sensitive(False)
        self.menu.append(self.item_status)
        
        self.menu.append(Gtk.SeparatorMenuItem())
        
        self.item_toggle = Gtk.MenuItem(label="Cambiando estado...")
        self.item_toggle.connect("activate", self.on_toggle_clicked)
        self.menu.append(self.item_toggle)
        
        self.menu.append(Gtk.SeparatorMenuItem())
        
        item_exit = Gtk.MenuItem(label="Salir")
        item_exit.connect("activate", Gtk.main_quit)
        self.menu.append(item_exit)
        
        self.menu.show_all()
        self.indicator.set_menu(self.menu)
        
        # Comprobar el estado real del archivo nada más arrancar
        self.check_status()

    def is_updates_enabled(self):
        """
        Detección del estado real por existencia del binario original:
        - Si existe /usr/local/bin/educaandos-update -> ACTIVADAS (True)
        - Si existe /usr/local/bin/educaandos-update.backup -> DESACTIVADAS (False)
        """
        if os.path.exists(BACKUP_PATH) or os.path.islink(BACKUP_PATH):
            return False
        return os.path.exists(EXEC_PATH) or os.path.islink(EXEC_PATH)

    def notify_user(self, title, message, icon="dialog-information"):
        try:
            user = os.environ.get('SUDO_USER') or os.environ.get('USER', 'administrador')
            cmd = [
                'systemd-run',
                f'--machine={user}@.host',
                '--user',
                'notify-send',
                '-a', 'GuadaMint Updates',
                '-i', icon,
                title,
                message
            ]
            subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def check_status(self):
        enabled = self.is_updates_enabled()
        if enabled:
            self.item_status.set_label("Actualizaciones: ACTIVADAS")
            self.item_toggle.set_label("Desactivar Actualizaciones Automáticas")
            self.indicator.set_icon_full("security-high", "Actualizaciones activadas")
        else:
            self.item_status.set_label("Actualizaciones: DESACTIVADAS")
            self.item_toggle.set_label("Activar Actualizaciones Automáticas")
            self.indicator.set_icon_full("process-stop", "Actualizaciones desactivadas")
        return False

    def on_toggle_clicked(self, widget):
        current_state = self.is_updates_enabled()
        
        if current_state:
            # DESACTIVAR: Matar procesos activos y renombrar archivo a .backup
            sys_cmd = f"pkill -9 -f sar-educaandos- ; pkill -9 -f guadamint-update ; mv -f {EXEC_PATH} {BACKUP_PATH}"
            msg_title = "Actualizaciones Desactivadas"
            msg_body = "Se ha detenido el servicio y renombrado el ejecutable a .backup."
            icon_name = "process-stop"
        else:
            # ACTIVAR: Restaurar ejecutable desde .backup
            sys_cmd = f"mv -f {BACKUP_PATH} {EXEC_PATH}"
            msg_title = "Actualizaciones Activadas"
            msg_body = "Se ha restaurado el ejecutable original de actualizaciones."
            icon_name = "security-high"

        try:
            # Ejecución con elevación gráfica directa
            res = subprocess.run(["pkexec", "sh", "-c", sys_cmd], capture_output=True, text=True)
            if res.returncode == 0:
                self.notify_user(msg_title, msg_body, icon_name)
            else:
                print(f"pkexec cancelado o denegado: {res.stderr}")
        except Exception as e:
            print(f"Error en ejecución: {e}")

        # Actualizar la interfaz basándose en la presencia del archivo
        GLib.idle_add(self.check_status)

if __name__ == "__main__":
    app = UpdateSwitchApp()
    Gtk.main()
