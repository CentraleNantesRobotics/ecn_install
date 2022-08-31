#!/usr/bin/bash

skel=$(realpath "$0")
skel=$(dirname $skel)/$(lsb_release -sc)

rm -rf $skel
mkdir -p ${skel}/Desktop
mkdir -p ${skel}/Downloads

# bashrc
cp ~/.bashrc $skel

# geany
mkdir -p ${skel}/.config/geany
echo "use_tab_to_indent=false
indent_type=0" >> ${skel}/.config/geany/geany.conf
rsync -avr ~/.config/geany/filedefs ${skel}/.config/geany

# xfce
rsync -avr --exclude desktop/ ~/.config/xfce4 ${skel}/.config/
