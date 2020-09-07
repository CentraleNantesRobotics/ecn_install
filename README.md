Some scripts to easily setup Ubuntu Focal / ROS Noetic / ROS 2 Foxy at Centrale Nantes

## ROS 1 / ROS 2 management

The script `ros_management.bash` has a set of tools to handle ROS 1 / ROS 2 workspaces. It can be sourced in a `.bashrc` after defining the two variables `ros1_workspaces` and `ros2_workspaces`, that point to the overlay-ordered workspaces:

```bash
ros1_workspaces="/opt/ros/noetic ~/a_first_ros1_workspace ~/main_ros1_overlay"
ros2_workspaces="/opt/ros/foxy ~/some_ros2_workspace ~/main_ros2_overlay"
source /path/to/ros_management.bash
ros1ws  # activate ROS 1 / disable ROS 2
ros2ws  # activate ROS 2 / disable ROS 1
```
The `ros1ws` and `ros2ws` functions also update the bash prompt to highlight the current distro in use.

## Overall setup

Do not blindly run the `reinstall_from_scratch.bash` script but feel free to reuse existing parts to suit your needs.


## Virtual Machine

The `virtual_machine` folder has several files to keep the Virtual Machine up to date. 
