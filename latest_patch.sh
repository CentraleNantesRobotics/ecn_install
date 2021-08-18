#!/bin/bash

# cd ~/.ecn_install
git pull --recurse-submodules

# system patches
bash ./patches.sh

# module dependencies
python3 ./update.py "$@"
