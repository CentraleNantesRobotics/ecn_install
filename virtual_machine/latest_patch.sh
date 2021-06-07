#!/bin/bash

cd ~/.ecn_install
git pull --recurse-submodules

bash virtual_machine/patches.sh

