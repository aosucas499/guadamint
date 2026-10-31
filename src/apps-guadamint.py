#!/usr/bin/env python3
import os
import sys
import subprocess
import threading
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

# Identificador de proceso para la barra de tareas / escritorio
GLib.set_prgname("apps-guadamint")

# ==========================================
# CATÁLOGO DE APLICACIONES Y SCRIPTS
# ==========================================
CATALOGO = [
    # --- APLICACIONES ---
    {
        "id": "gimp",
        "nombre": "GIMP",
        "descripcion": "Editor de imágenes y retoque fotográfico avanzado.",
        "categoria": "Aplicaciones",
        "tipo": "apt",
        "paquete": "gimp",
        "icono": "/usr/share/icons/hicolor/48x48/apps/gimp.png"
    },
    {
        "id": "vlc",
        "nombre": "VLC Media Player",
        "descripcion": "Reproductor multimedia multiformato.",
        "categoria": "Aplicaciones",
        "tipo": "apt",
        "paquete": "vlc",
        "icono": "/usr/share/icons/hicolor/48x48/apps/vlc.png"
    },
    {
        "id": "libreoffice",
        "nombre": "LibreOffice",
        "descripcion": "Suite ofimática para procesado de textos, hojas de cálculo y presentaciones.",
        "categoria": "Aplicaciones",
        "tipo": "apt",
        "paquete": "libreoffice",
        "icono": "/usr/share/icons/hicolor/48x48/apps/libreoffice-main.png"
    },
    {
        "id": "inkscape",
        "nombre": "Inkscape",
        "descripcion": "Editor de gráficos vectoriales SVG.",
        "categoria": "Aplicaciones",
        "tipo": "apt",
        "paquete": "inkscape",
        "icono": "/usr/share/icons/hicolor/48x48/apps/inkscape.png"
    },

    # --- SCRIPTS Y CONFIGURACIONES ---
    {
        "id": "smartboard",
        "nombre": "Drivers SMART Board",
        "descripcion": "Controladores para pizarras digitales SMART Board (smartdre / Docker).",
        "categoria": "Scripts y Configuraciones",
        "tipo": "script",
        "script": "/opt/guadamint/src/scripts/instalar_smartboard.sh",
        "icono": "/opt/guadamint/src/icons/smartboard.png"
    },
    {
        "id": "flatpak_repo",
        "nombre": "Soporte Flatpak y Flathub",
        "descripcion": "Habilita la integración de paquetes Flatpak y el repositorio Flathub.",
        "categoria": "Scripts y Configuraciones",
        "tipo": "script",
        "script": "/opt/guadamint/src/scripts/toggle-flatpak.sh",
        "icono": "/opt/guadamint/src/icons/flatpak.png"
    },
    {
        "id": "ubuntu_repos",
        "nombre": "Repositorios Temporales Ubuntu",
        "descripcion": "Activa temporalmente en RAM los repositorios oficiales de Ubuntu para actualizar paquetes.",
        "categoria": "Scripts y Configuraciones",
        "tipo": "script",
        "script": "/opt/guadamint/src/scripts/toggle-ubuntu-repos.sh",
        "icono": "/opt/guadamint/src/icons/ubuntu.png"
    }
]

def comprobar_estado(item):
    """Comprueba si un elemento está instalado o activo sin congelar la app."""
    tipo = item.get("tipo")
    try:
        if tipo == "script":
            script_path = item.get("script")
            if script_path and os.path.exists(script_path):
                res = subprocess.run([script_path, "status"], capture_output=True, text=True, timeout=3)
                return res.returncode == 0
            return False
        elif tipo == "apt":
            pkg = item.get("paquete")
            res = subprocess.run(["dpkg-query", "-W", "-f=${Status}", pkg], capture_output=True, text=True)
            return "installed" in res.stdout
    except Exception as e:
        print(f"Error comprobando {item.get('nombre')}: {e}")
    return False

class GuadaMintApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="GuadaMint - Tienda de Software")
        self.set_default_size(850, 550)
        self.set_position(Gtk.WindowPosition.CENTER)

        # HeaderBar principal
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("GuadaMint")
        header.set_subtitle("EducualAndOS v2")
        self.set_titlebar(header)

        # Botón de refrescar
        btn_refresh = Gtk.Button()
        icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        btn_refresh.add(icon)
        btn_refresh.connect("clicked", lambda x: self.cargar_catalogo())
        header.pack_end(btn_refresh)

        # Contenedor principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(main_box)

        # Barra lateral de categorías
        self.sidebar = Gtk.ListBox()
        self.sidebar.set_size_request(200, -1)
        self.sidebar.connect("row-selected", self.on_categoria_changed)

        cat_apps = Gtk.Label(label="Aplicaciones", xalign=0)
        cat_apps.set_margin_start(12)
        cat_apps.set_margin_top(12)
        cat_apps.set_margin_bottom(12)
        
        cat_scripts = Gtk.Label(label="Scripts y Configuraciones", xalign=0)
        cat_scripts.set_margin_start(12)
        cat_scripts.set_margin_top(12)
        cat_scripts.set_margin_bottom(12)

        self.sidebar.add(cat_apps)
        self.sidebar.add(cat_scripts)

        main_box.pack_start(self.sidebar, False, False, 0)
        main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)

        # Área de catálogo con Scroll
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.listbox_items = Gtk.ListBox()
        self.listbox_items.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.add(self.listbox_items)

        main_box.pack_start(scroll, True, True, 0)

        # Seleccionar primera categoría al iniciar
        self.sidebar.select_row(self.sidebar.get_row_at_index(0))

    def on_categoria_changed(self, listbox, row):
        if row is None:
            return
        label = row.get_child()
        categoria_seleccionada = label.get_text()
        self.cargar_catalogo(categoria_seleccionada)

    def cargar_catalogo(self, categoria="Aplicaciones"):
        # Limpiar lista anterior
        for child in self.listbox_items.get_children():
            self.listbox_items.remove(child)

        # Filtrar elementos por categoría
        elementos = [item for item in CATALOGO if item.get("categoria") == categoria]

        for item in elementos:
            row = Gtk.ListBoxRow()
            card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
            card.set_margin_start(12)
            card.set_margin_end(12)
            card.set_margin_top(10)
            card.set_margin_bottom(10)

            # --- GESTIÓN SEGURA DE ICONOS ---
            ruta_icono = item.get("icono", "")
            if os.path.exists(ruta_icono):
                img_icono = Gtk.Image.new_from_file(ruta_icono)
                img_icono.set_pixel_size(48)
            else:
                # Icono genérico si no se encuentra la imagen específica
                nombre_icono_defecto = "preferences-system" if item.get("tipo") == "script" else "package-x-generic"
                img_icono = Gtk.Image.new_from_icon_name(nombre_icono_defecto, Gtk.IconSize.DND)
                img_icono.set_pixel_size(48)

            card.pack_start(img_icono, False, False, 0)

            # Texto: Nombre y Descripción
            vbox_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            lbl_nombre = Gtk.Label(xalign=0)
            lbl_nombre.set_markup(f"<b>{item['nombre']}</b>")
            
            lbl_desc = Gtk.Label(label=item['descripcion'], xalign=0)
            lbl_desc.set_line_wrap(True)
            lbl_desc.set_max_width_chars(50)

            vbox_text.pack_start(lbl_nombre, False, False, 0)
            vbox_text.pack_start(lbl_desc, False, False, 0)
            card.pack_start(vbox_text, True, True, 0)

            # Conmutador / Switch de Estado
            switch = Gtk.Switch()
            switch.set_valign(Gtk.Align.CENTER)
            
            # Comprobación de estado inicial en segundo plano
            def verificar_y_actualizar_switch(sw, itm):
                estado = comprobar_estado(itm)
                GLib.idle_add(lambda: self.set_switch_state_silent(sw, estado))

            threading.Thread(target=verificar_y_actualizar_switch, args=(switch, item), daemon=True).start()

            # Conectar acción de activación/desactivación
            switch.connect("state-set", self.on_switch_toggled, item)
            card.pack_end(switch, False, False, 0)

            row.add(card)
            self.listbox_items.add(row)

        self.listbox_items.show_all()

    def set_switch_state_silent(self, switch, estado):
        """Aplica el estado al Switch sin activar la señal state-set."""
        switch.handler_block_by_func(self.on_switch_toggled)
        switch.set_active(estado)
        switch.handler_unblock_by_func(self.on_switch_toggled)

    def on_switch_toggled(self, switch, state, item):
        accion = "enable" if state else "disable"
        
        def ejecutar_accion():
            try:
                if item["tipo"] == "script":
                    cmd = ["sudo", item["script"], accion]
                elif item["tipo"] == "apt":
                    op = "install" if state else "purge"
                    cmd = ["sudo", "apt-get", op, "-y", item["paquete"]]
                
                subprocess.run(cmd, check=True)
            except Exception as e:
                print(f"Error al ejecutar {accion} en {item['nombre']}: {e}")
            finally:
                # Re-comprobar estado real tras terminar la instalación
                estado_final = comprobar_estado(item)
                GLib.idle_add(lambda: self.set_switch_state_silent(switch, estado_final))

        threading.Thread(target=ejecutar_accion, daemon=True).start()
        return True

if __name__ == "__main__":
    app = GuadaMintApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
