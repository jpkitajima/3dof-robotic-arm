#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([

        Node(
            package='robot_arm',
            executable='servo_adapter_dummy',
            name='servo_adapter_dummy',
            output='screen'
        ),

        Node(
            package='robot_arm',
            executable='forward_kinematics',
            name='forward_kinematics',
            output='screen'
        ),

        Node(
            package='robot_arm',
            executable='inverse_kinematics',
            name='inverse_kinematics',
            parameters=[{'elbow': 'up'}],
            output='screen'
        ),

        Node(
            package='robot_arm',
            executable='input_receiver',
            name='input_receiver',
            output='screen'
        ),

        Node(
            package='robot_arm',
            executable='plotter',
            name='plotter',
            output='screen'
        ),

        Node(
            package='robot_arm',
            executable='website_input',
            name='website_input',
            output='screen'
        ),

        Node(
            package='robot_arm',
            executable='points_manager',
            name='points_manager',
            output='screen'
        ),
    ])
