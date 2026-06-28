#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.substitutions import PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ld = LaunchDescription()

    # --- URDF / RViz display via urdf_launch ---
    default_model_path = PathJoinSubstitution(
        [FindPackageShare('robot_arm'), 'urdf', 'robot_arm.urdf']
    )
    default_rviz_config_path = PathJoinSubstitution(
        [FindPackageShare('launcher'), 'rviz', 'robot_arm.rviz']
    )

    ld.add_action(DeclareLaunchArgument(
        name='model', default_value=default_model_path,
        description='Path to robot URDF file'))
    ld.add_action(DeclareLaunchArgument(
        name='rvizconfig', default_value=default_rviz_config_path,
        description='Absolute path to RViz config file'))
    ld.add_action(DeclareLaunchArgument(
        name='servo_adapter_mode', default_value='both',
        description='Which servo adapter to run: real, dummy, or both'))

    # Use description.launch.py (robot_state_publisher only) instead of
    # display.launch.py to avoid joint_state_publisher competing on /joint_states.
    # servo_adapter_dummy remains the /joint_states publisher for visualization.
    ld.add_action(IncludeLaunchDescription(
        PathJoinSubstitution([FindPackageShare('urdf_launch'), 'launch', 'description.launch.py']),
        launch_arguments={
            'urdf_package': 'robot_arm',
            'urdf_package_path': LaunchConfiguration('model'),
        }.items()
    ))

    ld.add_action(Node(
        package='rviz2',
        executable='rviz2',
        condition=IfCondition(PythonExpression([
            "'", LaunchConfiguration('servo_adapter_mode'), "' == 'dummy'"
        ])),
        output='screen',
        arguments=['-d', LaunchConfiguration('rvizconfig')],
    ))

    # --- Robot arm nodes ---
    nodes = [

        Node(
            package='robot_arm',
            executable='servo_adapter',
            name='servo_adapter',
            condition=IfCondition(PythonExpression([
                "'", LaunchConfiguration('servo_adapter_mode'), "' in ['real', 'both']"
            ])),
            output='screen'
        ),

        Node(
            package='robot_arm',
            executable='servo_adapter_dummy',
            name='servo_adapter_dummy',
            condition=IfCondition(PythonExpression([
                "'", LaunchConfiguration('servo_adapter_mode'), "' in ['dummy', 'both']"
            ])),
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

        Node(
            package='robot_arm',
            executable='trajectory_tracker',
            name='trajectory_tracker',
            parameters=[{'marker_frame': 'base_link'}],
            output='screen'
        ),
    ]

    for node in nodes:
        ld.add_action(node)

    return ld
