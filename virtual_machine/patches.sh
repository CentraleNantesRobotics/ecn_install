#!/bin/bash
# Execute in the console of the Virtual Machine to have it up to date

# Downloaded before 16 September 2020
cd /opt/local_ws
sudo chown ecn . -R

# update bashrc / ros management
cp ~/.ecn_install/skel/.bashrc ~
cp ~/.ecn_install/ros_management.bash /opt/local_ws

cd /opt/local_ws
sudo apt update
sudo apt install -qy texlive-latex-extra texlive-fonts-recommended dvipng
source ~/.ecn_install/reinstall_helpers.bash

github_clone oKermorgant:log2plot --cmake
github_clone oKermorgant:qtcreator_gen_config

mkdir -p ros1/src && cd ros1/src
git clone https://github.com/ros/geometry2.git
git clone https://github.com/oKermorgant/ecn_common
cd ..
sudo apt install -qy libbullet-dev 
catkin config --extend /opt/ros/$ROS_DISTRO --install --cmake-args -DCMAKE_BUILD_TYPE=Release
catkin build




