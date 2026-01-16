#!/usr/bin/env bash


# a summary of various APT repos from OSRF

if [[ "$1" == "ros2.sources" ]]; then

    # remove previous lists if still here
    sudo rm -rf /etc/apt/sources.list.d/ros2-*

    sudo apt update && sudo apt install curl -y
    export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F\" '{print $4}')
    curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
    sudo dpkg -i /tmp/ros2-apt-source.deb
fi

if [[ "$1" == "gazebo-stable.list" ]]; then

    # remove previous style
    sudo rm -rf /etc/apt/sources.list.d/gazebo-latest.list

    sudo apt update && sudo apt install curl -y
    sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
fi

if [[ "$1" == "ros-latest.list" ]]; then
    sudo wget https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -O /etc/apt/trusted.gpg.d/ros.key
    sudo bash -c 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/trusted.gpg.d/ros.key] http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
fi


if [[ "$1" == "robotpkg.list" ]]; then
    sudo wget http://robotpkg.openrobots.org/packages/debian/robotpkg.asc -O /etc/apt/trusted.gpg.d/robotpkg.asc
    sudo bash -c 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/trusted.gpg.d/robotpkg.asc] http://robotpkg.openrobots.org/packages/debian/pub $(lsb_release -sc) robotpkg" > /etc/apt/sources.list.d/robotpkg.list'
fi


if [[ "$1" == "mozillateam-" ]]; then
    if snap >/dev/null 2>&1
    then
        sudo snap remove firefox --purge
        sudo apt autopurge firefox
    fi
    sudo add-apt-repository ppa:mozillateam/ppa -y
    echo '
Package: *
Pin: origin packages.mozilla.org
Pin-Priority: 1000
' | sudo tee /etc/apt/preferences.d/mozilla
fi

