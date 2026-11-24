#include <chrono>
#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float32_multi_array.hpp"

using namespace std::chrono_literals;

class CartesianCommandCppNode : public rclcpp::Node
{
public:
  CartesianCommandCppNode()
  : Node("cartesian_command_cpp")
  {
    publisher_ = create_publisher<std_msgs::msg::Float32MultiArray>("cartesian_xyz", 10);
    publish_timer_ = create_wall_timer(100ms, [this]() { publish_when_subscribed(); });
    RCLCPP_INFO(get_logger(), "Waiting for a subscriber on cartesian_xyz before sending one target.");
  }

private:
  void publish_when_subscribed()
  {
    if (publisher_->get_subscription_count() == 0) {
      return;
    }

    std_msgs::msg::Float32MultiArray msg;
    msg.data = {0.20F, 0.05F, 0.15F};
    publisher_->publish(msg);
    RCLCPP_INFO(get_logger(), "Published one cartesian_xyz target: [0.20, 0.05, 0.15] m");
    publish_timer_->cancel();
  }

  rclcpp::Publisher<std_msgs::msg::Float32MultiArray>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr publish_timer_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<CartesianCommandCppNode>());
  rclcpp::shutdown();
  return 0;
}
