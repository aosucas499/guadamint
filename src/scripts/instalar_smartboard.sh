#!/bin/bash

# Colores para la terminal
AZUL="\033[1;34m"
VERDE="\033[1;32m"
NORMAL="\033[0m"

# 1. Detectar la distribución actual
DISTRO=$(lsb_release -cs)

echo -e "${AZUL}====================================================${NORMAL}"
echo -e "${AZUL}   INSTALADOR SMARTBOARD PARA GUADAMINT / UBUNTU    ${NORMAL}"
echo -e "${AZUL}====================================================${NORMAL}"

# 2. Definir la función de instalación
function installSmartdre {
    echo -e "${VERDE}Preparando descarga desde el repositorio...${NORMAL}"
    
    # Limpiamos instalaciones previas del repositorio para evitar errores de git
    if [ -d "smartdre" ]; then
        echo "Eliminando carpeta smartdre temporal existente..."
        sudo rm -rf smartdre
    fi

    # Clonar el repositorio
    git clone https://github.com/aosucas499/smartdre.git
    
    # Entrar y ejecutar el instalador específico para Noble
    cd smartdre || { echo "Error: No se pudo acceder a la carpeta"; exit 1; }
    
    echo -e "${VERDE}Ejecutando install-noble...${NORMAL}"
    chmod +x install-noble
    ./install-noble
    
    # Volver atrás
    cd ..
}

# 3. Lógica de detección de versiones para informar al usuario
if [[ $DISTRO == w* || $DISTRO == "noble" ]]; then
    echo -e "Sistema detectado: ${VERDE}Base Noble (Ubuntu 24.04 / Mint serie 22)${NORMAL}"
elif [[ $DISTRO =~ ^(jammy|victoria|virginia)$ ]]; then
    echo -e "Sistema detectado: ${VERDE}Base Jammy (Ubuntu 22.04 / Mint serie 21)${NORMAL}"
else
    echo -e "Sistema detectado: ${AZUL}$DISTRO${NORMAL}"
fi

# 4. Ejecutar la función
installSmartdre

echo -e "${AZUL}====================================================${NORMAL}"
echo -e "${VERDE}PROCESO FINALIZADO${NORMAL}"
echo -e "${AZUL}====================================================${NORMAL}"
