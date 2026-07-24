docker run --rm -it \
  --name arm-dev \
  --network host \
  -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}" \
  -v "$PWD":/ws \
  -w /ws \
  ros:jazzy \
  bash
