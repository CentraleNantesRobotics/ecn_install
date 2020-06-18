#!/bin/bash

export version=`lsb_release -sc`
export ros_distro="kinetic"

if [[ $version == "trusty" ]]
then
export ros_distro="indigo"
fi

if [[ $version == "bionic" ]] || [[ $version == "stretch" ]]
then
export ros_distro="melodic"
fi


install_pkg_with_prefix()
{
ros_pkgs=""
for pkg in $pkgs 
do
    ros_pkgs="$ros_pkgs ros-$ros_distro-$pkg"
done

}


# creates Catkin workspace
before_dl()
{
    sudo mkdir -p /opt/ros_ext/src
    sudo chmod -R a+rwX /opt/ros_ext
    cd /opt/ros_ext/src
}


# install UWSim
dl_uwsim()
{
	src_dir=`pwd`

	# packaged deps
	sudo apt install -y libopenscenegraph-dev libfftw3-dev libxml++2.6-dev ros-${ros_distro}-control-toolbox

	# as ROS pkg
	cd $src_dir
	git clone -b master --recurse-submodules https://github.com/oKermorgant/underwater_simulation.git
	
	# non packaged deps
	cd underwater_simulation/submodules
	deps="uwsim_osgocean uwsim_osgworks uwsim_bullet uwsim_osgbullet"
	for dep in $deps
	do
	mkdir -p $dep-release/builduw
	cd $dep-release/builduw
	cmake .. -DCMAKE_BUILD_TYPE=Release && sudo make install
	cd ../..
	sudo chmod a+rX -R /usr/local
	sudo rm -rf $dep-release/builduw
	done

	# go back to root
	cd ../..
	
	# DL dataset
	if [ ! -d /opt/uwsim/data ]
	then
		sudo mkdir -p /opt/uwsim/ -m 2755
		cd /opt/uwsim
		sudo wget  http://www.irs.uji.es/uwsim/files/data.tgz
		sudo tar -xf data.tgz
		sudo chmod a+rwX -R .
		sudo rm data.tgz	
		
		# on-the-fly symlink for all users
		sudo bash -c "echo 'if [ ! -d ~/.uwsim ]; then ln -s /opt/uwsim ~/.uwsim; fi' >> /etc/bash.bashrc"
	fi
	cd $src_dir
}

# download Baxter files into temporary catkin ws
dl_baxter()
{    
    git clone https://github.com/RethinkRobotics/baxter_common.git
    git clone https://github.com/CentraleNantesRobotics/baxter_interface.git
    git clone https://github.com/CentraleNantesRobotics/baxter_tools.git       
}

# catkin install to /opt/ros
after_dl()
{    
    sudo ldconfig -v
    cd /opt/ros_ext/
    source /opt/ros/$ros_distro/setup.bash
    catkin config --extend /opt/ros/${ros_distro} --install --cmake-args -DCMAKE_BUILD_TYPE=Release
    sudo -E bash -c 'catkin build'
    sudo chmod -R a+rX /opt/ros_ext
}

