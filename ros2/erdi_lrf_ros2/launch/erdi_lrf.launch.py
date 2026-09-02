"""Launch the ERDI rangefinder Range publisher.

    ros2 launch erdi_lrf_ros2 erdi_lrf.launch.py \
        port:=/dev/ttyUSB0 model:=LRF3000A1 rate:=10.0
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    args = [
        DeclareLaunchArgument('port', default_value='/dev/ttyUSB0'),
        DeclareLaunchArgument('model', default_value='LRF3000A1'),
        DeclareLaunchArgument('baud', default_value='0'),
        DeclareLaunchArgument('rate', default_value='10.0'),
        DeclareLaunchArgument('frame_id', default_value='erdi_lrf'),
        DeclareLaunchArgument('continuous', default_value='false'),
    ]
    node = Node(
        package='erdi_lrf_ros2',
        executable='range_node',
        name='erdi_lrf_range',
        output='screen',
        parameters=[{
            'port': LaunchConfiguration('port'),
            'model': LaunchConfiguration('model'),
            'baud': LaunchConfiguration('baud'),
            'rate': LaunchConfiguration('rate'),
            'frame_id': LaunchConfiguration('frame_id'),
            'continuous': LaunchConfiguration('continuous'),
        }],
    )
    return LaunchDescription(args + [node])
