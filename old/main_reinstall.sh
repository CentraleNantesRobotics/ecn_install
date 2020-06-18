#!/bin/bash

base_dir=$('pwd')

# check that we have all files
deps="def_reinstall.sh ros_system_install.sh vrep_system_install.sh skel/.bashrc"
for dep in $deps
do
    if [ ! -f $dep ]
    then
    git clone https://gitlab.univ-nantes.fr/kermorgant-o/ecn_install.git
    cd ecn_install
    bash main_reinstall.sh
    exit
fi
done

source def_reinstall.sh

## purge unused packages
sudo apt purge -y thunderbird pidgin mousepad

sudo apt install ipython3 geany libvisp-dev

# we do everything in this directory and then remove it
mkdir -p build
cd build

# install ROS
bash $base_dir/ros_system_install.sh

# install user skeleton
sudo cp -r $base_dir/skel /etc/

# Coppelia Sim
bash $base_dir/vrep_system_install.sh /opt/ros_ext 

# cuda / tensorflow
install_tensorflow

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
