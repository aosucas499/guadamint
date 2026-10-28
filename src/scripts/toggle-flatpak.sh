#!/bin/bash

TOGGLE_REPOS="/opt/guadamint/src/scripts/toggle-ubuntu-repos.sh"

esta_instalado() {
    command -v flatpak >/dev/null 2>&1
}

case "$1" in
    enable)
        if [ -x "$TOGGLE_REPOS" ]; then
            "$TOGGLE_REPOS" enable
        fi

        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq flatpak gnome-software-plugin-flatpak
        flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

        if [ -x "$TOGGLE_REPOS" ]; then
            "$TOGGLE_REPOS" disable
        fi
        ;;

    disable)
        if [ -x "$TOGGLE_REPOS" ]; then
            "$TOGGLE_REPOS" enable
        fi

        flatpak remote-delete flathub --force 2>/dev/null
        apt-get purge -y -qq flatpak gnome-software-plugin-flatpak
        apt-get autoremove -y -qq

        if [ -x "$TOGGLE_REPOS" ]; then
            "$TOGGLE_REPOS" disable
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
