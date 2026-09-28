from setuptools import find_packages, setup

package_name = 'fourth_camera'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='tetsu',
    maintainer_email='tetsu@admat.jp',
    description='USB camera driver and image processing nodes',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'usb_camera_node = fourth_camera.usb_camera_node:main',
            'color_detector_node = fourth_camera.color_detector_node:main',
            'cuboid_finder_node = fourth_camera.cuboid_finder_node:main',
        ],
    },
)
