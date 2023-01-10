#!/bin/bash

base_dir=$(dirname $(realpath $0))

echo "Refreshing patches..."
(cd $base_dir && git pull)

# module dependencies
(cd $base_dir && python3 update.py "$@")
