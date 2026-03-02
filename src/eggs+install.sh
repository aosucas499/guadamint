#!/bin/bash 

# para ver bien en virtualbox
eggs adapt

# establecer nuestros iconos, fondos para todos los usuarios
eggs tools skel

# get the wardrobe of penguin eggs
eggs wardrove get

#copy our guadamint clothes
sudo cp -r /opt/guadamint/vendors/guadamint /home/$USER/.wardrobe/vendors/

#instalar calamares 
sudo eggs calamares --install --theme guadamint

# paquetes necesarios para instalación en EFI secureboot
#sudo dpkg -i grub-efi-amd64-signed*amd64.deb
sudo apt update -y 
#sudo apt-get install grub-efi-amd64-signed -y 
#sudo apt-get install shim-signed -y

#eliminar archivos innecesarios de EGGS
sudo rm /usr/share/applications/calamares.desktop
sudo rm /usr/lib/penguins-eggs/assets/penguins-eggs.desktop
sudo rm /usr/lib/penguins-eggs/assets/penguins-links-add.desktop

# NOW, we configure eggs, whit it's default 
sudo eggs dad -d

# Modify settings for iso
#sudo nano /etc/penguins-eggs.d/eggs.yaml
sudo cp /opt/guadamint/vendors/guadamint/penguins-eggs.d/eggs.yaml /etc/penguins-eggs.d/

# Tenemos que modificar el archivo eggs.yaml a mano e incluir el vmlinuz y initrd con la versión, no dejar sin la versión.
# así como los lenguajes, Europe/Madrid para la hora. Usar # sudo nano /etc/penguins-eggs.d/eggs.yaml después de estos dos comandos.
sudo nano /etc/penguins-eggs.d/eggs.yaml

# instala lo necesario para la iso y borra scripts de creación de iso
sudo eggs produce -vs --theme guadamint
sudo eggs kill

sudo apt-get update -y

#crear iso definitiva
sudo eggs produce -v --theme educaandos 
