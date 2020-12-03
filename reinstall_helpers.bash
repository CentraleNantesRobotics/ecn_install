#!/bin/bash

# List of apt-installed packages
ROS1_PKG="desktop robot-localization vision-opencv gazebo-ros-pkgs image-view compressed-image-transport amcl control-toolbox kdl-parser-py"
ROS2_PKG="desktop vision-opencv xacro joint-state-publisher joint-state-publisher-gui image-view compressed-image-transport ros1-bridge"

# Packages installed system-wide from source (list of owner:repo[:branch] on Github)
ROS1_EXT="RethinkRobotics:baxter_common CentraleNantesRobotics:baxter_interface CentraleNantesRobotics:baxter_tools oKermorgant:ecn_common oKermorgant:coppeliasim_ros_launcher freefloating-gazebo:freefloating_gazebo oKermorgant:slider_publisher:ros1 CentraleNantesRobotics:baxter_simple_sim"
ROS2_EXT="CentraleNantesRobotics:baxter_common_ros2 oKermorgant:slider_publisher:ros2 oKermorgant:simple_launch"

# System-wide libraries to install (list of owner:repo[:branch])
LIBS_EXT="oKermorgant:log2plot oKermorgant:qtcreator_gen_config"

# define ros workspaces
ros1_workspaces="/opt/ros/noetic /opt/local_ws/ros1"
ros2_workspaces="/opt/ros/foxy /opt/local_ws/ros2"

source ros_management.bash

# extract ROS base distros
ROS1_DISTRO=$(echo ${ros1_workspaces% *} | cut -d'/' -f 4)
ROS2_DISTRO=$(echo ${ros2_workspaces% *} | cut -d'/' -f 4)

# extract 3rd party directories
ROS1_EXT_PATH=$(echo $ros1_workspaces | cut -d' ' -f 2)
ROS2_EXT_PATH=$(echo $ros2_workspaces | cut -d' ' -f 2)
LIBS_EXT_PATH=$(echo ${ROS1_EXT_PATH%/*})

# adds a prefix (first argument) to a list of packages
add_prefix()
{
local pkgs=""
local prefix
local pkg
for pkg in $@
do
if [[ $prefix = "" ]]; then
    prefix=$pkg
else
pkgs="$pkgs $prefix-$pkg"
fi
done
echo $pkgs
}

# git clone a repo from a owner:repo:branch string
github_clone()
{
local owner=$(echo $1 | cut -d':' -f 1)
local repo=$(echo $1 | cut -d':' -f 2)
local branch=$(echo $1 | cut -d':' -f 3)
if [ -d "$repo" ]; then
  echo "updating $repo"
  cd $repo && git pull
  cd ..
else
  if [[ ${#branch} -le 2 ]]; then
      git clone https://github.com/$owner/$repo
  else
      git clone https://github.com/$owner/$repo -b $branch
  fi
fi

# try to compile if required / relevant
if [ "$#" -eq 2 ] && [ -f "$repo/CMakeLists.txt" ]; then
    mkdir -p "$repo/build"
    cd "$repo/build"
    if [ "$2" = "--cmake" ]; then
    cmake ..
    fi
    sudo make install
    cd ../../
fi
}

extra_src_installs()
{
base_dir=$1	
	
# external libraries from source
sudo mkdir -p $LIBS_EXT_PATH
sudo chown $USER $LIBS_EXT_PATH -R
cd $LIBS_EXT_PATH

# ViSP from sources - special cmake flags
sudo apt install -qy libogre-1.9-dev libopencv-dev libeigen3-dev libopenblas-dev liblapack-dev libxml2-dev libzbar-dev libgsl-dev
github_clone "lagadic:visp"
mkdir -p visp/build && cd visp/build
cmake .. -DBUILD_DEMOS=OFF -DBUILD_DEPRECATED_FUNCTIONS=ON -DBUILD_EXAMPLES=OFF -DBUILD_JAVA=OFF -DBUILD_PACKAGE=OFF -DBUILD_TESTS=OFF -DBUILD_TUTORIALS=OFF -DUSE_PCL=OFF -DBUILD_MODULE_visp_sensor=OFF
sudo make install

# log2plot deps
sudo apt install -qy texlive-latex-extra texlive-fonts-recommended dvipng

# all generic sources
cd $LIBS_EXT_PATH
for pkg in $LIBS_EXT
do
github_clone $pkg --cmake
done

# CoppeliaSim
cd $LIBS_EXT_PATH
bash $base_dir/coppeliaSim_system_install.sh
sudo chmod a+rX $LIBS_EXT_PATH -R
}


# Setup ROS 1  system install through apt
ros_apt_install()
{
echo "[Getting ROS key]"
sudo apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654
curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add -

echo "[Adding ROS repositories]"
if [ ! -e /etc/apt/sources.list.d/ros-latest.list ]; then
  sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
fi

echo "[System update]"
sudo apt-get update -qy

# some prerequisite packages
sudo apt install -qy $(add_prefix python3 rosdep catkin-tools rosinstall argcomplete osrf-pycommon)

echo "[ROS 1 installation]"
sudo apt-get install -qy $(add_prefix ros-$ROS1_DISTRO $ROS1_PKG)

source /opt/ros/$ROS1_DISTRO/setup.bash
echo "[rosdep init]"
sudo sh -c "rosdep init"
rosdep update
}

ros2_apt_install()
{
echo "[Getting ROS key]"
sudo apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654
curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add -

echo "[Adding ROS2 repositories]"
if [ ! -e /etc/apt/sources.list.d/ros2-latest.list ]; then
  sudo sh -c 'echo "deb http://packages.ros.org/ros2/ubuntu `lsb_release -cs` main" > /etc/apt/sources.list.d/ros2-latest.list'
fi

echo "[System update]"
sudo apt-get update -qy

# some prerequisite packages
sudo apt install -qy $(add_prefix python3 colcon-common-extensions rosdep catkin-tools rosinstall argcomplete osrf-pycommon)

echo "[ROS 2 installation]"
sudo apt-get install -y $(add_prefix ros-$ROS2_DISTRO $ROS2_PKG)	
}


# Installs required ROS1 packages from source
ros_src_install()
{
echo "[ROS 1 packages from source]"
sudo mkdir -p $ROS1_EXT_PATH/src
sudo chown $USER $ROS1_EXT_PATH -R
sudo cp $1/ros_management.bash $LIBS_EXT_PATH
source $LIBS_EXT_PATH/ros_management.bash

cd $ROS1_EXT_PATH/src
local pkg
for pkg in $ROS1_EXT
do
github_clone $pkg
done
cd ..
ros1ws
catkin config --extend /opt/ros/$ROS1_DISTRO --install --cmake-args -DCMAKE_BUILD_TYPE=Release
catkin build

sudo chmod a+rX $LIBS_EXT_PATH -R
}

# Installs required ROS2 packages from source
ros2_src_install()
{
echo "[ROS 2 packages from source]"
sudo mkdir -p $ROS2_EXT_PATH/src
sudo chown $USER $ROS2_EXT_PATH -R
cd $ROS2_EXT_PATH/src
local pkg
for pkg in $ROS2_EXT
do
github_clone $pkg
done
cd ..
ros2ws
colbuild

sudo chmod a+rX $LIBS_EXT_PATH -R
}


# install UWSim (after ROS 1)
uwsim_src_install()
{
	src_dir=`pwd`

	# packaged deps
	sudo apt install -qy libopenscenegraph-dev libfftw3-dev libxml++2.6-dev

	# as ROS pkg
	cd $ROS1_EXT_PATH/src
	git clone https://github.com/oKermorgant/underwater_simulation
		
	# non packaged deps
	cd underwater_simulation/3rd_parties
	deps="uwsim_osgocean uwsim_osgworks"
	for dep in $deps
	do
	mkdir -p $dep-release/build
	cd $dep-release/build
	cmake .. -DCMAKE_BUILD_TYPE=Release && sudo make install
	cd ../..
	#sudo rm -rf $dep-release/build
	done

	# compile
	ros1ws && catkin build uwsim
	
	# DL dataset
	if [ ! -d /opt/uwsim/data ]
	then
		sudo mkdir -p /opt/uwsim/ -m 2755
                sudo chown $USER /opt/uwsim
		cd /opt/uwsim
		wget http://pagesperso.ls2n.fr/~kermorgant-o/files/uwsim_data.tgz
		tar -xf uwsim_data.tgz		
		rm uwsim_data.tgz
        chmod a+rX -R .
		
		# on-the-fly symlink for all users
		sudo bash -c "echo 'if [ ! -d ~/.uwsim ]; then ln -s /opt/uwsim ~/.uwsim; fi' >> /etc/bash.bashrc"
	fi
	cd $src_dir
}
