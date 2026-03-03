#!/bin/bash 

# cambiarmos el fondo de escritorio. 

# el logo del boton de inicio se cambia con el boton derecho pulsando en él. 

#Modificar los archivos del grub para que tenga el archivo splash de guadamint despues de instalado en lugar del de linux mint.

#modificar el plymouth o grub desactivando los valores quiet splash por quiet. De esta manera quitamos el logo de linux mint en el boot.

# Para desactivar las aplicaciones de inicio de linux mint buscamos en /etc/xdg/autostart y /usr/share/applications y borramos: mintwelcome

# Para la pantalla de inicio de usuarios, se cambia en la aplicación ventana de inicio de sesion.

# establecer nuestros iconos, fondos para todos los usuarios
sudo eggs tools skel

# get the wardrobe of penguin eggs
eggs wardrobe get

#copy our guadamint clothes
sudo cp -r /opt/guadamint/vendors/guadamint /home/$USER/.wardrobe/vendors/

#instalar calamares 
sudo eggs calamares --install --theme guadamint

#eliminar archivos innecesarios de EGGS
sudo rm /usr/lib/penguins-eggs/assets/penguins-eggs.desktop
sudo rm /usr/lib/penguins-eggs/assets/penguins-links-add.desktop

# Modify settings for iso
#sudo nano /etc/penguins-eggs.d/eggs.yaml
sudo cp /opt/guadamint/vendors/guadamint/penguins-eggs.d/eggs.yaml /etc/penguins-eggs.d/

# Tenemos que modificar el archivo eggs.yaml a mano e incluir el vmlinuz y initrd con la versión, no dejar sin la versión.
# así como los lenguajes, Europe/Madrid para la hora. Usar # sudo nano /etc/penguins-eggs.d/eggs.yaml después de estos dos comandos.
sudo nano /etc/penguins-eggs.d/eggs.yaml

# instala lo necesario para la iso y borra scripts de creación de iso
#sudo eggs produce -vs --theme guadamint
sudo eggs kill

#crear iso definitiva
sudo eggs produce -v --theme guadamint --release --links calamares
