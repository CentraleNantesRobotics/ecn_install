#!/bin/bash
# Execute these lines in the console of the Virtual Machine to have it up to date


# Downloaded before 16 September 2020

# update ROS 1 path in bashrc
sed -i 's/"\/opt\/ros\/noetic ~\/ros"/"\/opt\/ros\/noetic \/opt\/local_ws\/ros1 ~\/ros"/' ~/.bashrc
sed -i 's/"\/opt\/ros\/foxy ~\/ros2"/"\/opt\/ros\/foxy \/opt\/local_ws\/ros2 ~\/ros2"/' ~/.bashrc
source ~/.bashrc
ros1ws
cd /opt/local_ws
sudo chown ecn . -R
mkdir -p ros1/src && cd ros1/src
git clone https://github.com/ros/geometry2.git
cd ..
catkin config --extend /opt/ros/$ROS1_DISTRO --install --cmake-args -DCMAKE_BUILD_TYPE=Release
catkin build

sudo apt update
sudo apt install -qy texlive-latex-extra texlive-fonts-recommended dvipng
cd /opt/src
git clone https://github.com/oKermorgant/log2plot
mkdir -p log2plot/build
cd log2plot/build
cmake .. && sudo make install
