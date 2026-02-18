#!/bin/bash

# ==============================================================================
# SCRIPT DE INSTALACIÓN: GOOGLE CHROME STABLE
# Compatible con: Linux Mint, Ubuntu, Debian (amd64)
# ==============================================================================

# 1. Comprobación de seguridad (Debe correr como Root)
if [ "$EUID" -ne 0 ]; then
  echo "!!! Error: Este script debe ejecutarse como root."
  exit 1
fi

echo ">>> Iniciando instalación de Google Chrome..."

# 2. Definir URL y archivo temporal
URL_CHROME="https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
TEMP_DEB="/tmp/google-chrome-stable_current_amd64.deb"

# 3. Descargar el paquete
# Usamos wget con -q (quiet) pero --show-progress para ver algo si se ejecuta en terminal
if command -v wget >/dev/null 2>&1; then
    echo "-> Descargando paquete oficial..."
    wget -q --show-progress "$URL_CHROME" -O "$TEMP_DEB"
else
    echo "!!! Error: No se encuentra 'wget'. Instalando..."
    apt-get update && apt-get install -y wget
    wget -q "$URL_CHROME" -O "$TEMP_DEB"
fi

# Verificar si la descarga fue correcta
if [ ! -f "$TEMP_DEB" ]; then
    echo "!!! Error: La descarga ha fallado."
    exit 1
fi

# 4. Instalar el paquete
# Usamos 'apt-get install' sobre el archivo local .deb
# Esto es mejor que 'dpkg -i' porque apt resuelve y descarga las dependencias automáticamente.
echo "-> Instalando paquete y dependencias..."

apt-get update  # Actualizamos índices por si acaso faltan dependencias nuevas
apt-get install -y "$TEMP_DEB"

STATUS=$?

# 5. Limpieza
echo "-> Limpiando archivos temporales..."
rm -f "$TEMP_DEB"

# 6. Verificación final
if [ $STATUS -eq 0 ]; then
    # Comprobamos si el binario existe realmente
    if command -v google-chrome-stable >/dev/null 2>&1; then
        echo ">>> ¡ÉXITO! Google Chrome se ha instalado correctamente."
        exit 0
    else
        echo "!!! Advertencia: La instalación pareció funcionar, pero no encuentro el ejecutable."
        exit 1
    fi
else
    echo "!!! Error crítico durante la instalación."
    exit 1
fi
