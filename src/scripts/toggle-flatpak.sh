#!/bin/bash

# Ruta al script de repositorios temporales
TOGGLE_REPOS="/opt/guadamint/src/scripts/toggle-ubuntu-repos.sh"

# Función para comprobar si Flatpak está instalado
esta_instalado() {
    command -v flatpak >/dev/null 2>&1
}

case "$1" in
    enable)
        # 1. Habilitar repositorios con bash (incluso si no tiene +x aún)
        if [ -f "$TOGGLE_REPOS" ]; then
            bash "$TOGGLE_REPOS" enable
        fi

        # 2. Actualizar e instalar paquetes
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -y
        apt-get install -y flatpak 
        cd "$(dirname "$0")"
        dpkg -i gnome-software-plugin-flatpak_47.0-1-SAR_amd64.deb

        # 3. Añadir el repositorio oficial Flathub
        flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

        # 4. Desactivar repositorios temporales y limpiar RAM
        if [ -f "$TOGGLE_REPOS" ]; then
            bash "$TOGGLE_REPOS" disable
        fi
        ;;

    disable)
        if [ -f "$TOGGLE_REPOS" ]; then
            bash "$TOGGLE_REPOS" enable
        fi

        flatpak remote-delete flathub --force 2>/dev/null
        apt-get purge -y flatpak gnome-software-plugin-flatpak
        apt-get autoremove -y

        if [ -f "$TOGGLE_REPOS" ]; then
            bash "$TOGGLE_REPOS" disable
        fi
        ;;

    status)
        if esta_instalado; then
            exit 0
        else
            exit 1
        fi
        ;;

    *)
        echo "Uso: $0 {enable|disable|status}"
        exit 1
        ;;
esac
