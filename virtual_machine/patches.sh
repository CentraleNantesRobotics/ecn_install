#!/bin/bash
# Uses the previous date when this script was run
# Avoids re-patching things

INSTALLDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"

git_update_subfolders()
{
for f in $(ls $1)
do
    if [ -d "$1/$f/.git" ]; then
    cd $1/$f
    echo "Refreshing $1/$f..."
    git pull
    fi
done
}

cd $INSTALLDIR

if [ ! -f ".latest" ]
then
    prev=2020-09-01
    ros_apt_install
else
    prev=$(cat .latest)
fi

student=""
if [ -f ~/.m2 ]; then
    student="M2_IMARO"
elif [ -f ~/.m1 ]; then
    student="M1_CORO"
elif [ -f ~/.rob ]; then
    student="OD_Robotique"
fi

if [ "$student" = "" ]; then
    echo "Please create a file to indicate your academic program:
    M1 CORO: touch ~/.m1
    M2 CORO-IMARO: touch ~/.m2
    OD Robotique: touch ~/.rob

    Then re-run this script"
    exit 1
fi

echo "Performing update for $student, last update was on $prev"

# # do a full upgrade anyway
sudo apt purge libreoffice-core libreoffice-common -qy
sudo apt autoremove --purge -qy
sudo apt update -qy
sudo apt upgrade -qy
sudo apt autoremove --purge -qy

# update bashrc / ros management
cd $INSTALLDIR
cp skel/.bashrc ~
source ~/.bashrc
source reinstall_helpers.bash


if [[ $prev < 2020-11-06 ]] && [ $student = "OD_Robotique" ]; then
    # prep ROS 2 labs... with ROS 1 packages
	cd $ROS1_EXT_PATH/src
	github_clone CentraleNantesRobotics:baxter_simple_sim
	github_clone oKermorgant:slider_publisher:ros1

    # install ROS 2 base packages
    ros2_apt_install
	mkdir -p $ROS2_EXT_PATH/src
	chown $USER $ROS2_EXT_PATH -R
	cd $ROS2_EXT_PATH/src
	local pkg
	for pkg in $ROS2_EXT
	do
	github_clone $pkg
	done
fi

if [[ $prev < 2020-11-23 ]] && [ $student = "OD_Robotique" ]; then
    cd $ROS2_EXT_PATH
    rm -rf install build log
    # uwsim
    #uwsim_src_install
    sudo apt install -qy $(add_prefix ros-$ROS1_DISTRO gazebo-ros gazebo-plugins)
    # ffg
    cd $ROS1_EXT_PATH/src
    github_clone freefloating-gazebo:freefloating_gazebo
fi

if [[ $prev < 2021-03-05 ]] && [ $student = "OD_Robotique" ]; then
    cd $ROS1_EXT_PATH/src
    github_clone oKermorgant:coppeliasim_ros_launcher
    cd $INSTALLDIR
    bash coppeliaSim_system_install.sh
fi



echo "Updating source-installed packages"
for f in $(ls /opt/local_ws)
do
    if [ -d "/opt/local_ws/$f/.git" ]; then
        cd /opt/local_ws/$f
        echo "Refreshing /opt/local_ws/$f..."
        git pull
        if [ -d "/opt/local_ws/$f/build" ]; then
            cd /opt/local_ws/$f/build
            sudo make install
        fi
    fi
done

echo "Updating ROS 1 source-installed packages"
source ~/.bashrc
git_update_subfolders $ROS1_EXT_PATH/src
cd $ROS1_EXT_PATH
ros1ws
catkin build --force-cmake

if [ -d $ROS2_EXT_PATH/src ]; then
echo "Updating ROS 2 source-installed packages"
    git_update_subfolders $ROS2_EXT_PATH/src
    cd $ROS2_EXT_PATH
    colbuild
fi

cd $INSTALLDIR
echo $(date -Idate) > .latest
