cd ~

# copy ROS base + Catkin default config
mkdir -p ~/.skel/skel/ros/src
cp ~/ros/baxter.sh ~/.skel/skel/ros/
cp -r ~/ros/.catkin_tools ~/.skel/skel/ros
rm -rf ~/.skel/skel/ros/.catkin_tools/profiles/default/packages

# copy configuration
mkdir -p ~/.skel/skel/.config
dirs="xfce4 user-dirs.dirs user-dirs.locale "
for dir in $dirs
do
    cp -r ~/.config/$dir ~/.skel/skel/.config/$dir
done

mkdir -p ~/.skel/skel/Desktop
mkdir -p ~/.skel/skel/Downloads

cp ~/.bashrc ~/.skel/skel


echo "Type 'rsync -a vm:~/.skel/skel .' in ecn_install folder"
