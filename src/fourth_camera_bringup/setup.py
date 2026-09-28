from glob import glob

from setuptools import setup

package_name = 'fourth_camera_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=[],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/worlds', glob('worlds/*.sdf')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='tetsu',
    maintainer_email='tetsu@admat.jp',
    description='Launch files, configs and Gazebo worlds for fourth_camera',
    license='Apache-2.0',
)
