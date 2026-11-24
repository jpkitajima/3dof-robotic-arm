cmake_minimum_required(VERSION 3.8)
project(cartesian_command_cpp)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)

add_executable(cartesian_command_cpp_node src/cartesian_command_cpp_node.cpp)
ament_target_dependencies(cartesian_command_cpp_node rclcpp std_msgs)

install(TARGETS
  cartesian_command_cpp_node
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
