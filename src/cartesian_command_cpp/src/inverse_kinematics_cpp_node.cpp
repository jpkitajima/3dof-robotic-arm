#include <array>
#include <cmath>
#include <functional>
#include <memory>
#include <optional>

#include "angles/angles.h"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float32_multi_array.hpp"

class InverseKinematicsCppNode : public rclcpp::Node
{
public:
  static constexpr double L1 = 0.1275;  // Length of the first arm segment in meters
  static constexpr double L2 = 0.132804;  // Length of the second arm segment in meters
  static constexpr double PEN_OFFSET = 0.02;  // Offset for the pen in meters
  static constexpr double L3 = 0.13075 + PEN_OFFSET;  // Length of the third arm segment in meters

  static constexpr int THETA_1_CHANNEL = 1;
  static constexpr int THETA_2_CHANNEL = 2;
  static constexpr int THETA_3_CHANNEL = 3;

  InverseKinematicsCppNode()
  : Node("inverse_kinematics_cpp")
  {
    publisher_ = create_publisher<std_msgs::msg::Float32MultiArray>("st3215_angle", 1000);
    subscription_ = create_subscription<std_msgs::msg::Float32MultiArray>(
      "cartesian_xyz",
      1000,
      std::bind(&InverseKinematicsCppNode::cartesian_xyz_callback, this, std::placeholders::_1));
  }

private:
  double calculate_theta_1_radians(double y, double x)
  {
    return std::atan2(y, x);
  }

  double calculate_theta_2_radians(
    double h, double r, double theta3)
  {
    const double a = L3 * std::cos(theta3) + L2;
    const double b = L3 * std::sin(theta3);
    return std::atan2(h, r) - std::atan2(b, a);
  }

  std::optional<std::array<double, 2>> calculate_theta_3_radians(double h, double r)
  {
    const double d = calculate_reachability(h, r);
    if (d > 1.0 || d < -1.0) {
      RCLCPP_ERROR(
        get_logger(),
        "Position is unreachable because reachability value d (%.6f) exceeds 1 or is less than -1.",
        d);
      return std::nullopt;
    }

    const double theta3_radians = std::acos(d);
    return std::array<double, 2>{theta3_radians, -theta3_radians};
  }

  double calculate_reachability(double h, double r)
  {
    const double d = (r * r + h * h - L3 * L3 - L2 * L2) / (2 * L3 * L2);
    return d;
  }

  // Returns theta1, theta2, and theta3 in degrees.
  std::optional<std::array<double, 3>> calculate_inverse_kinematics(float x, float y, float z)
  {
    const double theta1_radians = calculate_theta_1_radians(y, x);
    const double h = z - L1;
    const double r = std::sqrt(x * x + y * y);

    const auto theta3_candidates_radians = calculate_theta_3_radians(h, r);
    if (!theta3_candidates_radians.has_value()) {
      return std::nullopt;
    }

    const double theta3_positive_radians = (*theta3_candidates_radians)[0];
    [[maybe_unused]] const double theta3_negative_radians = (*theta3_candidates_radians)[1];
    const double theta2_radians =
      calculate_theta_2_radians(h, r, theta3_positive_radians);

    return std::array<double, 3>{
      -angles::to_degrees(theta1_radians),
      -angles::to_degrees(theta2_radians),
      angles::to_degrees(theta3_positive_radians)};
  }

  void publish_angles(double theta1_degrees, double theta2_degrees, double theta3_degrees)
  {
    const std::array<int, 3> channels = {
      THETA_1_CHANNEL, THETA_2_CHANNEL, THETA_3_CHANNEL};
    const std::array<double, 3> angles = {
      theta1_degrees, theta2_degrees, theta3_degrees};

    for (std::size_t i = 0; i < angles.size(); ++i) {
      std_msgs::msg::Float32MultiArray angle_msg;
      angle_msg.data = {
        static_cast<float>(channels[i]),
        static_cast<float>(angles[i])};
      publisher_->publish(angle_msg);
    }
  }

  void cartesian_xyz_callback(const std_msgs::msg::Float32MultiArray::ConstSharedPtr msg)
  {
    // The message contains the target Cartesian coordinates in meters, ordered as x, y, z.
    if (msg->data.size() != 3) {
      RCLCPP_ERROR(get_logger(), "Invalid Cartesian coordinates received. Expected 3 values.");
      return;
    }

    RCLCPP_INFO(
      get_logger(), "Received Cartesian coordinates: [%.3f, %.3f, %.3f]",
      msg->data[0], msg->data[1], msg->data[2]);

    const auto angles = calculate_inverse_kinematics(msg->data[0], msg->data[1], msg->data[2]);
    if (!angles.has_value()) {
      return;
    }

    publish_angles((*angles)[0], (*angles)[1], (*angles)[2]);
  }

  rclcpp::Publisher<std_msgs::msg::Float32MultiArray>::SharedPtr publisher_;
  rclcpp::Subscription<std_msgs::msg::Float32MultiArray>::SharedPtr subscription_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<InverseKinematicsCppNode>());
  rclcpp::shutdown();
  return 0;
}
