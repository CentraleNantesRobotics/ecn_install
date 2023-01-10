Some scripts to easily setup Ubuntu Focal / ROS 1 / ROS 2 at Centrale Nantes

## ROS 1 / ROS 2 management

ROS 1/2 dependencies assume you use the [ros_management](https://github.com/oKermorgant/ros_management_tools) tool to handle ROS 1 / ROS 2 workspaces. It can be sourced in a `.bashrc` after defining the two variables `ros1_workspaces` and `ros2_workspaces`, that point to the overlay-ordered workspaces:

```bash
ros1_workspaces="/opt/ros/noetic ~/a_first_ros1_workspace ~/main_ros1_overlay"
ros2_workspaces="/opt/ros/foxy ~/some_ros2_workspace ~/main_ros2_overlay"
# activate ROS 1 by default
source /path/to/ros_management.bash -k -p -ros1
```

If `ros1ws` or `ros2ws` are called then the corresponding ROS version will become the default in future terminals.

## Overall setup

Do not blindly run the `reinstall_from_scratch.bash` script but feel free to reuse existing parts to suit your needs.


## Virtual Machine

The `update.py` is used to keep the Virtual Machine up to date. Run it without arguments or by specifying which module you want to update:
  - `update.py -u` will update all installed modules
  - `update.py -u arpro` will only update arpro
  - `update.py -a` will install all dependencies for all labs (Robotics major / M1 CORO-IMARO / M2 CORO-IMARO)
    
In the lab dependencies, system-wide overlays are installed at `/opt/ecn/ros1` and `/opt/ecn/ros2`. They should be sourced in your `.bashrc` if you use this system on a native Ubuntu OS.
