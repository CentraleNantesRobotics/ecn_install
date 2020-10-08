#!/bin/bash

# cd ~/.ecn_install
# git pull

if [ ! -f ".latest" ]
then
    prev=2020-09-01
else
    prev=$(cat .latest)
fi

bash virtual_machine/patches.sh $prev


# cd ~/.ecn_install
echo $(date -Idate) > .latest


cd ~

