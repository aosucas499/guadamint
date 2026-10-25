#!/bin/bash

# Comprobación de root para la INSTALACIÓN
if [ "$EUID" -ne 0 ]; then
  echo "Por favor, ejecuta el instalador como root (sudo ./install.sh)"
  exit 1
fi

echo ">>> Instalando sistema GuadaMint (Actualizador + Tienda)..."

# 0. INSTALAR DEPENDENCIAS (GIT)
echo "Comprobando dependencias..."
if ! command -v git &> /dev/null; then
    echo "-> Git no encontrado. Instalando..."
    apt-get update
    apt-get install -y git
    if [ $? -eq 0 ]; then
        echo "-> Git instalado correctamente."
    else
        echo "¡ERROR CRÍTICO! No se pudo instalar git. El actualizador fallará."
        exit 1
    fi
else
    echo "-> Git ya está instalado. Correcto."
fi

# 1. DEFINIR RUTAS DE ORIGEN Y DESTINO
SOURCE_DIR=$(dirname "$0")

DEST_BIN_UPDATE="/usr/bin/guadamint-update.py"  
DEST_BIN_STORE="/usr/bin/apps-guadamint.py"
DEST_AUTOSTART="/etc/xdg/autostart/guadamint-update.desktop"
DEST_LAUNCHER_STORE="/usr/share/applications/apps-guadamint.desktop"
DEST_ICON="/usr/share/icons/guadamintuz.svg"
LOG_DIR="/var/log/guadamint"
OPT_DIR="/opt/guadamint"

# FUNCIÓN DE BÚSQUEDA INTELIGENTE
buscar_archivo() {
    local archivo=$1
    local subcarpeta=$2
    if [ -f "$SOURCE_DIR/$subcarpeta/$archivo" ]; then
        echo "$SOURCE_DIR/$subcarpeta/$archivo"
    elif [ -f "$SOURCE_DIR/$archivo" ]; then
        echo "$SOURCE_DIR/$archivo"
    else
        echo ""
    fi
}

# 2. CREAR ESTRUCTURA BASE EN /opt/guadamint
echo "Creando directorios base en /opt/guadamint..."
mkdir -p "$OPT_DIR/images"
mkdir -p "$OPT_DIR/src"

# 3. COMPROBACIÓN E INSTALACIÓN DEL SUDOERS (TOGGLE / PERMISOS)
FILE_SUDOERS=$(buscar_archivo "zz-guadamint-update" "src")
SUDOERS_DEST="/etc/sudoers.d/zz-guadamint-update"

if [ -n "$FILE_SUDOERS" ]; then
    echo "Configurando permisos sudo con $FILE_SUDOERS..."
    cp "$FILE_SUDOERS" "$SUDOERS_DEST"
    chown root:root "$SUDOERS_DEST"
    chmod 0440 "$SUDOERS_DEST"
    echo "-> Permisos sudoers configurados correctamente."
else
    echo "¡ERROR CRÍTICO! No se encontró el archivo 'zz-guadamint-update'."
    exit 1
fi

# 4. COPIAR IMÁGENES A /opt/guadamint/images
if [ -d "$SOURCE_DIR/images" ]; then
    echo "Copiando imágenes iniciales a $OPT_DIR/images/..."
    cp -r "$SOURCE_DIR/images/"* "$OPT_DIR/images/" 2>/dev/null
fi

# 5. COPIAR EL SCRIPT ACTUALIZADOR (PYTHON)
FILE_UPDATE=$(buscar_archivo "guadamint-update.py" "src")

if [ -n "$FILE_UPDATE" ]; then
    echo "Copiando actualizador a $DEST_BIN_UPDATE y $OPT_DIR/src/..."
    cp "$FILE_UPDATE" "$DEST_BIN_UPDATE"
    chmod 755 "$DEST_BIN_UPDATE"
    
    cp "$FILE_UPDATE" "$OPT_DIR/src/guadamint-update.py"
    chmod 755 "$OPT_DIR/src/guadamint-update.py"
else
    echo "¡ERROR CRÍTICO! No se encuentra 'guadamint-update.py'."
    exit 1
fi

# 6. COPIAR LA TIENDA DE APPS (PYTHON)
FILE_STORE=$(buscar_archivo "apps-guadamint.py" "src")

if [ -n "$FILE_STORE" ]; then
    echo "Copiando tienda $FILE_STORE a $DEST_BIN_STORE..."
    cp "$FILE_STORE" "$DEST_BIN_STORE"
    chmod 755 "$DEST_BIN_STORE"
    
    cp "$FILE_STORE" "$OPT_DIR/src/apps-guadamint.py" 2>/dev/null
else
    echo "AVISO: No se encuentra 'apps-guadamint.py'. La tienda no se instalará."
fi

# 7. COPIAR EL AUTOARRANQUE (.desktop)
FILE_AUTOSTART=$(buscar_archivo "guadamint-update.desktop" "src")

if [ -n "$FILE_AUTOSTART" ]; then
    echo "Copiando autostart $FILE_AUTOSTART a $DEST_AUTOSTART..."
    cp "$FILE_AUTOSTART" "$DEST_AUTOSTART"
    chmod 644 "$DEST_AUTOSTART"
else
    echo "¡ERROR CRÍTICO! No se encuentra 'guadamint-update.desktop'."
    exit 1
fi

# 8. COPIAR EL LANZADOR DE LA TIENDA (.desktop)
FILE_LAUNCHER=$(buscar_archivo "apps-guadamint.desktop" "src")

if [ -n "$FILE_LAUNCHER" ]; then
    echo "Copiando lanzador de menú $FILE_LAUNCHER a $DEST_LAUNCHER_STORE..."
    cp "$FILE_LAUNCHER" "$DEST_LAUNCHER_STORE"
    chmod 644 "$DEST_LAUNCHER_STORE"
else
    echo "AVISO: No se encuentra 'apps-guadamint.desktop'."
fi

# 9. INSTALAR ICONO
FILE_ICON=$(buscar_archivo "guadamintuz.svg" "images")
if [ -z "$FILE_ICON" ]; then FILE_ICON=$(buscar_archivo "AndaTuz2.svg" "images"); fi

echo "Instalando icono en $DEST_ICON..."
if [ -n "$FILE_ICON" ]; then
    cp "$FILE_ICON" "$DEST_ICON"
    chmod 644 "$DEST_ICON"
    echo "-> Icono instalado."
else
    echo "AVISO: No se encontró el icono (guadamintuz.svg). Se usará genérico."
fi

# 10. DIRECTORIO DE LOGS Y PERMISOS FINAL
mkdir -p "$LOG_DIR"
chmod 777 "$LOG_DIR"

echo ">>> Instalación completada con éxito."
