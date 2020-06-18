#!/bin/bash
# The BSD License
# Copyright (c) 2014 OROCA and ROS Korea Users Group
# Adapted for specific needs during labs - Olivier Kermorgant

#set -x

ros_ws=$1
ros_ws=${ros_ws:="ros"}

ros_distro="indigo" # default version

version=`lsb_release -sc`

# yep, we only support LTS's
if [ "$version" = "xenial" ]
then
  ros_distro="kinetic"
fi

rosdep update

echo "[Making the catkin workspace and compiling]"
mkdir -p ~/$ros_ws/src
cd ~/$ros_ws/src
cd ~/$ros_ws/
source /opt/ros/$ros_distro/setup.bash
catkin build --save-config --cmake-args -DCMAKE_BUILD_TYPE=Debug

echo "[Setting the ROS evironment]"
sh -c "echo \"source /opt/ros/$ros_distro/setup.bash\" >> ~/.bashrc"
sh -c "echo \"source ~/$ros_ws/devel/setup.bash\" >> ~/.bashrc"
sh -c "echo \"alias dmake=cmake -DCMAKE_BUILD_TYPE=Debug\" >> ~/.bashrc"

echo "[Complete!]"
echo "Open a new terminal to initialize the ROS environment"

exec bash
