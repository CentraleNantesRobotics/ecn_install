#!/bin/bash

cd ~/.ecn_install
echo "Refreshing patches..."
git pull

# module dependencies
python3 ./update.py "$@" 
cd ~
