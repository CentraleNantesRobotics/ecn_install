#!/bin/bash

sed -i 's@export PS1=/c@export PS1=\"\\\[\\\e[1;34m\\\]\\\w\\\[\\\e[0m\\\]$ \"@' ~/.bashrc
