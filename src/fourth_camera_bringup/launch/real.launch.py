"""Real hardware: V4L2 USB camera + processing."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('fourth_camera_bringup')

    return LaunchDescription([
        DeclareLaunchArgument('device', default_value='/dev/video0'),
        DeclareLaunchArgument(
            'camera_info_file',
            default_value=os.path.join(pkg, 'config', 'usb_camera_calibration.yaml'),
            description='camera_calibration YAML; empty = uncalibrated'),
        DeclareLaunchArgument('viewer', default_value='true'),

        Node(
            package='fourth_camera', executable='usb_camera_node',
            name='usb_camera', namespace='camera',
            parameters=[os.path.join(pkg, 'config', 'usb_camera.yaml'),
                        {'device': LaunchConfiguration('device'),
                         'camera_info_file': LaunchConfiguration('camera_info_file')}],
            output='screen',
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(pkg, 'launch', 'processing.launch.py')),
            launch_arguments={'use_sim_time': 'false',
                              'viewer': LaunchConfiguration('viewer')}.items(),
        ),
    ])
