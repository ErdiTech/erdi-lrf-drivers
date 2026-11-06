# ROS 2

The ROS 2 driver now lives in its own repository so it can be released through
the ROS build farm (rosdistro requires packages that do not depend on pip keys):

**https://github.com/Tommyapi/erdi_lrf_ros2**

* Same package name (`erdi_lrf_ros2`), same `range` topic (`sensor_msgs/msg/Range`) and parameters.
* Serial codec bundled, so no `pip install erdi-lrf` is needed; `python3-serial` is the only runtime dependency.
* Per-model beam divergence table, optional continuous streaming, CI on ROS 2 Jazzy and Humble.
* The old `range_node` executable name is kept as an alias.

```bash
cd ~/ros2_ws/src && git clone https://github.com/Tommyapi/erdi_lrf_ros2.git
```

The Python driver in this repository (`python/`) is unchanged.
