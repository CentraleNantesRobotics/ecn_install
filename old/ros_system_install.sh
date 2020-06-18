#!/bin/bash
# The BSD License
# Copyright (c) 2014 OROCA and ROS Korea Users Group
# Adapted for specific needs during labs - Olivier Kermorgant

ROS1_DISTRO="noetic"
ROS2_DISTRO="foxy"

install_ros_pkg()
{
ros_pkgs=""
local this_distro
for pkg in $pkgs 
do
if [[ $this_distro = "" ]]; then
    this_distro=$pkg
    echo $this_distro
else
ros_pkgs="$ros_pkgs ros-$this_distro-$pkg"
fi
done
echo $ros_pkgs
}

source def_reinstall.sh

echo "[Adding ROS repositories]"
if [ ! -e /etc/apt/sources.list.d/ros-latest.list ]; then
  sudo sh -c "echo \"deb http://packages.ros.org/ros/ubuntu $version main\" > /etc/apt/sources.list.d/ros-latest.list"
fi

echo "[Getting ROS key]"
roskey=`apt-key list | grep "ROS builder"`
if [ -z "$roskey" ]; then
  wget --quiet https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -O - | sudo apt-key add -
fi

echo "[System update]"
sudo apt-get update -qy
sudo apt-get upgrade -qy

echo "[ROS installation]"
pkgs="desktop gazebo-ros-pkgs image-view compressed-image-transport moveit-setup-assistant moveit amcl robot-localization vision-opencv"

ros_pkgs=""
for pkg in $pkgs 
do
ros_pkgs="$ros_pkgs ros-$ros_distro-$pkg"
done

sudo apt-get install -y python-rosdep gitk python-sympy python-rosinstall python-catkin-tools ipython python-matplotlib libvisp-dev $ros_pkgs

source /opt/ros/$ros_distro/setup.bash
echo "[rosdep init]"
sudo sh -c "rosdep init"
