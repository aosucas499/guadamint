#!/usr/bin/env python3
import os
import sys
import subprocess
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib

SERVICES = ["unattended-upgrades", "apt-daily.timer", "apt-daily-upgrade.timer"]

class UpdateSwitchApp:
    def __init__(self):
        # Crear el indicador para el panel superior de GNOME
        self.indicator = AppIndicator3.Indicator.new(
            "guadamint-autoupdate-switch",
            "software-update-available",
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        # Crear menú contextual
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
        
        # Consultar estado inicial
        self.check_status()

    def is_updates_enabled(self):
        """Comprueba si el servicio principal unattended-upgrades está habilitado."""
        try:
            res = subprocess.run(
                ["systemctl", "is-enabled", "unattended-upgrades"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
            )
            return res.stdout.strip() == "enabled"
        except Exception:
            return False

    def notify_user(self, title, message, icon="dialog-information"):
        """Envía notificación usando el bus de sesión de GNOME vía systemd-run."""
        try:
            user = os.environ.get('USER', 'administrador')
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
            # Acción: Desactivar y enmascarar servicios
            sys_cmd = "systemctl disable --now unattended-upgrades apt-daily.timer apt-daily-upgrade.timer && systemctl mask unattended-upgrades"
            msg_title = "Actualizaciones Desactivadas"
            msg_body = "Se han pausado las descargas automáticas del sistema."
            icon_name = "dialog-warning"
        else:
            # Acción: Desenmascarar y activar servicios
            sys_cmd = "systemctl unmask unattended-upgrades && systemctl enable --now unattended-upgrades apt-daily.timer apt-daily-upgrade.timer"
            msg_title = "Actualizaciones Activadas"
            msg_body = "El sistema volverá a buscar e instalar actualizaciones automáticamente."
            icon_name = "software-update-available"

        # Elevar privilegios mediante pkexec
        full_cmd = f"pkexec bash -c '{sys_cmd}'"
        res = subprocess.run(full_cmd, shell=True)

        if res.returncode == 0:
            self.notify_user(msg_title, msg_body, icon_name)
        
        # Actualizar interfaz tras el cambio
        GLib.idle_add(self.check_status)

if __name__ == "__main__":
    app = UpdateSwitchApp()
    Gtk.main()
