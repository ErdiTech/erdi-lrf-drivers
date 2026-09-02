import os
from glob import glob

from setuptools import setup

package_name = 'erdi_lrf_ros2'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
         glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools', 'erdi-lrf'],
    zip_safe=True,
    maintainer='ERDI Technology (Chengdu)',
    maintainer_email='noreply@erdilrf.com',  # enquiries: https://erdilrf.com/contact/
    description='ROS 2 driver for ERDI 905 nm laser rangefinder modules.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'range_node = erdi_lrf_ros2.range_node:main',
        ],
    },
)
