#!/bin/bash

base_dir=$('pwd')


echo "[Installing / removing base packages]"
sudo apt update -qy
# purge unused packages
sudo apt purge -qy thunderbird pidgin mousepad gnome-software xfburn gnome-mines sgt-puzzles sgt-launcher simple-scan transmission-gtk parole
sudo apt autoremove --purge

# install useful packages
sudo apt install -qy curl geany qtcreator libclang-common-8-dev vlc \
ipython3 $(add_prefix python3 matplotlib scipy sympy) \
build-essential cmake

# upgrade other ones
sudo apt-get upgrade -qy

source reinstall_helpers.bash

# we do everything in this directory and then remove it
mkdir -p build
cd build

# install some 3rd parties from source
extra_src_installs $base_dir

# install apt-available ROS 1 & 2
ros_apt_install

# install other ROS 1/2 packages from source
ros_src_install $base_dir

# make sure local workspace is read/exec able
chmod a+rX $LIBS_EXT_PATH -R


# install user skeleton
sudo cp -r $base_dir/skel /etc/

# Coppelia Sim
bash $base_dir/coppeliaSim_system_install.sh


# Begin DL and compile of some ROS packages
before_dl

dl_uwsim
dl_baxter
git clone https://github.com/oKermorgant/ecn_common.git
git clone https://github.com/oKermorgant/slider_publisher.git
git clone https://github.com/freefloating-gazebo/freefloating_gazebo.git

# All packages downloaded -> compile and install system-wide
after_dl

cd $base_dir
sudo rm -rf build
