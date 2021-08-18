#!/bin/bash

INSTALLDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# update bashrc
cd $INSTALLDIR
cp skel/.bashrc ~
source ~/.bashrc

