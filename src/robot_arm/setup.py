from glob import glob
from pathlib import Path
from setuptools import find_packages, setup

package_name = 'robot_arm'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/resource', [p for p in glob('resource/*') if Path(p).is_file()]),
        (
            'share/' + package_name + '/resource/website_input',
            glob('robot_arm/website_input/resources/*'),
        ),
        (
            'share/' + package_name + '/resource/plotter',
            glob('robot_arm/plotter/resources/*.svg'),
        ),
        ('share/robot_arm/urdf', ['urdf/robot_arm.urdf']),
        ('share/robot_arm/meshes', glob('meshes/*.stl')),
    ],
    install_requires=['setuptools', 'aiohttp', 'svgpathtools', 'python-st3215'],
    zip_safe=True,
    maintainer='Kitajima',
    maintainer_email='noreply@example.com',
    description='TODO: Package description',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'bus_servo_adapter = robot_arm.bus_servo_adapter.bus_servo_adapter:main',
            'servo_adapter = robot_arm.servo_adapter.servo_adapter:main',
            'servo_adapter_dummy = robot_arm.servo_adapter_dummy.servo_adapter_dummy:main',
            'inverse_kinematics = robot_arm.inverse_kinematics.inverse_kinematics:main',
            'forward_kinematics = robot_arm.forward_kinematics.forward_kinematics:main',
            'plotter = robot_arm.plotter.node:main',
            'points_manager = robot_arm.manual_path_programmer.points_manager:main',
            'input_receiver = robot_arm.input_receiver.input_receiver:main',
            'website_input = robot_arm.website_input.website_input:main',
            'trajectory_tracker = robot_arm.trajectory_tracker.trajectory_tracker:main',
        ],
    },
)
