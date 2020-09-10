#!/bin/bash
source reinstall_helpers.bash

# update all system packages
sudo apt update -qy
sudo apt upgrade -qy

# update all source-installed libs
cd $LIBS_EXT_PATH
github_clone "lagadic:visp" --make
for pkg in $LIBS_EXT
do
github_clone $pkg --make
done

# update ROS 1 source-installed packages
cd $ROS1_EXT_PATH/src
for pkg in $ROS1_EXT
do
github_clone $pkg
done
cd ..
ros1ws
catkin config --extend /opt/ros/$ROS1_DISTRO --install --cmake-args -DCMAKE_BUILD_TYPE=Release
catkin build

# update ROS 2 source-installed packages
cd $ROS2_EXT_PATH/src
for pkg in $ROS2_EXT
do
github_clone $pkg
done
cd ..
ros2ws
colbuild
