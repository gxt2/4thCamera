"""Common part shared by sim and real: camera optical TF, image processing, viewer."""

import math
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(get_package_share_directory('fourth_camera_bringup'), 'config')
    use_sim_time = LaunchConfiguration('use_sim_time')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('viewer', default_value='true',
                              description='Open rqt_image_view on the annotated image'),

        # camera_link (x forward, z up) -> camera_optical_frame (z forward, x right, y down)
        Node(
            package='tf2_ros', executable='static_transform_publisher',
            name='camera_optical_tf',
            arguments=['--roll', str(-math.pi / 2), '--yaw', str(-math.pi / 2),
                       '--frame-id', 'camera_link', '--child-frame-id', 'camera_optical_frame'],
            parameters=[{'use_sim_time': use_sim_time}],
        ),
        Node(
            package='fourth_camera', executable='color_detector_node',
            name='color_detector', namespace='camera',
            parameters=[os.path.join(config, 'color_detector.yaml'),
                        {'use_sim_time': use_sim_time}],
            output='screen',
        ),
        Node(
            package='rqt_image_view', executable='rqt_image_view',
            arguments=['/camera/image_annotated'],
            parameters=[{'use_sim_time': use_sim_time}],
            condition=IfCondition(LaunchConfiguration('viewer')),
        ),
    ])
