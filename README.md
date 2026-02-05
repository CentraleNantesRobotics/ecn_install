# Some scripts to easily setup Ubuntu / ROS 2

A meta-package manager for Ubuntu (apt + git + deb + pip), used at Centrale Nantes to keep the lab computers up-to-date. This tool was built during the COVID lockdown so that students could easily manage their virtual machine and spend time learning robotics instead of Ubuntu / ROS 2 packaging.

# Entry point

The `install_deps.py` is to be run it without arguments or by specifying which module you want to update:

  - `install_deps.py -u` will update all installed modules
  - `install_deps.py -u arpro` will only update arpro
  - `install_deps.py -a` will install all dependencies for all modules
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

# Refreshing the whole directory

The `update.sh` script will first run `git pull` before running the Python script, in order to keep the dependency list (and various files) up-to-date as well.
