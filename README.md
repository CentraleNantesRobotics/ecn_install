Some scripts to easily setup Ubuntu Focal / ROS 1 / ROS 2 at Centrale Nantes

Module files indicate the dependencies for each lab.

The `update.py` is used to keep the computer up to date. Run it without arguments or by specifying which module you want to update:
  - `update.py -u` will update all installed modules
  - `update.py -u arpro` will only update arpro
  - `update.py -a` will install all dependencies for all labs (Robotics major / M1 CORO-IMARO / M2 CORO-IMARO)
  - adding `-n` will skip the `apt upgrade` step, which may be a bit long

In the lab dependencies, system-wide ROS overlays are installed at `/opt/ecn/ros1` and `/opt/ecn/ros2`. They should be sourced in your `.bashrc` if you use this system on a native Ubuntu OS.
