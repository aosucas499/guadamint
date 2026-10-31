#!/bin/bash

TOGGLE_REPOS="/opt/guadamint/src/scripts/toggle-ubuntu-repos.sh"

# Comprobar si el ejecutable creado por install-eos2 ya existe en el sistema
esta_instalado() {
    [ -f "/usr/bin/smartdre" ]
}

case "$1" in
    enable|install)
        # 1. Habilitar repositorios temporales de Ubuntu (oracular via old-releases)
        # Necesario para que el 'apt install docker.io' de install-eos2 funcione
        if [ -f "$TOGGLE_REPOS" ]; then
            bash "$TOGGLE_REPOS" enable
        fi

        # 2. Clonar el repositorio smartdre e invocar install-eos2
        TEMP_DIR="/tmp/smartdre_install"
        rm -rf "$TEMP_DIR"
        git clone https://github.com/aosucas499/smartdre.git "$TEMP_DIR"

        if [ -d "$TEMP_DIR" ]; then
            cd "$TEMP_DIR" || exit 1
            
            # Forzar el arranque del servicio de Docker si ya estuviera instalado previamente
            systemctl enable --now docker 2>/dev/null || true

            chmod +x install-eos2
            ./install-eos2

            cd /tmp || exit 1
            rm -rf "$TEMP_DIR"
        fi

        # 3. Desactivar repositorios temporales para mantener EOS limpio
        if [ -f "$TOGGLE_REPOS" ]; then
            bash "$TOGGLE_REPOS" disable
        fi
        ;;

    disable|remove)
        # 1. Habilitar repositorios temporales por si la limpieza requiere APT
        if [ -f "$TOGGLE_REPOS" ]; then
            bash "$TOGGLE_REPOS" enable
        fi

        # 2. Ejecutar desinstalador oficial uninstall-smartdre
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

        # 3. Limpieza complementaria de seguridad
        rm -f /usr/bin/smartdre /usr/bin/orient /usr/bin/controlpanel /usr/bin/check-appindicator-gnome-extension
        rm -f /etc/xdg/autostart/smartdre.desktop /etc/xdg/autostart/check-appindicator-gnome-extension.desktop
        rm -f /usr/share/applications/smartdre*.desktop
        rm -f /etc/sudoers.d/zz-smartdre /etc/sudoers.d/zz-orient /etc/sudoers.d/zz-controlpanel
        docker rmi aosucas499/smartdre:eos 2>/dev/null || true

        # 4. Desactivar repositorios temporales
        if [ -f "$TOGGLE_REPOS" ]; then
            bash "$TOGGLE_REPOS" disable
        fi
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
