#!/bin/bash
# The BSD License
# Will install Coppelia Sim in /opt 
# Olivier Kermorgant

cSim_version="4_1_0"

ubuntu_version=`lsb_release -sr | sed 's/\./_/g'`
cSim_file=CoppeliaSim_Edu_V${cSim_version}_Ubuntu18_04.tar.xz

base_dir=$('pwd')

if [ ! -f $cSim_file ]
then
    echo "Downloading CoppeliaSim"
    wget https://coppeliarobotics.com/files/$cSim_file
fi

if [ ! -f $cSim_file ]
then
    exit
fi

dest='/opt/coppeliaSim'

if [ -d ${dest} ]
then
echo "Deleting previous directory"
sudo rm -rf ${dest}
fi

sudo mkdir ${dest}
echo "Extracting archive"
sudo tar -xf $cSim_file -C ${dest} --strip 1

sudo ln -s ${dest}/compiledRosPlugins/* ${dest}

sudo chmod -R a+rwX ${dest}

export COPPELIASIM_ROOT_DIR=${dest}

if [ "$#" -eq 1 ]; then
    sudo mkdir -p "$1/src"
    sudo chmod -R a+rwX "$1"
    cd "$1/src"
    git clone https://github.com/oKermorgant/coppeliasim_ros_launcher.git
else
    echo "To run CoppeliaSim from ROS launch files, follow these steps:"
    echo " - go to your ROS workspace source"
    echo " - git clone https://github.com/oKermorgant/coppeliasim_ros_launcher.git"
    echo " - catkin build"
fi

rm  $cSim_file 

cd $base_dir
