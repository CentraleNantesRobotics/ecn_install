#!/bin/bash

export ROS_MASTER_URI=http://baxter.local:11311
export ROS_IP=$(echo $(hostname -I) | cut -d' ' -f 1)
export PS1="[baxter ] $PS1"
