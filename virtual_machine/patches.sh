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



# # update bashrc / ros management
if [[ $prev < 2021-03-30 ]] && [ $student = "OD_Robotique" ]; then
    cd /opt/local_ws
    github_clone oKermorgant:ros_management_tools
    rm -rf qtcreator_gen_config
    rm -rf log2plot
fi
cp skel/.bashrc ~
source reinstall_helpers.bash

if [[ $prev < 2020-09-16 ]]
then
    # Downloaded before 16 September 2020
    sudo apt install -qy texlive-latex-extra texlive-fonts-recommended dvipng libbullet-dev 

    cd $LIBS_EXT_PATH
    sudo chown ecn . -R
    github_clone oKermorgant:log2plot --cmake
    github_clone oKermorgant:qtcreator_gen_config

    mkdir -p ros1/src && cd ros1/src
    git clone https://github.com/oKermorgant/ecn_common
    git clone https://github.com/RethinkRobotics/baxter_common.git
fi

if [[ $prev < 2020-10-07 ]]
then
    # a small typo in the previous patch...
    sudo chown ecn /home/ecn/ros -R
    ros_apt_install
fi

if [[ $prev < 2020-11-06 ]] && [ $student = "OD_Robotique" ]; then
    # prep ROS 2 labs... with ROS 1 packages
	cd $ROS1_EXT_PATH/src
	github_clone CentraleNantesRobotics:baxter_simple_sim
	github_clone oKermorgant:slider_publisher:ros1

    # install ROS 2 base packages
    ros2_apt_install
	sudo mkdir -p $ROS2_EXT_PATH/src
	sudo chown $USER $ROS2_EXT_PATH -R
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
    sudo apt install -qy $(add_prefix  ros-$ROS1_DISTRO gazebo-ros gazebo-plugins)
    # ffg
    cd $ROS1_EXT_PATH/src
    github_clone freefloating-gazebo:freefloating_gazebo
fi

if [[ $prev < 2020-12-3 ]]; then
   # remove geometry2 pkg, was fixed   
   cd $ROS1_EXT_PATH
   if [ -d src/geometry2 ]; then
    geom2=$(ls src/geometry2)
    dsts="build devel/.private devel/include devel/lib devel/share install/include install/lib install/share"
    for dst in $dsts
    do
        for pkg in $geom2
        do
            if [ -d "$dst/$pkg" ]; then
                rm -rf $dst/$pkg
            fi        
        done
    done
    rm -rf src/geometry2
   fi
   if [ -d src/underwater_simulation ]; then
    touch src/underwater_simulation/CATKIN_IGNORE
   fi
fi

if [[ $prev < 2020-12-16 ]] && [ $student = "OD_Robotique" ]; then
    # add map simulator for lab 4
    cd $ROS2_EXT_PATH/src
    github_clone oKermorgant:map_simulator:ros2
    sudo apt install -qy $(add_prefix  ros-$ROS2_DISTRO navigation2) 
fi

if [[ $prev < 2021-01-06 ]] && [ $student = "OD_Robotique" ]; then
    cd $ROS1_EXT_PATH
    rm -rf build devel logs
fi

if [[ $prev < 2021-03-05 ]] && [ $student = "OD_Robotique" ]; then
    cd $ROS1_EXT_PATH/src
    github_clone oKermorgant:coppeliasim_ros_launcher
    cd $INSTALLDIR
    bash coppeliaSim_system_install.sh
fi

if [[ $prev < 2021-03-06 ]] && [ $student = "OD_Robotique" ]; then
    cd $ROS1_EXT_PATH/src
    github_clone oKermorgant:ecn_common
fi



echo "Updating source-installed packages"
git_update_subfolders /opt/local_ws

echo "Updating ROS 1 source-installed packages"
source ~/.bashrc
git_update_subfolders $ROS1_EXT_PATH/src
cd $ROS1_EXT_PATH
ros1ws
catkin config --extend /opt/ros/$ROS1_DISTRO --install --cmake-args -DCMAKE_BUILD_TYPE=Release
catkin build --force-cmake

if [ -d $ROS2_EXT_PATH/src ]; then
echo "Updating ROS 2 source-installed packages"
    git_update_subfolders $ROS2_EXT_PATH/src
    cd $ROS2_EXT_PATH
    colbuild
fi

cd $INSTALLDIR
echo $(date -Idate) > .latest

if [[ $prev < 2021-01-06 ]] && [ $student = "OD_Robotique" ]; then
    cd $INSTALLDIR/skel/.config
    rsync -avr xfce4 ~/.config --delete
    echo "XFCE will restart to reload the panel"
    sleep 10
    pkill -KILL -u ecn
fi
