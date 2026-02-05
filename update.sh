#!/usr/bin/bash

base_dir=$(dirname $(realpath $0))

echo "Refreshing modules..."
(cd $base_dir && git pull)

# run explicitely in bash terminal for ROS pkgs
cmd="python3 install_deps.py $@"
(cd $base_dir && bash -i -c "$cmd")
