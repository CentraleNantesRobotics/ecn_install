#!/bin/bash

base_dir=$('pwd')
source reinstall_helpers.bash

echo "[Installing / removing base packages]"
sudo apt update -qy
# purge unused packages
sudo apt purge -qy thunderbird pidgin mousepad gnome-software xfburn gnome-mines sgt-puzzles sgt-launcher simple-scan transmission-gtk parole
sudo apt autoremove -qy --purge

# install useful packages
sudo apt install -qy curl geany qtcreator libclang-common-8-dev vlc \
ipython3 $(add_prefix python3 matplotlib scipy sympy) \
build-essential cmake python-is-python3

# upgrade other ones
sudo apt-get upgrade -qy

graphics=$(ubuntu-drivers devices | grep recommended)
sudo apt install $(echo $graphics | cut -d' ' -f 3)

# install some 3rd parties from source
extra_src_installs $base_dir

# install apt-available ROS 1 & 2
ros_apt_install

# install other ROS 1/2 packages from source
ros_src_install $base_dir

# install user skeleton
sudo cp -r $base_dir/skel /etc/
# install wallpaper
sudo cp $base_dir/images/noetic-foxy.jpg $LIBS_EXT_PATH
# change monitor reference to display wallpaper
this_monitor=$(xrandr --query | grep " connected" | cut -d' ' -f 1)
sudo sed -i "s/monitorVirtual1/monitor${this_monitor}/" /etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml

# make sure local workspace is {read,exec}-able
sudo chmod a+rX $LIBS_EXT_PATH -R

# Coppelia Sim
bash $base_dir/coppeliaSim_system_install.sh

# UWSim
uwsim_src_install

cd $base_dir
