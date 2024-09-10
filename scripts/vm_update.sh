#!/bin/bash

sed -i "/^export PS1=/c\export PS1=\"\\\[\\\e[1;34m\\\]\\\w\\\[\\\e[0m\\\]$ \"" ~/.bashrc

# change to Galactic to enable Ignition Fortress bridge
if [ ! $(grep -c foxy ~/.bashrc) -eq 0 ]; then
    echo "Changing ROS 2 from foxy to galactic"
    rm -rf ~/ros2/build ~/ros2/install
    rm -rf /opt/ecn/ros2/build /opt/ecn/ros2/install /opt/ecn/ros2/log
    sed -i 's/foxy/galactic/g' ~/.bashrc
    sudo apt purge ros-foxy-*
    sudo apt autoremove --purge
    sed -i 's/foxy/galactic/g' ~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml
fi
