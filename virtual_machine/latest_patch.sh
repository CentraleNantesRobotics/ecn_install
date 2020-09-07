#!/bin/bash
# execute these lines in the console of the Virtual Machine to have it up to date


# 7 Sept 2020
sudo apt update
sudo apt install -qy texlive-latex-extra texlive-fonts-recommended dvipng
cd /opt/src
git clone https://github.com/oKermorgant/log2plot
mkdir -p log2plot/build
cd log2plot/build
cmake .. && sudo make install
