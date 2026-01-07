# Some scripts to easily setup Ubuntu / ROS 1 / ROS 2

A meta-package manager for Ubuntu (apt + git + deb + pip), used at Centrale Nantes to keep the computers up-to-date.

# Entry point


The `update.py` is to be run it without arguments or by specifying which module you want to update:

  - `update.py -u` will update all installed modules
  - `update.py -u arpro` will only update arpro
  - `update.py -a` will install all dependencies for all modules
  - adding `-n` will skip the `apt upgrade` step, which may save some time

In the lab dependencies, system-wide ROS overlays are installed at `/opt/ecn/ros1` and `/opt/ecn/ros2`. They should be sourced in your `.bashrc` if you use this system on a native Ubuntu OS.


# Module definitions

Modules are the `module*.yaml` files, where:

  - `modules.yaml` is common to all distros
  - ``modules-{distro}.yaml` is specific to this distro

The two files will be merged into a single dependency graph.

## Specific keys

  - `lib_folder`: where git-based packages are installed. ROS / ROS 2 are installed under  `{lib_folder}/ros1` and  `{lib_folder}/ros2`
  - `vm`: if specific packages are not to be installed in a given virtual machine, also give the VM hostname to identify it
