#!/bin/bash
# Script de instalación para Drivers SMART Board (Ubuntu 20)
# Ejecutado por apps-guadamint.py (ya tiene permisos de root)

echo "=== Descargando clave de SMART Technologies ==="
wget -q https://downloads.smarttech.com/software/linux/nb-for-ubuntu-20/dists/swbuild.asc -O /tmp/swbuild.asc

echo "=== Añadiendo clave de seguridad ==="
apt-key add /tmp/swbuild.asc

echo "=== Añadiendo repositorio temporal ==="
echo "deb http://downloads01.smarttech.com/software/linux/nb-for-ubuntu-20 stable non-free" > /etc/apt/sources.list.d/smartboard.list

echo "=== Actualizando lista de paquetes ==="
apt-get update -y

echo "=== Instalando drivers de la Pizarra SMART ==="
apt-get install -y smart-product-drivers smart-notebook
apt-get install -f -y

echo "=== Limpiando repositorio temporal ==="
# Borramos el repo para evitar errores de actualización en el futuro
rm /etc/apt/sources.list.d/smartboard.list
rm /tmp/swbuild.asc

echo "=== Instalación de SMART Board completada ==="
