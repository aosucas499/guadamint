#!/bin/bash

TOGGLE_REPOS="/opt/guadamint/src/scripts/toggle-ubuntu-repos.sh"

# Comprobar si el ejecutable instalado por install-oracular existe en el sistema
esta_instalado() {
    [ -f "/usr/bin/smartdre" ]
}

case "$1" in
    enable|install)
        # 1. Habilitar repositorios temporales de Ubuntu por si faltan dependencias (docker.io, etc.)
        if [ -f "$TOGGLE_REPOS" ]; then
            bash "$TOGGLE_REPOS" enable
        fi

        # 2. Clonar e instalar desde el repositorio oficial de SMART
        TEMP_DIR="/tmp/smartdre_install"
        rm -rf "$TEMP_DIR"
        git clone https://github.com/aosucas499/smartdre.git "$TEMP_DIR"

        if [ -d "$TEMP_DIR" ]; then
            cd "$TEMP_DIR" || exit 1
            chmod +x install-oracular
            ./install-oracular
            cd /tmp || exit 1
            rm -rf "$TEMP_DIR"
        fi

        # 3. Desactivar repositorios temporales y limpiar RAM
        if [ -f "$TOGGLE_REPOS" ]; then
            bash "$TOGGLE_REPOS" disable
        fi
        ;;

    disable|remove)
        # 1. Intentar desinstalar mediante el script oficial uninstall-smartdre
        TEMP_DIR="/tmp/smartdre_install"
        rm -rf "$TEMP_DIR"
        git clone https://github.com/aosucas499/smartdre.git "$TEMP_DIR"

        if [ -d "$TEMP_DIR" ]; then
            cd "$TEMP_DIR" || exit 1
            if [ -f "uninstall-smartdre" ]; then
                chmod +x uninstall-smartdre
                ./uninstall-smartdre
            fi
            cd /tmp || exit 1
            rm -rf "$TEMP_DIR"
        fi

        # 2. Limpieza de seguridad de archivos y accesos directos
        rm -f /usr/bin/smartdre /usr/bin/orient /usr/bin/controlpanel /usr/bin/check-appindicator-gnome-extension
        rm -f /etc/xdg/autostart/smartdre.desktop /etc/xdg/autostart/check-appindicator-gnome-extension.desktop
        rm -f /usr/share/applications/smartdre*.desktop
        rm -f /etc/sudoers.d/zz-smartdre /etc/sudoers.d/zz-orient /etc/sudoers.d/zz-controlpanel
        docker rmi aosucas499/smartdre:eos 2>/dev/null || true
        ;;

    status)
        if esta_instalado; then
            exit 0 # Instalado -> Switch ENCENDIDO
        else
            exit 1 # NO instalado -> Switch APAGADO
        fi
        ;;

    *)
        echo "Uso: $0 {enable|disable|status}"
        exit 1
        ;;
esac
