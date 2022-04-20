#!/bin/bash
source reinstall_helpers.bash
base_dir=$('pwd')

if [ "$1" == "-u" ]; then
echo "updating system packages"
# update all system packages
sudo apt update -qy
sudo apt upgrade -qy
sudo apt autoremove
fi


echo "Updating source-installed packages"
cd $LIBS_EXT_PATH
github_clone "lagadic:visp" --make
for pkg in $LIBS_EXT
do
github_clone $pkg --make
done

echo "Updating ROS 1 source-installed packages"
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
if [ -d $ROS2_EXT_PATH/src ]; then
    echo "Updating ROS 2 source-installed packages"
    cd $ROS2_EXT_PATH/src
    for pkg in $ROS2_EXT
    do
    github_clone $pkg
    done
    cd ..
    ros2ws
    colbuild
fi

# make sure local workspace is {read,exec}-able
sudo chmod a+rX $LIBS_EXT_PATH -R
sudo ldconfig
