Some scripts to easily setup new Ubuntu compters at Centrale Nantes

## ROS 1 / ROS 2 management

The script `ros_management.bash` has a set of tools to handle ROS 1 / ROS 2 workspaces. It can be sourced in a `.bashrc` after defining the two variables `ros1_workspaces` and `ros2_workspaces`, that point to the overlay-ordered workspaces:

```bash
ros1_workspaces="/opt/ros/noetic $HOME/code/libs/ros $HOME/code/ros"
ros2_workspaces="/opt/ros/foxy $HOME/code/libs/ros2 $HOME/code/ros2"
source /home/olivier/code/projects/ecn_install/ros_management.bash
ros1ws  # activate ROS 1 / disable ROS 2
ros2ws  # activate ROS 2 / disable ROS 1
```
