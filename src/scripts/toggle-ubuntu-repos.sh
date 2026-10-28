#!/bin/bash

TEMP_REPO_FILE="/tmp/ubuntu-temp.list"
SYMLINK_REPO_FILE="/etc/apt/sources.list.d/ubuntu-temp.list"

# 1. Asegurar el enlace simbólico permanente si no existe
if [ ! -L "$SYMLINK_REPO_FILE" ]; then
    ln -sf "$TEMP_REPO_FILE" "$SYMLINK_REPO_FILE"
fi

# 2. Según el argumento ($1), activar o desactivar
case "$1" in
    enable)
        echo "# Repositorios temporales de Ubuntu en RAM (/tmp)" > "$TEMP_REPO_FILE"
        echo "deb http://archive.ubuntu.com/ubuntu/ jammy main restricted universe multiverse" >> "$TEMP_REPO_FILE"
        echo "deb http://archive.ubuntu.com/ubuntu/ jammy-updates main restricted universe multiverse" >> "$TEMP_REPO_FILE"
        echo "deb http://archive.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse" >> "$TEMP_REPO_FILE"
        apt-get update -qq
        ;;
    disable)
        rm -f "$TEMP_REPO_FILE"
        apt-get update -qq
        ;;
    status)
        if [ -s "$TEMP_REPO_FILE" ]; then
            exit 0 # Activo
        else
            exit 1 # Inactivo
        fi
        ;;
    *)
        echo "Uso: $0 {enable|disable|status}"
        exit 1
        ;;
esac
