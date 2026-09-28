"""Gazebo (Harmonic) simulation: camera world + bridge + processing."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('fourth_camera_bringup')
    world = LaunchConfiguration('world')
    # -r: start unpaused, -s: server only (no GUI)
    gz_args = PythonExpression([
        "'-r ' + ('-s ' if '", LaunchConfiguration('headless'), "' == 'true' else '') + '",
        world, "'"])

    return LaunchDescription([
        DeclareLaunchArgument('world', default_value=os.path.join(pkg, 'worlds', 'camera_world.sdf')),
        DeclareLaunchArgument('headless', default_value='false'),
        DeclareLaunchArgument('viewer', default_value='true'),
        DeclareLaunchArgument('detector', default_value='color', choices=['color', 'cuboid']),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
            launch_arguments={'gz_args': gz_args, 'on_exit_shutdown': 'true'}.items(),
        ),
        Node(
            package='ros_gz_bridge', executable='parameter_bridge',
            name='gz_bridge',
            parameters=[{'config_file': os.path.join(pkg, 'config', 'gz_bridge.yaml'),
                         'use_sim_time': True}],
            output='screen',
        ),
        # Must match <pose> of the "camera" model in worlds/camera_world.sdf
        Node(
            package='tf2_ros', executable='static_transform_publisher',
            name='world_to_camera_tf',
            arguments=['--z', '1.0', '--pitch', '0.3',
                       '--frame-id', 'world', '--child-frame-id', 'camera_link'],
            parameters=[{'use_sim_time': True}],
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(pkg, 'launch', 'processing.launch.py')),
            launch_arguments={'use_sim_time': 'true',
                              'viewer': LaunchConfiguration('viewer'),
                              'detector': LaunchConfiguration('detector')}.items(),
        ),
    ])
